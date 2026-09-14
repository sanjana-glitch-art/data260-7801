# DATA-260 Homework 2 Reproducible Run Instructions

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
| Local model | qwen3:4b |

## Requirements

The following software is required:

- Windows 11 or another operating system with Python support
- Git
- Python 3.11 or 3.12
- Ollama
- The `qwen3:4b` Ollama model

Docker Desktop is optional for local container verification.

## 1. Clone the repository

```powershell
git clone https://github.com/sanjana-glitch-art/data260-7801.git
cd data260-7801
```

To reproduce the submitted Homework 2 version after the tag is created:

```powershell
git checkout hw2
```

## 2. Create and activate the Python environment

On Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Confirm the Python version:

```powershell
python --version
```

Expected major and minor version:

```text
Python 3.11
```

## 3. Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Confirm the main HW2 dependencies:

```powershell
python -c "import fastapi, uvicorn, pydantic, langgraph, ollama; print('HW2 dependencies available')"
```

Expected:

```text
HW2 dependencies available
```

## 4. Start Ollama

Confirm Ollama is installed:

```powershell
ollama --version
```

Download the documented local model if necessary:

```powershell
ollama pull qwen3:4b
```

Confirm the model is available:

```powershell
ollama list
```

Ollama must remain running while executing the agent graph or experiments.

## 5. Compile the Python files

From the repository root:

```powershell
python -m py_compile `
    code\main.py `
    code\run_agent_graph.py `
    code\run_hw2_experiments.py `
    code\agent_graph\state.py `
    code\agent_graph\schemas.py `
    code\agent_graph\nodes.py `
    code\agent_graph\router.py `
    code\agent_graph\workflow.py `
    src\model_client.py
```

No output indicates successful compilation.

## 6. Run the FastAPI application

```powershell
python -m uvicorn code.main:app `
    --host 0.0.0.0 `
    --port 8601 `
    --reload
```

Open the application:

```text
http://localhost:8601
```

Open the automatically generated API documentation:

```text
http://localhost:8601/docs
```

The application should display the Clinical Trial Listings home view and its
initial records.

## 7. Verify the FastAPI API

Keep FastAPI running and open a second PowerShell window in the repository.

Activate the environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Retrieve all records:

```powershell
Invoke-RestMethod http://localhost:8601/api/trials |
    ConvertTo-Json -Depth 5
```

Search by trial title or sponsor:

```powershell
Invoke-RestMethod "http://localhost:8601/api/trials?search=SJSU" |
    ConvertTo-Json -Depth 5
```

Create a record:

```powershell
$body = @{
    trial_title = "Nutrition and Concentration Study"
    sponsor_name = "SJSU Student Health Center"
    submitter_email = "nutrition@example.edu"
    trial_description = "This clinical trial examines nutrition and concentration among university students."
    trial_phase = "Phase I"
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri http://localhost:8601/api/trials `
    -Method Post `
    -ContentType "application/json" `
    -Body $body |
    ConvertTo-Json -Depth 5
```

Update record ID 1:

```powershell
$body = @{
    trial_title = "Updated Sleep Quality Study"
    sponsor_name = "Updated SJSU Research Center"
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri http://localhost:8601/api/trials/1 `
    -Method Put `
    -ContentType "application/json" `
    -Body $body |
    ConvertTo-Json -Depth 5
```

The browser interface also provides controls for creating a record, updating
record ID 1, deleting the highest-ID record, and searching by title or sponsor.

The records are stored in memory. Restarting FastAPI restores the initial
records.

## 8. Run the normal stateful agent graph

Confirm Ollama is running, then execute:

```powershell
python code\run_agent_graph.py `
    --model qwen3:4b `
    --temperature 0.0 `
    --turn-ceiling 2
```

A successful run should stream updates from:

```text
Supervisor
Planner
Reviewer
```

The final state should normally contain:

```text
status = completed
completed = true
abandoned = false
```

Model output can vary, so exact tags and summary wording are not expected to
remain identical.

## 9. Run the correction-loop demonstration

```powershell
python code\run_agent_graph.py `
    --model qwen3:4b `
    --temperature 0.0 `
    --turn-ceiling 2 `
    --force-reviewer-issue
```

The forced test should route from Reviewer back through Supervisor and Planner.
It should stop after two Planner attempts with:

```text
status = abandoned
completed = false
abandoned = true
```

This test demonstrates that the correction loop cannot run indefinitely.

## 10. Validate the frozen experiment inputs

```powershell
python -m json.tool reports\hw02\cases\schema_input.json
python -m json.tool reports\hw02\cases\adversarial_input.json
```

The schema input must not be changed between experiment groups.

## 11. Run the schema-validation experiment

```powershell
python code\run_hw2_experiments.py `
    --experiment schema `
    --model qwen3:4b `
    --temperature 0.7
```

This performs or resumes 30 runs and creates:

- `reports/hw02/raw/schema_validation_results.json`
- `reports/hw02/raw/schema_validation_results.csv`
- `reports/hw02/raw/schema_validation_metrics.json`

## 12. Run the turn-ceiling comparison

```powershell
python code\run_hw2_experiments.py `
    --experiment ceilings `
    --model qwen3:4b `
    --temperature 0.7
```

This performs:

- 20 runs using turn ceiling 2
- 20 runs using turn ceiling 10

It creates:

- `reports/hw02/raw/ceiling_comparison_results.json`
- `reports/hw02/raw/ceiling_comparison_results.csv`
- `reports/hw02/raw/ceiling_comparison_metrics.json`

## 13. Run the adversarial experiment

```powershell
python code\run_hw2_experiments.py `
    --experiment adversarial `
    --model qwen3:4b `
    --temperature 0.7
```

This performs or resumes five runs and creates:

- `reports/hw02/raw/adversarial_results.json`
- `reports/hw02/raw/adversarial_results.csv`
- `reports/hw02/raw/adversarial_metrics.json`

## 14. Run or resume every experiment

The runner saves each completed run. If execution is interrupted, repeat the
same command and it will resume from the existing results.

```powershell
python code\run_hw2_experiments.py `
    --experiment all `
    --model qwen3:4b `
    --temperature 0.7
```

The complete experiment contains 75 runs:

- 30 schema-validation runs
- 20 ceiling-2 runs
- 20 ceiling-10 runs
- 5 adversarial runs

## 15. Verify experiment counts

```powershell
python -c "import json; from pathlib import Path; p=Path('reports/hw02/raw'); s=json.load(open(p/'schema_validation_results.json'))['results']; c=json.load(open(p/'ceiling_comparison_results.json'))['results']; a=json.load(open(p/'adversarial_results.json'))['results']; print('Schema:', len(s)); print('Ceiling 2:', sum(r['turn_ceiling']==2 for r in c)); print('Ceiling 10:', sum(r['turn_ceiling']==10 for r in c)); print('Adversarial:', len(a)); print('Total:', len(s)+len(c)+len(a))"
```

Expected:

```text
Schema: 30
Ceiling 2: 20
Ceiling 10: 20
Adversarial: 5
Total: 75
```

## 16. Inspect the generated metrics

```powershell
python -m json.tool reports\hw02\raw\schema_validation_metrics.json
python -m json.tool reports\hw02\raw\ceiling_comparison_metrics.json
python -m json.tool reports\hw02\raw\adversarial_metrics.json
```

## 17. Run the Homework 2 verifier

After all required application and report files are present:

```powershell
python code\verify_hw2.py
```

This command writes:

```text
reports/hw02/verification.json
```

A successful result must contain:

```text
"passed": true
```

## 18. Review the run log

The real console output and timestamps used for the report are stored in:

```text
reports/hw02/RUN_LOG.txt
```

## Expected Experiment Results for This Submission

The submitted experiment produced:

- 30 of 30 schema runs valid on the first attempt
- 20 of 20 ceiling-2 runs completed
- 20 of 20 ceiling-10 runs completed
- 5 of 5 adversarial runs reached the turn ceiling
- 75 total recorded experiment runs
- Deployment ceiling selected: 2

Exact model wording may vary if the experiment is executed again. Verification
should test structural properties and counts rather than exact generated text.