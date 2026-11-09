# DATA-260 Homework 8 Metrics

Student: Sanjana Thummalapalli  
SID4: 7801  
Domain: Clinical Trials  
PREFIX: s7801  
SEED: 7801  
VERIFY_SEED: 267801  

## Part 1: Kafka Request/Response

| Check | Result |
|---|---:|
| CREATE_CLINICAL_TRIAL succeeded | PASS |
| UUID entity ID generated | PASS |
| GET_CLINICAL_TRIAL returned the created entity | PASS |
| Correlation ID preserved | PASS |
| Missing entity returned a clean error | PASS |
| Request topic | `s7801_entity_requests` |
| Response topic | `s7801_entity_responses` |

## Part 2: Three-Agent Pipeline

| Stage | Input topic | Output topic | Result |
|---|---|---|---:|
| Planner | `s7801_inbox` | `s7801_tasks` | PASS |
| Writer | `s7801_tasks` | `s7801_drafts` | PASS |
| Reviewer | `s7801_drafts` | `s7801_final` | PASS |
| Final status | — | — | `approved` |
| Correlation ID preserved through all stages | — | — | PASS |

## Part 3: Failure Behavior

| Failure scenario | Before fix | After fix |
|---|---|---|
| Duplicate delivery | Replaying one correlation ID generated two different entity IDs, causing a duplicate side effect. | The worker cached the response by correlation ID. Replay returned the original entity ID with `idempotent_replay: true`; no additional side effect occurred. |
| Consumer killed mid-work | A Writer could terminate after receiving a task but before completing it. | The offset was not committed before successful processing. After restart, Kafka redelivered the same correlation ID and the Writer completed and committed it. |
| Poison message | Invalid input could raise an exception and stop the Writer, blocking later messages. | The Writer retried twice, failed on attempt 3, sent the message to `s7801_dead_letter`, committed the poison offset, and processed the following valid message. |
| Two partitions/two consumers | Twenty unkeyed related messages used partitions 0 and 1 and two Writers. Completion order was not preserved. | Using the clinical-trial entity key placed all 20 related messages in one partition and preserved order from 0 through 19. |

## Duplicate Delivery Results

| Metric | Before | After |
|---|---:|---:|
| Same correlation ID replayed | Yes | Yes |
| Same entity ID returned | No | Yes |
| Duplicate side effect | Yes | No |
| Idempotency passed | No | Yes |

## Poison Message Results

| Metric | Result |
|---|---:|
| Maximum attempts | 3 |
| Retry events | 2 |
| Sent to `s7801_dead_letter` | Yes |
| Poison offset committed | Yes |
| Following valid message processed | Yes |
| Overall | PASS |

## Ordering Results

| Metric | Before: no key | After: entity key |
|---|---|---|
| Messages | 20 | 20 |
| Task partitions used | 0 and 1 | 0 |
| Writer instances | 2 | 1 |
| Completion order | `1,3,5,7,0,9,11,13,15,2,17,19,4,6,8,10,12,14,16,18` | `0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19` |
| Ordering preserved | No | Yes |
| Overall | Expected disorder demonstrated | PASS |

## HW2 In-Process Graph vs. Kafka

### Benefits gained

1. **Independent scaling:** Planner, Writer, and Reviewer are separate consumers. Additional Writer instances can process different Kafka partitions without scaling the entire application.

2. **Decoupled failure and durable work:** A temporary Writer failure does not require the Planner to repeat its work. Kafka retains the uncommitted task and redelivers it after the Writer restarts.

### New responsibilities

1. **Duplicate delivery and idempotency:** Kafka can deliver a message again when processing finishes but offset commit does not. The application must use correlation IDs and idempotency logic to prevent duplicate side effects.

2. **Ordering, retries, and offset management:** Ordering is guaranteed only within a partition. The application must select appropriate message keys, commit offsets after success, bound retries, and route poison messages to a dead-letter topic.

## Evidence Files

- `raw/pipeline_result.json`
- `raw/duplicate_before.json`
- `raw/duplicate_after.json`
- `raw/consumer_death_writer_test.log`
- `raw/poison_message_results.json`
- `raw/poison_writer.log`
- `raw/ordering_results.json`
- `raw/ordering_results.csv`

## JMeter Load Test

Configuration: 100 users, 10-second ramp-up, one request per user.

| Metric | Result |
|---|---:|
| Samples | 100 |
| Average response time | 72 ms |
| Minimum response time | 63 ms |
| Maximum response time | 169 ms |
| Error rate | 0.00% |
| Throughput | 10.0 requests/second |
| Duration | 10 seconds |
| Result | PASS |

All 100 requests successfully created clinical-trial entities through the FastAPI-to-Kafka request/response service. No HTTP or Kafka request errors were observed.