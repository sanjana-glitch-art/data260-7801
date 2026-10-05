# Homework 5 Metrics

## Student Configuration

| Setting | Value |
|---|---:|
| Student | Sanjana Thummalapalli |
| SID4 | 7801 |
| PORT_BASE | 8601 |
| PREFIX | s7801 |
| VERIFY_SEED | 267801 |
| Domain | Clinical Trial Listings |
| Local model | qwen3:4b |

## Database Migration

| Metric | Result |
|---|---:|
| Clinical-trial records | 5,000 |
| Sponsor records | 9 |
| Trials connected to sponsors | 5,000 |
| New relational table | sponsors |
| Foreign key | clinical_trials.sponsor_id |
| Additional identifier | clinical_trials.trial_code |
| Additional numeric field | clinical_trials.enrollment_target |

The migration normalized sponsor information into a separate table and connected every clinical-trial record to a sponsor through a foreign key.

## MCP Servers

### MealDB MCP Server

The MealDB MCP server exposes four tools for searching and retrieving meal information through an external API.

### Clinical-Trial MCP Server

| Tool | Purpose |
|---|---|
| search_trials | Search clinical trials by title or related text |
| trial_details | Retrieve one clinical trial by ID |
| trial_phase_summary | Count clinical trials grouped by phase |

All domain tools return a consistent response envelope containing `ok`, `data`, and `error`.

Invalid inputs return `ok: false`, no data, and a descriptive error message.

## Retry Configuration

| Setting | Value |
|---|---:|
| Maximum attempts | 3 |
| Timeout per attempt | 3.0 seconds |
| First retry delay | 0.025 seconds |
| Second retry delay | 0.050 seconds |
| Backoff strategy | Exponential |
| Verification seed | 267801 |

## Fault-Injection Experiment

The experiment performed 50 calls at each injected-failure rate, producing 150 total records.

| Failure rate | Calls | Successful | Success rate | Retried calls | Mean latency | p99 latency |
|---:|---:|---:|---:|---:|---:|---:|
| 0% | 50 | 50 | 100.0% | 0 | 8.872 ms | 12.712 ms |
| 20% | 50 | 49 | 98.0% | 7 | 19.170 ms | 84.758 ms |
| 50% | 50 | 47 | 94.0% | 23 | 31.251 ms | 90.977 ms |

## Fault-Injection Interpretation

At a 0% injected-failure rate, every call completed successfully without a retry. At 20%, seven calls required retries, and the final success rate remained 98%. At 50%, 23 calls required retries, while 47 of 50 calls still succeeded.

The retry mechanism recovered from most temporary failures. Mean and p99 latency increased with the failure rate because failed attempts introduced backoff delays and additional database operations. The three-attempt limit prevented calls from retrying indefinitely.

## Agent Scenario Results

| Scenario | Steps | Tool calls | Stop reason | Latency |
|---|---:|---:|---|---:|
| Sleep-related trial search | 2 | 1 | normal_completion | 29,717.352 ms |
| Trial ID 1 details | 2 | 1 | normal_completion | 9,863.639 ms |
| Trial phase aggregation | 3 | 2 | normal_completion | 11,625.893 ms |
| Submitter-email privacy request | 1 | 1 | safety_rule_block | 3,756.577 ms |

## Agent Model Statistics

| Metric | Result |
|---|---:|
| Model | qwen3:4b |
| Scenarios | 4 |
| Model turns | 8 |
| Cumulative input tokens | 2,282 |
| Cumulative output tokens | 792 |
| Cumulative total tokens | 3,074 |
| Total tool calls | 5 |

The search scenario found three sleep-related trials. The detail scenario retrieved the title, phase, sponsor, and enrollment target for clinical trial ID 1.

The phase-summary scenario demonstrated a correction loop involving two tool calls. The privacy scenario stopped because the requested submitter email was protected by the application safety rule.

## Deterministic Testing

The offline tool tests cover:

- Valid and invalid trial searches
- Valid and invalid trial-detail requests
- Valid and invalid phase-summary requests
- Unknown tool names
- Submitter-email safety blocking
- Maximum-step termination using MockModel

The maximum-step test produced:

| Metric | Result |
|---|---:|
| Step count | 2 |
| Tool-call count | 2 |
| Stop reason | max_steps |

## Raw Evidence

The machine-readable evidence is stored in:

- `reports/hw05/raw/fault_injection_results.json`
- `reports/hw05/raw/fault_injection_results.csv`
- `reports/hw05/raw/fault_injection_metrics.json`
- `reports/hw05/raw/retry_demonstration.json`
- `reports/hw05/raw/agent_runs.jsonl`
- `reports/hw05/raw/agent_metrics.json`