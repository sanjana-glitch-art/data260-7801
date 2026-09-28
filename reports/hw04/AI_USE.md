# Homework 4 AI Use Disclosure

## Student

- Name: Sanjana Thummalapalli
- SID4: 7801
- Course: DATA 260
- Assignment: Homework 4

## AI Tools Used

ChatGPT/Codex was used as a development assistant during Homework 4.

The local Ollama model `qwen3:4b` was also used as the generation model for the RAG experiment.

## How AI Was Used

ChatGPT/Codex assisted with:

- Interpreting the Homework 4 requirements.
- Connecting the React frontend to the FastAPI JSON API.
- Implementing password hashing and opaque server-side sessions.
- Creating the 180-request performance experiment.
- Troubleshooting Python imports, Docker configuration, PowerShell commands, and Ollama memory errors.

## Student Validation and Corrections

All suggested code was reviewed and executed locally.

Several corrections were made during testing:

- Python package imports were fixed by adding `code/__init__.py` and running scripts with `python -m`.
- Docker and MySQL connectivity were verified before database initialization.
- Ollama GPU-memory errors were addressed by lowering context size, reducing chunk size, and using partial GPU offloading.
- The initial RAG responses were truncated before producing final answers.
- Structured JSON output was added to the RAG experiment.
- The corrected RAG experiment was rerun for all 42 model calls.
- Database, N+1, index, authentication, and RAG results were generated locally and inspected.

## What AI Did Not Do

The experimental measurements were not invented by the AI assistant.

All reported values came from the locally generated files in:

- `reports/hw04/raw/n_plus_one_results.json`
- `reports/hw04/raw/n_plus_one_results.csv`
- `reports/hw04/raw/n_plus_one_metrics.json`
- `reports/hw04/raw/index_experiment.json`
- `reports/hw04/raw/rag_results.json`
- `reports/hw04/raw/rag_results.csv`
- `reports/hw04/raw/rag_metrics.json`

The final code, screenshots, Git repository, and submitted report were reviewed by the student.