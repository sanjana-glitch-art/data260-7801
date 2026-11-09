from __future__ import annotations

import csv
import json
import time
from code.hw8_config import (
    BOOTSTRAP_SERVERS,
    DRAFTS_TOPIC,
    TASKS_TOPIC,
    VERIFY_SEED,
)
from code.hw8_kafka_client import (
    json_bytes,
    parse_json_bytes,
)
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from confluent_kafka import (
    Consumer,
    Producer,
    TopicPartition,
)

MESSAGE_COUNT = 20
WAIT_SECONDS = 60.0

JSON_PATH = Path(
    "reports/hw08/raw/ordering_results.json"
)
CSV_PATH = Path(
    "reports/hw08/raw/ordering_results.csv"
)


def utc_timestamp() -> str:
    """Return the current UTC timestamp."""

    return datetime.now(UTC).isoformat()


def create_draft_consumer() -> Consumer:
    """Consume drafts produced after this test starts."""

    consumer = Consumer({
        "bootstrap.servers": BOOTSTRAP_SERVERS,
        "group.id": (
            "s7801-order-verifier-"
            + str(uuid4())
        ),
        "enable.auto.commit": False,
        "auto.offset.reset": "latest",
    })

    metadata = consumer.list_topics(
        DRAFTS_TOPIC,
        timeout=10.0,
    )

    topic_metadata = metadata.topics[
        DRAFTS_TOPIC
    ]

    assignments = []

    for partition_id in sorted(
        topic_metadata.partitions
    ):
        partition = TopicPartition(
            DRAFTS_TOPIC,
            partition_id,
        )

        _, high_watermark = (
            consumer.get_watermark_offsets(
                partition,
                timeout=10.0,
                cached=False,
            )
        )

        assignments.append(
            TopicPartition(
                DRAFTS_TOPIC,
                partition_id,
                high_watermark,
            )
        )

    consumer.assign(assignments)
    return consumer


def produce_batch(
    producer: Producer,
    *,
    label: str,
    keyed: bool,
) -> None:
    """Produce one 20-message experiment batch."""

    entity_key = (
        f"clinical-trial-{VERIFY_SEED}"
    )

    for sequence in range(MESSAGE_COUNT):
        correlation_id = str(uuid4())

        message = {
            "correlation_id": correlation_id,
            "question": (
                "Process ordering event "
                f"{sequence} for {entity_key}."
            ),
            "plan": [
                (
                    "Process the clinical-trial "
                    f"event numbered {sequence}."
                ),
                (
                    "Preserve related-event "
                    "ordering."
                ),
            ],
            "entity_key": entity_key,
            "experiment_label": label,
            "sequence": sequence,
            "processing_delay_ms": (
                150
                if sequence % 2 == 0
                else 0
            ),
            "stage": "planned",
            "created_at": utc_timestamp(),
        }

        if keyed:
            producer.produce(
                TASKS_TOPIC,
                key=entity_key,
                value=json_bytes(message),
            )
        else:
            producer.produce(
                TASKS_TOPIC,
                key=None,
                partition=sequence % 2,
                value=json_bytes(message),
            )

    undelivered = producer.flush(
        timeout=15.0
    )

    if undelivered:
        raise RuntimeError(
            f"{undelivered} messages "
            "were not delivered."
        )


def collect_drafts(
    consumer: Consumer,
    label: str,
) -> list[dict[str, Any]]:
    """Collect all drafts for one experiment."""

    drafts: dict[int, dict[str, Any]] = {}

    deadline = (
        time.monotonic()
        + WAIT_SECONDS
    )

    while (
        len(drafts) < MESSAGE_COUNT
        and time.monotonic() < deadline
    ):
        kafka_message = consumer.poll(1.0)

        if kafka_message is None:
            continue

        if kafka_message.error():
            raise RuntimeError(
                str(kafka_message.error())
            )

        message = parse_json_bytes(
            kafka_message.value()
        )

        if (
            message.get("experiment_label")
            != label
        ):
            continue

        sequence = message.get("sequence")

        if not isinstance(sequence, int):
            continue

        drafts[sequence] = message

    if len(drafts) != MESSAGE_COUNT:
        raise TimeoutError(
            "Expected "
            f"{MESSAGE_COUNT} drafts for "
            f"{label}, received {len(drafts)}."
        )

    return list(drafts.values())


def summarize(
    label: str,
    drafts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Summarize completion ordering."""

    completion_order = [
        int(message["sequence"])
        for message in sorted(
            drafts,
            key=lambda item: str(
                item["created_at"]
            ),
        )
    ]

    source_partitions = sorted({
        int(message["source_partition"])
        for message in drafts
    })

    writer_instances = sorted({
        str(message["writer_instance"])
        for message in drafts
    })

    expected_order = list(
        range(MESSAGE_COUNT)
    )

    return {
        "label": label,
        "message_count": len(drafts),
        "expected_order": expected_order,
        "completion_order": completion_order,
        "ordering_preserved": (
            completion_order
            == expected_order
        ),
        "source_partitions": (
            source_partitions
        ),
        "writer_instances": (
            writer_instances
        ),
        "writer_count": len(
            writer_instances
        ),
    }


def write_csv(
    before_drafts: list[dict[str, Any]],
    after_drafts: list[dict[str, Any]],
) -> None:
    """Write message-level ordering evidence."""

    CSV_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with CSV_PATH.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "experiment_label",
                "sequence",
                "source_partition",
                "source_offset",
                "writer_instance",
                "completed_at",
            ],
        )

        writer.writeheader()

        for message in (
            before_drafts
            + after_drafts
        ):
            writer.writerow({
                "experiment_label": (
                    message[
                        "experiment_label"
                    ]
                ),
                "sequence": message[
                    "sequence"
                ],
                "source_partition": (
                    message[
                        "source_partition"
                    ]
                ),
                "source_offset": message[
                    "source_offset"
                ],
                "writer_instance": message[
                    "writer_instance"
                ],
                "completed_at": message[
                    "created_at"
                ],
            })


def main() -> None:
    """Run before-and-after ordering tests."""

    producer = Producer({
        "bootstrap.servers": (
            BOOTSTRAP_SERVERS
        ),
    })

    draft_consumer = (
        create_draft_consumer()
    )

    run_suffix = str(uuid4())[:8]
    before_label = (
        f"before-unkeyed-{run_suffix}"
    )
    after_label = (
        f"after-keyed-{run_suffix}"
    )

    try:
        print(
            "DATA-260 Homework 8 Part 3"
        )
        print(
            "Ordering and Partitioning Test"
        )
        print(
            "Messages per scenario:",
            MESSAGE_COUNT,
        )

        print()
        print(
            "=== BEFORE: NO ENTITY KEY ==="
        )

        produce_batch(
            producer,
            label=before_label,
            keyed=False,
        )

        before_drafts = collect_drafts(
            draft_consumer,
            before_label,
        )

        before_summary = summarize(
            before_label,
            before_drafts,
        )

        print(
            "Completion order:",
            before_summary[
                "completion_order"
            ],
        )
        print(
            "Partitions:",
            before_summary[
                "source_partitions"
            ],
        )
        print(
            "Writers:",
            before_summary[
                "writer_instances"
            ],
        )
        print(
            "Ordering preserved:",
            before_summary[
                "ordering_preserved"
            ],
        )

        print()
        print(
            "=== AFTER: RELATED ENTITY KEY ==="
        )

        produce_batch(
            producer,
            label=after_label,
            keyed=True,
        )

        after_drafts = collect_drafts(
            draft_consumer,
            after_label,
        )

        after_summary = summarize(
            after_label,
            after_drafts,
        )

        print(
            "Completion order:",
            after_summary[
                "completion_order"
            ],
        )
        print(
            "Partitions:",
            after_summary[
                "source_partitions"
            ],
        )
        print(
            "Writers:",
            after_summary[
                "writer_instances"
            ],
        )
        print(
            "Ordering preserved:",
            after_summary[
                "ordering_preserved"
            ],
        )

    finally:
        producer.flush(timeout=2.0)
        draft_consumer.close()

    before_used_two_partitions = (
        before_summary[
            "source_partitions"
        ]
        == [0, 1]
    )

    before_used_two_writers = (
        before_summary[
            "writer_count"
        ]
        >= 2
    )

    before_showed_disorder = not (
        before_summary[
            "ordering_preserved"
        ]
    )

    after_used_one_partition = (
        len(
            after_summary[
                "source_partitions"
            ]
        )
        == 1
    )

    after_preserved_order = (
        after_summary[
            "ordering_preserved"
        ]
    )

    overall_passed = all([
        before_used_two_partitions,
        before_used_two_writers,
        before_showed_disorder,
        after_used_one_partition,
        after_preserved_order,
    ])

    results = {
        "experiment": (
            "hw8_ordering_and_partitioning"
        ),
        "verify_seed": VERIFY_SEED,
        "message_count_per_scenario": (
            MESSAGE_COUNT
        ),
        "before": before_summary,
        "after": after_summary,
        "checks": {
            "before_used_two_partitions": (
                before_used_two_partitions
            ),
            "before_used_two_writers": (
                before_used_two_writers
            ),
            "before_showed_disorder": (
                before_showed_disorder
            ),
            "after_used_one_partition": (
                after_used_one_partition
            ),
            "after_preserved_order": (
                after_preserved_order
            ),
        },
        "overall_passed": (
            overall_passed
        ),
        "generated_at": utc_timestamp(),
    }

    JSON_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    JSON_PATH.write_text(
        json.dumps(
            results,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    write_csv(
        before_drafts,
        after_drafts,
    )

    print()
    print(
        "Before used two partitions:",
        before_used_two_partitions,
    )
    print(
        "Before used two writers:",
        before_used_two_writers,
    )
    print(
        "Before showed disorder:",
        before_showed_disorder,
    )
    print(
        "After used one partition:",
        after_used_one_partition,
    )
    print(
        "After preserved order:",
        after_preserved_order,
    )
    print(
        "Overall:",
        (
            "PASS"
            if overall_passed
            else "FAIL"
        ),
    )
    print(
        "JSON:",
        JSON_PATH.resolve(),
    )
    print(
        "CSV:",
        CSV_PATH.resolve(),
    )

    if not overall_passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()