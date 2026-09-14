# DATA-260 Homework 2 Metrics

## Student Configuration

| Setting | Value |
|---|---:|
| Student | Sanjana Thummalapalli |
| SID4 | 7801 |
| PORT_BASE | 8601 |
| PREFIX | s7801 |
| SEED | 7801 |
| VERIFY_SEED | 267801 |
| DOMAIN_ID | 1 |
| Domain | Clinical Trial Listings |

## Model Configuration

| Setting | Value |
|---|---|
| Model | qwen3:4b |
| Temperature | 0.7 |
| Context size | 4096 |
| Maximum predicted tokens | 256 |
| Model adapter | `src/model_client.py` |
| Schema validator | Pydantic |
| Schema-run turn ceiling | 10 |
| Ceiling comparison | 2 versus 10 |
| Adversarial turn ceiling | 2 |

The local `qwen3:4b` model was used as the documented substitute established during Homework 1. Every Planner and Reviewer model call was routed through `src/model_client.py`.

## Frozen Schema Input

The same frozen input was used for all 30 schema-validation runs and all 40 turn-ceiling comparison runs. It is stored at `reports/hw02/cases/schema_input.json`.

The input file was created before running the experiments and was not changed between runs.

## Schema-Validation Experiment

The graph was executed 30 times on the exact same frozen input. Planner output was validated using Pydantic. A valid proposal required:

- Exactly three tags
- Three distinct tags
- Every tag to contain between 3 and 30 characters
- A nonempty summary
- A summary containing no more than 25 whitespace-separated words
- No unexpected JSON fields

| Outcome over 30 runs | Count | Mean latency (ms) |
|---|---:|---:|
| Valid first attempt | 30 | 8,638.34 |
| Valid after 1 retry | 0 | N/A |
| Valid after 2 or more retries | 0 | N/A |
| Hit turn ceiling | 0 | N/A |
| **Total** | **30** | **8,638.34 overall** |

All 30 runs produced an acceptable result on the first Planner attempt. No schema-validation retry was required, and no run reached the turn ceiling.

## Turn-Ceiling Comparison

The same frozen input and model settings were used for both groups. The graph was run 20 times with a turn ceiling of 2 and 20 times with a turn ceiling of 10.

| Metric | Ceiling 2 | Ceiling 10 |
|---|---:|---:|
| Runs | 20 | 20 |
| Completed | 20 | 20 |
| Abandoned | 0 | 0 |
| Completion rate | 100.00% | 100.00% |
| Mean latency | 8,729.50 ms | 6,005.43 ms |
| Mean completed-run latency | 8,729.50 ms | 6,005.43 ms |
| Mean Planner attempts | 1.00 | 1.00 |

### Deployment Choice

I selected a turn ceiling of **2** for deployment.

Both ceilings achieved a 100% completion rate, and both required an average of one Planner attempt. Therefore, the larger ceiling did not improve completion or reduce the number of attempts in this experiment. A ceiling of 2 provides the same measured reliability while placing a tighter upper bound on model calls, latency, and correction-loop resource usage.

Ceiling 10 had a lower observed mean latency, but both groups completed in one attempt. The difference therefore cannot reasonably be attributed to the ceiling itself. Model warm-up, caching, GPU state, and background system load may have affected timing.

## Adversarial Experiment

The adversarial input is stored at `reports/hw02/cases/adversarial_input.json`.

It contains prompt-injection-style instructions embedded inside untrusted title and content fields. Those instructions attempt to make the Planner return:

- Only two tags
- Tags longer than 30 characters
- An unexpected JSON field
- A summary longer than 25 words

The graph was run five times with a turn ceiling of 2.

| Metric | Result |
|---|---:|
| Runs | 5 |
| Completed | 0 |
| Hit turn ceiling | 5 |
| Hit-ceiling rate | 100.00% |
| Preferred four-of-five threshold reached | Yes |
| Mean latency | 29,699.65 ms |

The adversarial input reached the ceiling in all five runs. This demonstrates that the graph stops safely instead of entering an infinite correction loop. The observed result was 5 out of 5 runs; it is reported as an experimental observation rather than a universal claim that the behavior will always be deterministic.

### Why the Input Causes Difficulty

The title and content contain instructions that conflict with the system-level schema requirements. Although the values are supposed to be treated as clinical-trial data, the local model may interpret the embedded text as instructions. The Pydantic validator rejects malformed output, while the Reviewer may reject proposals influenced by the adversarial instructions. Repeated failures then consume both permitted Planner attempts.

### Proposed Fix

A stronger implementation would clearly delimit title and content as untrusted data and explicitly instruct the model never to follow commands found inside those fields. Additional input preprocessing could flag common prompt-injection phrases before the model call. A deterministic fallback could also generate safe domain tags when all model attempts fail.

The turn ceiling must remain in place even after these improvements because it provides protection against unexpected or persistent failures.

## Loop-Safety Demonstration

A separate forced-correction test was used to demonstrate graph routing. In that test, the Reviewer deliberately returned an issue after each proposal. The graph routed back through Supervisor and Planner and then ended with `status="abandoned"` after two Planner attempts.

This test demonstrates:

- Shared state persists across nodes.
- Reviewer feedback is available to the next Planner attempt.
- Supervisor increments the Planner-attempt counter.
- Conditional edges route rejected work back for correction.
- The turn ceiling prevents infinite loops.

## Reviewer Verification Issue

During initial testing, the model Reviewer incorrectly claimed that a valid summary exceeded the 25-word limit. Deterministic Python counting showed that the summary contained fewer than 25 whitespace-separated words, and Pydantic had correctly accepted it.

The Reviewer prompt was updated so that Pydantic remains authoritative for mechanical schema requirements. The Reviewer now receives the deterministic word count and reviews semantic relevance and factual support rather than recalculating validated constraints.

## Raw Data

### Schema validation

- `reports/hw02/raw/schema_validation_results.json`
- `reports/hw02/raw/schema_validation_results.csv`
- `reports/hw02/raw/schema_validation_metrics.json`

### Ceiling comparison

- `reports/hw02/raw/ceiling_comparison_results.json`
- `reports/hw02/raw/ceiling_comparison_results.csv`
- `reports/hw02/raw/ceiling_comparison_metrics.json`

### Adversarial experiment

- `reports/hw02/raw/adversarial_results.json`
- `reports/hw02/raw/adversarial_results.csv`
- `reports/hw02/raw/adversarial_metrics.json`

## Summary

The normal frozen input was reliable under the tested configuration: all 30 schema-validation runs and all 40 ceiling-comparison runs completed successfully. The adversarial input reached the configured ceiling in all five runs, confirming that the loop-safety mechanism stopped repeated correction attempts. Based on equal completion rates and equal mean attempt counts, ceiling 2 was selected for deployment.