# AI Use Disclosure

## Student

Sanjana Thummalapalli  
SID4: 7801  
Course: DATA-260  
Assignment: Homework 6

## AI Tools Used

I used ChatGPT/Codex as a development assistant while completing Homework 6. I also used the local Ollama model `qwen3:4b` as the model required by the assignment experiments.

## How AI Was Used

ChatGPT/Codex was used to:

- Interpret the Homework 6 requirements and divide the work into implementation stages.
- Suggest the MongoDB Docker Compose configuration.
- Draft MongoDB collection validators and indexes.
- Help create FastAPI CRUD endpoints for document-based clinical-trial records.
- Help design message, summary, and episodic-memory collections.
- Draft memory-service functions for short-term, summary, and episodic retrieval.
- Help construct the 30-message memory experiment and five memory probes.
- Debug Windows PowerShell, Docker, MongoDB, FastAPI, Python, and Ollama errors.
- Draft file-memory loading, prompt construction, consolidation checks, and command handling.
- Help create the final verification script.
- Organize experiment metrics and report content.

## Example Prompts

Examples of prompts used during development included:

1. “Explain the assignment step by step and tell me what files I need to create.”
2. “Give me the complete MongoDB memory service code using the existing ModelClient adapter.”
3. “The memory experiment is taking a long time and the terminal output is not changing. How can I verify it is still running?”
4. “Create a file-based memory implementation supporting `/memory`, `/compact`, `/dream`, and `/help`.”
5. “Help me fix the failed verification checks for FastAPI routes, MongoDB generators, and UTF-8 run-log decoding.”
6. “Give me the complete metrics content in Markdown format.”

## AI-Generated or AI-Assisted Components

The following components were created with AI assistance and then reviewed, executed, and tested by me:

- `compose.hw6.yaml`
- `code/mongo_database.py`
- `code/init_hw6_mongodb.py`
- `code/mongo_schemas.py`
- `code/mongo_trials_api.py`
- `code/init_hw6_memory.py`
- `code/memory_schemas.py`
- `code/memory_service.py`
- `code/memory_api.py`
- `code/run_hw6_memory_experiments.py`
- `code/file_memory.py`
- `code/hw6_agent_instruction_demo.py`
- `code/verify_hw6.py`
- `reports/hw06/METRICS.md`
- `reports/hw06/MEMORY_COMPARISON.md`
- Portions of the final written report

## Student Review and Validation

I did not treat AI-generated output as automatically correct. I:

- Read and reviewed the generated code.
- Ran Python compilation checks.
- Started MongoDB through Docker Compose.
- Initialized and inspected MongoDB collections.
- Tested valid and invalid CRUD operations.
- Tested FastAPI endpoints.
- Ran the required ten-message memory demonstration.
- Ran all 30-message experiment configurations.
- Verified experiment output files and metrics.
- Tested all file-memory commands.
- Preserved original and consolidated memory versions.
- Verified duplicate merging and explicit contradiction resolution.
- Ran the final Homework 6 verification script.
- Corrected errors discovered during execution.

## Problems Identified During Testing

Testing revealed several issues that required correction:

- Docker Desktop had to be running before MongoDB was accessible.
- The FastAPI server and MongoDB container had to run simultaneously.
- Long Ollama experiments appeared inactive because PowerShell buffered output.
- MongoDB message counts changed while configurations were reset and rerun.
- A FastAPI route used a different path-parameter name than the verifier initially expected.
- The MongoDB dependency returned a generator rather than a database object directly.
- PowerShell initially stored `RUN_LOG.txt` using UTF-16, so it was converted to UTF-8.
- The local model required substantial execution time for the complete memory experiment.

## Local Model Use

The local `qwen3:4b` Ollama model was used for:

- Conversational-memory responses
- Summary generation
- Memory-probe answers
- Short-term memory comparisons
- Compression-policy evaluation

The experiment used the existing `src/model_client.py` adapter. The application did not bypass this adapter for direct model calls.

## Responsibility Statement

I remain responsible for the submitted implementation and report. I executed the application, reviewed the outputs, corrected runtime problems, validated the required behaviors, and confirmed that the final verification passed.