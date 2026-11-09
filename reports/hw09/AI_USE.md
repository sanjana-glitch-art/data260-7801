@'
# AI Use Statement

## What I Used AI For

I used an AI assistant to help interpret the Homework 9 requirements, plan the Redis and agent architecture, draft portions of the Python implementation, generate test commands, troubleshoot errors, and organize the final report structure.

The AI assistant helped with:

- Adapting the provided Redis example to the Clinical Trials domain.
- Designing the Redis-backed clinical-trial view counter.
- Creating a Redis HNSW semantic vector index.
- Designing the 40-case labeled threshold dataset.
- Creating the threshold sweep, cost model, stale-cache experiment, and invalidation logic.
- Designing the Answering Agent, Evaluator Agent, reusable lesson memory, validation gate, and four system variants.
- Preparing compilation, Ruff, runtime, and verification commands.

## What I Personally Did

I personally:

- Created and managed the Git branches.
- Installed and configured Redis Stack in Docker.
- Ran the MySQL, Kafka, Redis, Ollama, and FastAPI services.
- Executed every experiment.
- Inspected the Redis vector index and prefixed keys.
- Ran the 25-access view-counter demonstration.
- Ran the semantic-cache queries and collected actual latency measurements.
- Committed `cache_cases.yaml` before observing threshold results.
- Ran the five-threshold experiment.
- Verified the false-hit and stale-cache behavior.
- Ran the Answering Agent and Evaluator Agent experiments.
- Inspected the generated lessons and held-out test results.
- Ran `py_compile`, Ruff, pre-commit, and the final 15-check verification.

## AI Output That Required Correction

Some generated PowerShell here-string wrapper markers were accidentally included inside output files. For example, a JSON file contained the literal `@'` marker and therefore failed JSON parsing.

The initial verification script assumed UTF-8 log files, but PowerShell `Tee-Object` created one log in UTF-16. This caused a `UnicodeDecodeError`.

Ruff also identified nested conditional logic that required manual simplification.

## How I Detected the Problems

I detected and corrected these issues using:

- `python -m py_compile`
- `python -m ruff check`
- `pre-commit run --all-files`
- JSON parsing with Python and PowerShell
- Redis CLI commands
- MySQL queries
- Docker logs
- The final `code.verify_hw9` verification script

## Corrections I Made

I removed invalid wrapper markers, regenerated the affected JSON file, updated the verification script to support UTF-8 and UTF-16 logs, and simplified the conditional code required by Ruff.

I also verified that all Redis keys begin with `s7801`, that the Redis vector index uses 384-dimensional FLOAT32 cosine embeddings, and that the database record modified during the stale-cache experiment was restored.

## Final Verification

The final automated verification passed all 15 checks with an overall result of PASS.
'@ | Set-Content reports\hw09\AI_USE.md -Encoding utf8