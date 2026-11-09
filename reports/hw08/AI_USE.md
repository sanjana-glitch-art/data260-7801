# AI Use Statement — Homework 8

Student: Sanjana Thummalapalli  
SID4: 7801  
Course: DATA-260  
Homework: 8  

## 1. What did you use an AI assistant for, and what did you do yourself?

I used an AI assistant to help interpret the Homework 8 requirements, plan the Kafka architecture, draft portions of the Python code, troubleshoot errors, and prepare verification commands and report structure.

I personally configured Docker Desktop, created and ran the Kafka containers, executed all commands, inspected logs, tested the FastAPI and Kafka flows, terminated and restarted the Writer during the failure experiment, verified the generated JSON evidence, corrected files in VS Code, and confirmed results using `py_compile`, Ruff, Kafka CLI commands, and actual runtime output.

## 2. What AI-produced output was wrong or unsuitable, or what did you independently verify?

Some initially generated file-creation instructions included PowerShell here-string markers such as `@'` and `'@ | Set-Content`. When those wrapper lines were accidentally included inside Python and YAML files, they caused syntax and parsing errors.

The initial Kafka request/response client also occasionally timed out even though the worker produced a response. I independently verified this by comparing the client traceback with the worker logs, which showed that the request was received, processed, replied to, and committed.

## 3. How did you detect or verify the problem?

I detected the file-content problem using:

- `python -m py_compile`
- `python -m ruff check`
- Docker Compose YAML parsing
- Inspection of the first and last lines of affected files

I detected the Kafka response timing issue by comparing correlation IDs in the client output and worker logs. I also verified every final behavior using machine-readable JSON files and objective checks, including duplicate entity IDs, retry counts, dead-letter output, partition numbers, Writer process IDs, completion sequences, and preserved correlation IDs.

## 4. What did you change, and why does it work now?

I removed the PowerShell wrapper text from Python and YAML files and retained only valid source code. I corrected imports, formatting, and exception types until compilation and Ruff checks passed.

For Kafka request/response handling, I positioned the response consumer at the current high watermark before sending the request. This ensures it listens for the newly generated correlated response without consuming stale records or missing the new response.

I added idempotency caching keyed by correlation ID, manual offset commits after successful processing, bounded retries, dead-letter routing, entity-based Kafka keys, and objective experiment scripts. These changes prevent duplicate side effects, allow redelivery after consumer failure, isolate poison messages, and preserve ordering for related clinical-trial events.