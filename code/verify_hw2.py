from __future__ import annotations

import io
import json
import subprocess
import sys
import time
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT)
    )


from code.agent_graph import (  # noqa: E402
    initialize_state,
    run_workflow
)
from code.agent_graph.schemas import (  # noqa: E402
    PlannerProposal
)
from src.model_client import ModelClient  # noqa: E402


HOMEWORK_NUMBER = 2
SID4 = 7801
PORT_BASE = 8601
SEED = 7801
VERIFY_SEED = 267801

MODEL = "qwen3:4b"
TEMPERATURE = 0.0
NUM_CTX = 4096
NUM_PREDICT = 256
TURN_CEILING = 2

BASE_URL = f"http://127.0.0.1:{PORT_BASE}"

REPORT_DIRECTORY = (
    PROJECT_ROOT
    / "reports"
    / "hw02"
)

RAW_DIRECTORY = (
    REPORT_DIRECTORY
    / "raw"
)

OUTPUT_PATH = (
    REPORT_DIRECTORY
    / "verification.json"
)

checks: list[dict[str, Any]] = []


def record(
    name: str,
    passed: bool,
    details: str
) -> None:
    """Store one objective verification result."""

    checks.append({
        "name": name,
        "passed": bool(passed),
        "details": details
    })


def utc_timestamp() -> str:
    """Return the current UTC time."""

    return datetime.now(
        timezone.utc
    ).isoformat()


def get_commit_hash() -> str:
    """Return the current Git commit hash."""

    try:
        result = subprocess.run(
            [
                "git",
                "rev-parse",
                "HEAD"
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True
        )

        return result.stdout.strip()

    except (
        OSError,
        subprocess.CalledProcessError
    ):
        return "unavailable"


def read_json(
    path: Path
) -> Any:
    """Load a JSON file."""

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def http_request(
    method: str,
    path: str,
    *,
    json_data: dict[str, Any] | None = None,
    form_data: dict[str, str] | None = None,
    timeout: float = 10.0
) -> tuple[int, str, str]:
    """Send an HTTP request to the FastAPI application."""

    body: bytes | None = None
    headers: dict[str, str] = {}

    if json_data is not None:
        body = json.dumps(
            json_data
        ).encode("utf-8")

        headers[
            "Content-Type"
        ] = "application/json"

    elif form_data is not None:
        body = urlencode(
            form_data
        ).encode("utf-8")

        headers[
            "Content-Type"
        ] = "application/x-www-form-urlencoded"

    request = Request(
        f"{BASE_URL}{path}",
        data=body,
        headers=headers,
        method=method
    )

    with urlopen(
        request,
        timeout=timeout
    ) as response:
        response_text = (
            response
            .read()
            .decode("utf-8")
        )

        return (
            response.status,
            response_text,
            response.geturl()
        )


def backend_responds() -> bool:
    """Return whether FastAPI responds on PORT_BASE."""

    try:
        status, _, _ = http_request(
            "GET",
            "/",
            timeout=2.0
        )

        return status == 200

    except (
        HTTPError,
        URLError,
        TimeoutError
    ):
        return False


def start_backend() -> subprocess.Popen[str] | None:
    """Use the running service or start temporary Uvicorn."""

    if backend_responds():
        record(
            "fastapi_port",
            True,
            (
                "Existing FastAPI application responded "
                f"on port {PORT_BASE}."
            )
        )

        return None

    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "code.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(PORT_BASE)
        ],
        cwd=PROJECT_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True
    )

    deadline = (
        time.monotonic()
        + 30
    )

    while time.monotonic() < deadline:
        if backend_responds():
            record(
                "fastapi_port",
                True,
                (
                    "Temporary FastAPI application "
                    f"responded on port {PORT_BASE}."
                )
            )

            return process

        time.sleep(0.5)

    record(
        "fastapi_port",
        False,
        (
            "FastAPI did not respond on "
            f"port {PORT_BASE}."
        )
    )

    process.terminate()

    return None


def stop_backend(
    process: subprocess.Popen[str] | None
) -> None:
    """Stop only a server started by this script."""

    if process is None:
        return

    process.terminate()

    try:
        process.wait(
            timeout=10
        )

    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(
            timeout=5
        )


def check_required_files() -> None:
    """Verify the required pre-report files."""

    required_files = [
        "code/__init__.py",
        "code/main.py",
        "code/Dockerfile",
        "code/run_agent_graph.py",
        "code/run_hw2_experiments.py",
        "code/verify_hw2.py",
        "code/agent_graph/__init__.py",
        "code/agent_graph/state.py",
        "code/agent_graph/schemas.py",
        "code/agent_graph/nodes.py",
        "code/agent_graph/router.py",
        "code/agent_graph/workflow.py",
        "code/web_application/index.html",
        "code/web_application/styles.css",
        "code/web_application/script.js",
        "src/model_client.py",
        "reports/hw02/AI_USE.md",
        "reports/hw02/METRICS.md",
        "reports/hw02/RUN_LOG.txt",
        (
            "reports/hw02/"
            "reproducible_run_instructions.md"
        ),
        (
            "reports/hw02/cases/"
            "schema_input.json"
        ),
        (
            "reports/hw02/cases/"
            "adversarial_input.json"
        ),
        (
            "reports/hw02/raw/"
            "schema_validation_results.json"
        ),
        (
            "reports/hw02/raw/"
            "schema_validation_results.csv"
        ),
        (
            "reports/hw02/raw/"
            "schema_validation_metrics.json"
        ),
        (
            "reports/hw02/raw/"
            "ceiling_comparison_results.json"
        ),
        (
            "reports/hw02/raw/"
            "ceiling_comparison_results.csv"
        ),
        (
            "reports/hw02/raw/"
            "ceiling_comparison_metrics.json"
        ),
        (
            "reports/hw02/raw/"
            "adversarial_results.json"
        ),
        (
            "reports/hw02/raw/"
            "adversarial_results.csv"
        ),
        (
            "reports/hw02/raw/"
            "adversarial_metrics.json"
        )
    ]

    missing = [
        path
        for path in required_files
        if not (
            PROJECT_ROOT
            / path
        ).is_file()
    ]

    record(
        "required_files",
        not missing,
        (
            "All required pre-report files exist."
            if not missing
            else f"Missing files: {missing}"
        )
    )


def check_frontend() -> None:
    """Verify responsive UI and interface states."""

    html_path = (
        PROJECT_ROOT
        / "code"
        / "web_application"
        / "index.html"
    )

    css_path = (
        PROJECT_ROOT
        / "code"
        / "web_application"
        / "styles.css"
    )

    script_path = (
        PROJECT_ROOT
        / "code"
        / "web_application"
        / "script.js"
    )

    html = html_path.read_text(
        encoding="utf-8"
    )

    css = css_path.read_text(
        encoding="utf-8"
    )

    script = script_path.read_text(
        encoding="utf-8"
    )

    state_ids = [
        "loadingState",
        "emptyState",
        "errorState"
    ]

    states_in_html = all(
        f'id="{state_id}"' in html
        for state_id in state_ids
    )

    states_in_script = all(
        state_id in script
        for state_id in state_ids
    )

    record(
        "frontend_states",
        (
            states_in_html
            and states_in_script
        ),
        (
            "Loading, empty, and error states "
            "exist and are controlled by JavaScript."
        )
    )

    responsive = (
        "@media" in css
        and "max-width: 450px" in css
    )

    record(
        "responsive_375px",
        responsive,
        (
            "CSS contains a mobile layout "
            "applicable at 375px."
        )
    )

    correct_api = (
        'const API_URL = "/api/trials";'
        in script
    )

    record(
        "frontend_api_url",
        correct_api,
        (
            "Frontend uses /api/trials."
            if correct_api
            else "Frontend API URL is incorrect."
        )
    )


def check_model_adapter() -> None:
    """Ensure graph nodes use ModelClient injection."""

    nodes_path = (
        PROJECT_ROOT
        / "code"
        / "agent_graph"
        / "nodes.py"
    )

    source = nodes_path.read_text(
        encoding="utf-8"
    )

    forbidden = [
        "ChatOpenAI",
        "ChatOllama",
        "ollama.Client",
        "from ollama import Client"
    ]

    passed = (
        "llm.complete" in source
        and not any(
            value in source
            for value in forbidden
        )
    )

    record(
        "model_adapter_usage",
        passed,
        (
            "Planner and Reviewer use the "
            "injected ModelClient adapter."
            if passed
            else (
                "A direct model-provider call "
                "may remain in nodes.py."
            )
        )
    )


def check_fastapi() -> None:
    """Test home, list, create, update, search, and delete."""

    unique_title = (
        f"Verification Trial {VERIFY_SEED}"
    )

    unique_sponsor = (
        f"Verification Sponsor {VERIFY_SEED}"
    )

    updated_title = (
        f"Updated Trial {VERIFY_SEED}"
    )

    updated_sponsor = (
        f"Updated Sponsor {VERIFY_SEED}"
    )

    original_id_one: dict[str, Any] | None = None
    created_id: int | None = None

    try:
        status, home, _ = http_request(
            "GET",
            "/"
        )

        record(
            "fastapi_home",
            (
                status == 200
                and "Clinical Trial Listings"
                in home
            ),
            f"GET / returned HTTP {status}."
        )

        status, text, _ = http_request(
            "GET",
            "/api/trials"
        )

        initial_trials = json.loads(
            text
        )

        record(
            "fastapi_list",
            (
                status == 200
                and isinstance(
                    initial_trials,
                    list
                )
                and len(initial_trials) > 0
            ),
            (
                "GET /api/trials returned "
                f"{len(initial_trials)} records."
            )
        )

        original_id_one = next(
            trial
            for trial in initial_trials
            if trial["id"] == 1
        )

        status, _, final_url = http_request(
            "POST",
            "/trials",
            form_data={
                "trial_title": unique_title,
                "sponsor_name": unique_sponsor,
                "submitter_email": (
                    "verify@example.edu"
                ),
                "trial_description": (
                    "This verification trial "
                    "contains more than "
                    "twenty-five characters."
                ),
                "trial_phase": "Phase I"
            }
        )

        _, text, _ = http_request(
            "GET",
            "/api/trials"
        )

        after_create = json.loads(
            text
        )

        created = next(
            (
                trial
                for trial in after_create
                if trial["trial_title"]
                == unique_title
            ),
            None
        )

        if created is not None:
            created_id = created["id"]

        create_passed = (
            status == 200
            and final_url.rstrip("/")
            == BASE_URL
            and created is not None
        )

        record(
            "fastapi_create_redirect",
            create_passed,
            (
                "Form creation redirected home "
                "and added the record."
            )
        )

        status, _, final_url = http_request(
            "POST",
            "/trials/1/update",
            form_data={
                "trial_title": updated_title,
                "sponsor_name": updated_sponsor
            }
        )

        _, text, _ = http_request(
            "GET",
            "/api/trials/1"
        )

        updated = json.loads(
            text
        )

        update_passed = (
            status == 200
            and final_url.rstrip("/")
            == BASE_URL
            and updated["trial_title"]
            == updated_title
            and updated["sponsor_name"]
            == updated_sponsor
        )

        record(
            "fastapi_update_id_1",
            update_passed,
            (
                "Record ID 1 was updated and "
                "the form redirected home."
            )
        )

        query = urlencode({
            "search": str(VERIFY_SEED)
        })

        status, text, _ = http_request(
            "GET",
            f"/api/trials?{query}"
        )

        matches = json.loads(
            text
        )

        search_passed = (
            status == 200
            and len(matches) >= 1
            and all(
                str(VERIFY_SEED)
                in (
                    trial["trial_title"]
                    + " "
                    + trial["sponsor_name"]
                )
                for trial in matches
            )
        )

        record(
            "fastapi_search",
            search_passed,
            (
                f"Search returned "
                f"{len(matches)} matching records."
            )
        )

        status, _, final_url = http_request(
            "POST",
            "/trials/delete-highest",
            form_data={}
        )

        _, text, _ = http_request(
            "GET",
            "/api/trials"
        )

        after_delete = json.loads(
            text
        )

        delete_passed = (
            status == 200
            and final_url.rstrip("/")
            == BASE_URL
            and created_id is not None
            and all(
                trial["id"] != created_id
                for trial in after_delete
            )
        )

        record(
            "fastapi_delete_highest",
            delete_passed,
            (
                "The highest-ID record was "
                "deleted and the form redirected home."
            )
        )

    except Exception as error:
        record(
            "fastapi_behavior_exception",
            False,
            (
                f"{type(error).__name__}: "
                f"{error}"
            )
        )

    finally:
        if original_id_one is not None:
            try:
                http_request(
                    "PUT",
                    "/api/trials/1",
                    json_data={
                        "trial_title": (
                            original_id_one[
                                "trial_title"
                            ]
                        ),
                        "sponsor_name": (
                            original_id_one[
                                "sponsor_name"
                            ]
                        )
                    }
                )

            except Exception:
                pass


def check_graph() -> None:
    """Run a deterministic LangGraph smoke test."""

    class DeterministicSmokeClient:
        """Small test double with the ModelClient interface."""

        def __init__(self) -> None:
            self.call_count = 0

        def complete(
            self,
            messages: list[dict[str, str]],
            tools: list[Any] | None = None,
            response_format: (
                dict[str, Any]
                | str
                | None
            ) = None
        ) -> SimpleNamespace:
            """Return valid Planner or Reviewer JSON."""

            del tools
            del response_format

            self.call_count += 1

            combined_prompt = " ".join(
                message.get(
                    "content",
                    ""
                )
                for message in messages
            )

            if (
                "semantic Reviewer"
                in combined_prompt
            ):
                content = json.dumps({
                    "approved": True,
                    "issues": []
                })

            else:
                content = json.dumps({
                    "tags": [
                        "sleep_quality",
                        "academic_performance",
                        "cognitive_outcomes"
                    ],
                    "summary": (
                        "Study examines sleep effects "
                        "on student academic and "
                        "cognitive outcomes."
                    )
                })

            return SimpleNamespace(
                content=content,
                input_tokens=10,
                output_tokens=10,
                total_tokens=20
            )

    try:
        input_data = read_json(
            REPORT_DIRECTORY
            / "cases"
            / "schema_input.json"
        )

        smoke_client = (
            DeterministicSmokeClient()
        )

        initial_state = initialize_state(
            title=input_data["title"],
            content=input_data["content"],
            email=input_data["email"],
            task=input_data["task"],
            llm=smoke_client,
            strict=input_data.get(
                "strict",
                True
            ),
            turn_ceiling=TURN_CEILING,
            force_reviewer_issue=False
        )

        captured_output = io.StringIO()

        started = time.perf_counter()

        with redirect_stdout(
            captured_output
        ):
            final_state = run_workflow(
                initial_state,
                show_stream=False
            )

        latency_ms = (
            time.perf_counter()
            - started
        ) * 1000

        graph_passed = (
            final_state.get("status")
            == "completed"
            and final_state.get(
                "completed"
            ) is True
            and final_state.get(
                "abandoned"
            ) is False
            and final_state.get(
                "turn_count"
            ) == 1
            and smoke_client.call_count == 2
        )

        record(
            "langgraph_finishes",
            graph_passed,
            (
                "Deterministic graph smoke test "
                "completed with "
                f"status={final_state.get('status')}, "
                "Planner attempts="
                f"{final_state.get('turn_count')}, "
                "model calls="
                f"{smoke_client.call_count}, "
                f"latency={latency_ms:.2f} ms."
            )
        )

        proposal = (
            PlannerProposal.model_validate(
                final_state.get(
                    "planner_proposal",
                    {}
                )
            )
        )

        schema_passed = (
            len(proposal.tags) == 3
            and len(
                proposal.summary.split()
            ) <= 25
        )

        record(
            "planner_schema_smoke_test",
            schema_passed,
            (
                "Deterministic Planner returned "
                f"{len(proposal.tags)} tags and "
                f"a {len(proposal.summary.split())}"
                "-word summary."
            )
        )

    except Exception as error:
        record(
            "langgraph_smoke_exception",
            False,
            (
                f"{type(error).__name__}: "
                f"{error}"
            )
        )


def check_experiments() -> None:
    """Verify all required experiment results."""

    try:
        schema_payload = read_json(
            RAW_DIRECTORY
            / "schema_validation_results.json"
        )

        ceiling_payload = read_json(
            RAW_DIRECTORY
            / "ceiling_comparison_results.json"
        )

        adversarial_payload = read_json(
            RAW_DIRECTORY
            / "adversarial_results.json"
        )

        schema_results = schema_payload[
            "results"
        ]

        ceiling_results = ceiling_payload[
            "results"
        ]

        adversarial_results = (
            adversarial_payload[
                "results"
            ]
        )

        ceiling_two_count = sum(
            result["turn_ceiling"] == 2
            for result in ceiling_results
        )

        ceiling_ten_count = sum(
            result["turn_ceiling"] == 10
            for result in ceiling_results
        )

        total = (
            len(schema_results)
            + len(ceiling_results)
            + len(adversarial_results)
        )

        counts_passed = (
            len(schema_results) == 30
            and ceiling_two_count == 20
            and ceiling_ten_count == 20
            and len(adversarial_results) == 5
            and total == 75
        )

        record(
            "experiment_counts",
            counts_passed,
            (
                f"Schema={len(schema_results)}, "
                f"ceiling2={ceiling_two_count}, "
                f"ceiling10={ceiling_ten_count}, "
                "adversarial="
                f"{len(adversarial_results)}, "
                f"total={total}."
            )
        )

        normal_results = (
            schema_results
            + ceiling_results
        )

        invalid_proposals = 0

        for result in normal_results:
            try:
                PlannerProposal.model_validate(
                    result[
                        "planner_proposal"
                    ]
                )

            except Exception:
                invalid_proposals += 1

        record(
            "stored_normal_schemas",
            invalid_proposals == 0,
            (
                "Invalid normal stored "
                f"proposals: {invalid_proposals}."
            )
        )

        schema_metrics = read_json(
            RAW_DIRECTORY
            / "schema_validation_metrics.json"
        )

        ceiling_metrics = read_json(
            RAW_DIRECTORY
            / "ceiling_comparison_metrics.json"
        )

        adversarial_metrics = read_json(
            RAW_DIRECTORY
            / "adversarial_metrics.json"
        )

        metrics_passed = (
            schema_metrics.get(
                "runCount"
            ) == 30
            and ceiling_metrics.get(
                "recommendedCeiling"
            ) in {
                2,
                10
            }
            and adversarial_metrics.get(
                "runCount"
            ) == 5
        )

        record(
            "experiment_metrics",
            metrics_passed,
            (
                "Metric files contain the required "
                "run counts and deployment choice."
            )
        )

        hit_count = adversarial_metrics.get(
            "hitTurnCeilingCount",
            0
        )

        record(
            "adversarial_summary",
            (
                adversarial_metrics.get(
                    "runCount"
                ) == 5
            ),
            (
                f"Adversarial ceiling hits: "
                f"{hit_count}/5."
            )
        )

    except Exception as error:
        record(
            "experiment_results_exception",
            False,
            (
                f"{type(error).__name__}: "
                f"{error}"
            )
        )


def write_verification() -> dict[str, Any]:
    """Write the final verification object."""

    passed = all(
        check["passed"]
        for check in checks
    )

    result = {
        "homework": HOMEWORK_NUMBER,
        "assignment": "DATA-260 Homework 2",
        "student": "Sanjana Thummalapalli",
        "sid4": SID4,
        "commitHash": get_commit_hash(),
        "modelConfiguration": {
            "experimentModel": MODEL,
            "experimentTemperature": 0.7,
            "interactiveTemperature": TEMPERATURE,
            "numCtx": NUM_CTX,
            "numPredict": NUM_PREDICT,
            "deploymentTurnCeiling": (
                TURN_CEILING
            ),
            "portBase": PORT_BASE,
            "graphSmokeTestClient": (
                "deterministic test double"
            ),
            "graphSmokeTestPurpose": (
                "Verify graph routing, schema, "
                "state updates, and termination "
                "without nondeterministic model output."
            )
        },
        "seed": SEED,
        "verifySeed": VERIFY_SEED,
        "timestamp": utc_timestamp(),
        "passed": passed,
        "checks": checks
    }

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    OUTPUT_PATH.write_text(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    return result


def main() -> None:
    """Run all Homework 2 smoke tests."""

    checks.clear()

    temporary_backend: (
        subprocess.Popen[str]
        | None
    ) = None

    check_required_files()
    check_frontend()
    check_model_adapter()

    try:
        temporary_backend = start_backend()

        if backend_responds():
            check_fastapi()
        else:
            record(
                "fastapi_behavior",
                False,
                "FastAPI was unavailable."
            )

    except Exception as error:
        record(
            "fastapi_smoke_exception",
            False,
            (
                f"{type(error).__name__}: "
                f"{error}"
            )
        )

    finally:
        stop_backend(
            temporary_backend
        )

    check_graph()
    check_experiments()

    result = write_verification()

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False
        )
    )

    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()