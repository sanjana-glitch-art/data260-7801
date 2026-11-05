@'
# DATA-260 Homework 7 AI Use Disclosure

## 1. What did I use an AI assistant for, and what did I do myself?

I used an AI assistant to help interpret the assignment requirements, draft implementation scaffolding, diagnose Python, PowerShell, Docker, MySQL, Ollama, Ruff, and React errors, and organize the verification and report artifacts. I personally ran the commands, configured the development environment, reviewed and integrated the code, started the required services, executed all experiments, inspected the generated results, tested the API and UI, and saved the evidence.

## 2. What AI-produced output was wrong or unsuitable?

One generated Part 2 verification runner initially allowed the comparison task to search for the generic phrase “clinical trials.” The database search returned no matching rows, so the model repeatedly called the same search tool instead of completing two detail lookups. Another generated file was accidentally copied as only a small code fragment, producing an indentation error.

## 3. How did I detect or verify the problem?

I detected the problem through objective terminal output. Task C reported `Success: False`, showed five `search_trials` calls, and contained no `trial_details` calls. Ruff and Python compilation also reported that the replacement runner began with unexpected indentation. I verified the corrected implementation using `py_compile`, Ruff, the fixed showcase tasks, the 20-attempt reliability sweep, and the saved JSON artifacts.

## 4. What did I change, and why does it work now?

I replaced the incomplete runner with the full source file and changed Task C to request the exact search input `{"query": "Study", "limit": 4}`. That query matches the seeded clinical-trial records and returns enough distinct IDs for two detail lookups. After the correction, Task C used `search_trials → trial_details → trial_details` and passed. I also used deterministic verifiers, bounded repair and Reflexion paths, tool and token budgets, and tool-boundary validation so that failures stop safely instead of producing unsupported answers.
'@ | Set-Content `
    reports\hw07\AI_USE.md `
    -Encoding utf8