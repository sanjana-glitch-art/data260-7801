# Homework 1 Reproducible Run Instructions

Run all commands from the repository root:

```text
data260-7801/
```

## 1. Activate the Python Environment

Create the environment if it does not already exist:

```powershell
py -3.11 -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Verify Python:

```powershell
python --version
```

Expected major/minor version:

```text
Python 3.11
```

## 2. Prepare Ollama

Start Ollama from the Windows Start menu.

Verify it:

```powershell
ollama --version
```

Download the local model:

```powershell
ollama pull qwen3:4b
```

Confirm the model is available:

```powershell
ollama list
```

## 3. Build the Local Web Application

Start Docker Desktop and wait until its engine is running.

Build the image from the repository root:

```powershell
docker build -f code/Dockerfile -t data260-hw1:latest .
```

Create and run the container for the first time:

```powershell
docker run --name data260-hw1-7801 -d -p 8601:80 data260-hw1:latest
```

If the container already exists, restart it:

```powershell
docker start data260-hw1-7801
```

Verify the container:

```powershell
docker ps --filter "name=data260-hw1-7801"
```

Open the application:

```text
http://localhost:8601
```

Stop the container when finished:

```powershell
docker stop data260-hw1-7801
```

## 4. Run the Agent Pipeline

Use the fixed clinical-trial example:

```powershell
python code/agents_demo.py --model qwen3:4b --title "Sleep Quality and Academic Performance Study" --content "This clinical trial studies how sleep duration and sleep quality affect concentration, memory, and academic performance among university students."
```

The console should display:

- Planner Output
- Reviewer Output
- Finalized Output
- Publish Output

The finalized output must contain exactly three tags and a summary of no
more than 25 words.

## 5. Run the Nondeterminism Experiment

The fixed input is stored at:

```text
reports/hw01/cases/nondeterminism_input.json
```

Run:

```powershell
python code/run_nondeterminism.py
```

The script performs or resumes:

- 20 runs at temperature 0.7
- 20 runs at temperature 0.0

Results are saved to:

```text
reports/hw01/raw/nondeterminism_results.json
reports/hw01/raw/nondeterminism_results.csv
reports/hw01/raw/nondeterminism_metrics.json
```

If all 40 runs already exist, the script does not repeat them. It
recalculates and prints the metrics from the saved results.

## 6. Run the Interactive Model Client

Run:

```powershell
python code/hw1_client.py
```

Available commands:

```text
/stats
/exit
```

After every model response, the client prints input, output, and total
tokens.

The `/stats` command prints cumulative counts and serialized history
length without changing the conversation history.

The required five-turn results are stored at:

```text
reports/hw01/raw/client_token_counts.json
```

## 7. Run Verification

Run:

```powershell
python code/verify_hw1.py
```

A successful result contains:

```json
{
  "passed": true
}
```

The complete result is saved to:

```text
reports/hw01/verification.json
```

## 8. Review the Report

Open:

```text
reports/hw01/report.pdf
```

Confirm that:

- The personal configuration is present
- The repository URL works
- Code and output screenshots are together
- Docker localhost evidence is readable
- Agent outputs are readable
- Experiment metrics match the raw data
- Turn 3 and turn 5 statistics match the raw token log
- The AWS status is stated accurately

## 9. Confirm the Tagged Submission

Verify that the `hw1` tag exists:

```powershell
git show --no-patch --oneline hw1
```

Confirm that the tagged tree contains the report:

```powershell
git ls-tree -r --name-only hw1 | Select-String "reports/hw01/report.pdf"
```

Repository:

```text
https://github.com/sanjana-glitch-art/data260-7801
```

Tagged submission:

```text
https://github.com/sanjana-glitch-art/data260-7801/tree/hw1
```