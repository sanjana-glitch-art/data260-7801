# Homework 6 Metrics

## Student Configuration

| Setting | Value |
|---|---|
| Student | Sanjana Thummalapalli |
| SID4 | 7801 |
| Verify seed | 267801 |
| Domain | Clinical Trial Listings |
| MongoDB database | s7801_doc |
| Ollama model | qwen3:4b |
| Embedding model | sentence-transformers/all-MiniLM-L6-v2 |
| API port | 8601 |

## Part 1: MongoDB Document Storage

The clinical-trial document API used the `trial_documents` MongoDB collection. The collection applied schema validation for required fields, trial phase, recruitment status, dates, and string-length constraints.

The following API operations were tested:

| Operation | Endpoint | Result |
|---|---|---|
| Create | POST `/api/document-trials` | Passed |
| Read all | GET `/api/document-trials` | Passed |
| Read one | GET `/api/document-trials/{document_id}` | Passed |
| Update | PUT `/api/document-trials/{document_id}` | Passed |
| Delete | DELETE `/api/document-trials/{document_id}` | Passed |
| Invalid document rejection | POST `/api/document-trials` | Passed |

Raw evidence is stored in `reports/hw06/raw/part1_crud_results.json`.

## Part 2: Conversational Memory

The conversational-memory implementation used three MongoDB collections:

| Collection | Purpose |
|---|---|
| `messages` | Stores user and assistant conversation turns |
| `summaries` | Stores session and lifetime summaries |
| `episodes` | Stores durable facts with embeddings for retrieval |

The required ten-message test produced:

| Metric | Result |
|---|---:|
| User messages submitted | 10 |
| Total stored user and assistant messages | 20 |
| Messages returned in memory snapshot | 16 |
| Session summary created | Yes |
| Lifetime summary created | Yes |
| Episodic memories created | 10 |
| Daily aggregate message count | 20 |

Raw evidence is stored in:

- `reports/hw06/raw/part2_conversation.json`
- `reports/hw06/raw/memory_snapshot.json`
- `reports/hw06/raw/aggregate_snapshot.json`
- `reports/hw06/raw/chat_turn_metrics.csv`
- `reports/hw06/raw/chat_turn_metrics.jsonl`

## Part 3: Short-Term Memory Experiment

### Experiment Configuration

| Setting | Value |
|---|---:|
| Fixed conversation messages | 30 |
| Memory probes | 5 |
| Short-term values | 4, 12, and 30 |
| Additional configuration | Compression policy |
| Model | qwen3:4b |
| Temperature | 0.0 |

### Results

| Configuration | Mean Prompt Tokens | Mean Latency (ms) | Mean Probe Quality (1–5) | Estimated Cost per 10,000 Conversations |
|---|---:|---:|---:|---:|
| SHORT_TERM_N=4 | 869.433 | 12,144.905 | 3.8 | $500.83 |
| SHORT_TERM_N=12 | 1,479.400 | 17,831.934 | 4.2 | $683.82 |
| SHORT_TERM_N=30 | 1,059.467 | 12,478.687 | 1.4 | $557.84 |
| Compression policy | 934.167 | 12,065.704 | 3.8 | $520.25 |

### Compression Results

| Metric | Result |
|---|---:|
| Prompt-token savings | 11.83% |
| Probe-quality improvement over N=30 | 2.4 points |
| Compression mean probe quality | 3.8 |
| Compression mean latency | 12,065.704 ms |

### Interpretation

`SHORT_TERM_N=12` produced the highest mean probe quality of 4.2. It preserved enough recent conversational context to answer most memory probes correctly, but it also had the largest prompt size, highest mean latency, and highest estimated cost.

`SHORT_TERM_N=4` reduced prompt tokens and latency while maintaining a probe-quality score of 3.8. This demonstrates that a smaller recent-message window can remain effective when summaries and episodic memories preserve durable facts.

`SHORT_TERM_N=30` produced the weakest probe-quality score of 1.4. A larger nominal short-term window did not improve recall because the model context limit and competing prompt content reduced the usefulness of the additional history. More context was therefore not automatically better context.

The compression policy achieved the lowest mean latency, retained a probe-quality score of 3.8, and saved 11.83% of prompt tokens compared with the uncompressed comparison. This configuration provided the strongest balance between memory quality and computational cost.

For applications prioritizing maximum recall quality, `SHORT_TERM_N=12` is recommended. For applications prioritizing lower latency and prompt cost while retaining good recall, the compression policy is recommended.

Raw experiment evidence is stored in:

- `reports/hw06/raw/short_term_sweep_results.json`
- `reports/hw06/raw/short_term_sweep_results.csv`
- `reports/hw06/raw/memory_probe_results.json`
- `reports/hw06/raw/compression_results.json`
- `reports/hw06/raw/memory_experiment_metrics.json`

## Part 4: File-Based Memory

### Consolidation Metrics

| Metric | Result |
|---|---:|
| Original fact lines | 55 |
| Exact duplicates detected | 6 |
| Contradictions explicitly resolved | 3 |
| Lines immediately after consolidation | 35 |
| Final lines after `/dream` | 36 |
| Required maximum | Fewer than 40 |
| Requirement passed | Yes |

The deliberately contradictory facts covered:

1. Phase II versus Phase III preference
2. San Jose versus Santa Clara location preference
3. Five-message versus ten-message summary interval

The consolidation process preserved an explicit explanation for every resolved conflict rather than silently deleting contradictory information.

### Supported File-Memory Commands

| Command | Purpose | Result |
|---|---|---|
| `/memory` | Display current durable memory and consolidation status | Passed |
| `/compact` | Merge duplicates, resolve conflicts, and report before/after counts | Passed |
| `/dream` | Extract durable facts from recent conversation | Passed |
| `/help` | Display available commands | Passed |

### AGENT.md Compliance

The expanded `AGENT.md` includes instructions in five categories:

- Project description
- Technology stack
- Coding conventions
- Testing approach
- Prohibited actions

The `filter_trials_by_phase` function was compiled and tested. It follows the instructions by using type hints, descriptive names, a docstring, input validation, a predictable response structure, and no direct model access.

## Final Verification

| Check | Result |
|---|---|
| Required files | Passed |
| Supported Python version | Passed |
| AGENT.md categories and instructions | Passed |
| Original and consolidated memory versions | Passed |
| File-memory functions and commands | Passed |
| AGENT.md-compliant function | Passed |
| FastAPI routes | Passed |
| MongoDB collections | Passed |
| Experiment case counts | Passed |
| Raw JSON parsing | Passed |
| Experiment configurations and metrics | Passed |
| Reproducibility run log | Passed |
| Overall verification | Passed |

The machine-readable verification result is stored in `reports/hw06/verification.json`.