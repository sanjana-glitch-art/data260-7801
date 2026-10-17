## Homework 6 Memory-Agent Instructions

### Project Description

- Maintain a clinical-trial listing assistant that uses MongoDB conversation memory and Markdown-based durable memory.
- Answer clinical-trial questions using stored application data and clearly identify when requested information is unavailable.

### Technology Stack

- Use Python 3.11, FastAPI, PyMongo, MongoDB 7, Ollama, and the existing `src/model_client.py` adapter.
- Store structured conversational records in MongoDB and durable project facts in `MEMORY.md`.

### Coding Conventions

- Use type hints, descriptive snake_case names, short functions, and docstrings for public functions.
- Return predictable dictionaries or validated models from service functions.
- Keep configuration in environment variables rather than embedding credentials in source code.

### Testing Approach

- Test successful operations, invalid input, missing records, memory persistence, command behavior, and consolidation thresholds.
- Save reproducible test output and metrics under `reports/hw06/`.

### Prohibited Actions

- Do not expose passwords, session secrets, private email addresses, or MongoDB credentials in model responses or committed reports.
- Do not silently discard contradictory memory facts; consolidation must record how each contradiction was resolved.
- Do not access the model directly outside the existing `src/model_client.py` adapter.