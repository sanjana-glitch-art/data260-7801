@'
# Homework 9 Metrics

Student: Sanjana Thummalapalli  
SID4: 7801  
PREFIX: s7801  
Domain: Clinical Trials

## Part 1: Redis View Counter

| Metric | Result |
|---|---:|
| Total simulated accesses | 25 |
| Redis final count | 25 |
| Database final persisted count | 20 |
| Database synchronization interval | 10 accesses |
| Synchronizations observed | Counts 10 and 20 |
| Result | PASS |

Redis key format:

`S7801:views:clinical_trial:<trial_id>`

Actual implementation uses the lowercase configured prefix:

`s7801:views:clinical_trial:<trial_id>`

## Part 2: Semantic Response Cache

| Metric | Result |
|---|---:|
| Queries | 10 |
| Cache hits | 3 |
| Cache misses | 7 |
| Cache hit rate | 30.00% |
| Average cached latency | 7.922 ms |
| Average non-cached latency | 7105.463 ms |
| Starting similarity threshold | 0.85 |
| Embedding model | all-MiniLM-L6-v2 |
| Embedding dimensions | 384 |
| Redis vector algorithm | HNSW |
| Distance metric | Cosine |
| Result | PASS |

## Part 3: Threshold Sweep

| Threshold | Hit rate | False-hit rate | Mean latency | Total cost |
|---:|---:|---:|---:|---:|
| 0.75 | 55.00% | 30.00% | 3204.516 ms | $6.36 |
| 0.80 | 50.00% | 30.00% | 3559.369 ms | $6.40 |
| 0.85 | 25.00% | 0.00% | 5335.839 ms | $0.60 |
| 0.90 | 25.00% | 0.00% | 5335.744 ms | $0.60 |
| 0.95 | 25.00% | 0.00% | 5337.649 ms | $0.60 |

### Cost Model

- Cache-miss cost: $0.02 per miss.
- False-hit support/correction cost: $1.00 per false hit.
- False hits are assigned a larger cost because an incorrect clinical-trial response may require user support and correction.
- Recommended production threshold: 0.90.
- The 0.90 threshold tied for the lowest total cost, produced no false hits, and had slightly lower observed mean latency than 0.85.

## False-Hit Example

| Field | Value |
|---|---|
| Threshold | 0.75 |
| Similarity | 0.830932 |
| Cached query | What phase is the sleep quality trial? |
| Incoming query | What is the enrollment target of the sleep quality trial? |
| Incorrect cached answer | The sleep quality trial is Phase II. |
| Correct answer | The sleep quality trial has an enrollment target of 120. |

The embedding model confused these questions because both contain the same trial name and share most query terms, even though they request different attributes.

## Stale-Cache Invalidation

| Metric | Result |
|---|---:|
| Original enrollment target | 120 |
| Updated enrollment target | 145 |
| Stale cached value returned | 120 |
| Stale hit demonstrated | Yes |
| Stale entries deleted | 1 |
| Cache miss after invalidation | Yes |
| Refreshed answer correct | Yes |
| Original database value restored | Yes |
| Result | PASS |

The implemented strategy deletes semantic-cache entries whose stored data-version marker differs from the current relational-data version.

## Part 4: Self-Improving Agents

### Validation

| Metric | Result |
|---|---:|
| Validation correct before lesson | 4/8 |
| Validation correct after lesson | 8/8 |
| Improved cases | 4 |
| Regressions | 0 |
| Lesson retained | Yes |
| Lesson use count | 11 |

### Held-Out Test Results

| Variant | Correct | Incorrect | Average attempts | Average latency |
|---|---:|---:|---:|---:|
| Baseline | 4 | 4 | 1.000 | 0.022 ms |
| Evaluator Repair | 8 | 0 | 1.500 | 0.028 ms |
| Lesson Memory | 8 | 0 | 1.000 | 3.357 ms |
| Validated Improvement | 8 | 0 | 1.000 | 3.460 ms |

## Final Verification

| Metric | Result |
|---|---:|
| Checks passed | 15/15 |
| Overall result | PASS |
'@ | Set-Content reports\hw09\METRICS.md -Encoding utf8