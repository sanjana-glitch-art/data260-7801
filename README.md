# DATA-260 Homework 1

## Repository

- Repository: https://github.com/sanjana-glitch-art/data260-7801
- Tagged submission: https://github.com/sanjana-glitch-art/data260-7801/tree/hw1

## Student Configuration

| Value | Result |
|---|---|
| Student | Sanjana Thummalapalli |
| SID4 | 7801 |
| PORT_BASE | 8601 |
| PREFIX | s7801 |
| SEED | 7801 |
| VERIFY_SEED | 267801 |
| DOMAIN_ID | 1 |
| Assigned domain | Clinical Trial Listings |

## Hardware and Software

- Operating system: Windows 11
- Processor: AMD Ryzen 5 7535HS with Radeon Graphics
- Memory: 8 GB RAM
- Dedicated GPU: AMD Radeon RX 6550M, 4 GB
- Integrated GPU: AMD Radeon Graphics
- Python: 3.11
- Ollama model: qwen3:4b
- Local URL: http://localhost:8601

The requested qwen3:8b model was tested first. One Planner-Reviewer
pipeline run took approximately 519 seconds on this hardware. The smaller
tool-capable qwen3:4b model was therefore used for the repeated experiment.

## Repository Structure

```text
data260-7801/
├── code/
│   ├── web_application/
│   │   ├── index.html
│   │   └── script.js
│   ├── agents_demo.py
│   ├── hw1_client.py
│   ├── run_nondeterminism.py
│   ├── verify_hw1.py
│   └── Dockerfile
├── src/
│   ├── __init__.py
│   └── model_client.py
├── reports/
│   └── hw01/
│       ├── cases/
│       ├── raw/
│       ├── screenshots/
│       ├── AI_USE.md
│       ├── METRICS.md
│       ├── RUN_LOG.txt
│       ├── report.pdf
│       ├── reproducible_run_instructions.md
│       └── verification.json
├── AGENT.md
├── DOMAIN_SCHEMA.md
├── README.md
└── requirements.txt
```

The application code in `code/` and `src/` is shared and will be extended
in future homework assignments. Homework-specific reports, evidence, logs,
and raw results are stored under `reports/hw01/`.

## Web Application

The web application provides a form for clinical trial listings. It
collects:

- Trial title
- Sponsor name
- Submitter email
- Trial description
- Trial phase
- Terms-and-conditions acceptance

The JavaScript verifies that the description contains more than 25
characters and that the terms checkbox is selected.

After successful validation, the application:

- Converts the form object into a JSON string
- Parses the JSON string back into an object
- Uses destructuring to extract the trial title and email
- Uses the spread operator to add `submissionDate`
- Uses a closure to count successful submissions

## Prerequisites

- Git
- Python 3.11 or 3.12
- Docker Desktop
- Ollama
- qwen3:4b

## Python Setup

Run all commands from the repository root.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
ollama pull qwen3:4b
```

## Local Docker Deployment

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

Open:

```text
http://localhost:8601
```

Check its status:

```powershell
docker ps --filter "name=data260-hw1-7801"
```

Stop it when it is not needed:

```powershell
docker stop data260-hw1-7801
```

## Agent Pipeline

The agent pipeline contains:

1. Planner agent
2. Reviewer agent
3. Deterministic, non-agent finalization step

All model calls pass through:

```text
src/model_client.py
```

Run:

```powershell
python code/agents_demo.py --model qwen3:4b --title "Sleep Quality and Academic Performance Study" --content "This clinical trial studies how sleep duration and sleep quality affect concentration, memory, and academic performance among university students."
```

The pipeline prints:

- Planner JSON
- Reviewer JSON
- Finalized JSON
- Publish JSON
- Planner and Reviewer latency

The final output always contains exactly three tags and a summary of at
most 25 words.

## Nondeterminism Experiment

The unchanged input is stored at:

```text
reports/hw01/cases/nondeterminism_input.json
```

Run:

```powershell
python code/run_nondeterminism.py
```

The experiment performs:

- 20 runs at temperature 0.7
- 20 runs at temperature 0.0
- 40 successful runs in total

The script saves each successful run immediately and resumes from the
existing results if interrupted.

Raw outputs are stored in:

```text
reports/hw01/raw/nondeterminism_results.json
reports/hw01/raw/nondeterminism_results.csv
reports/hw01/raw/nondeterminism_metrics.json
```

## Experiment Results

| Metric | Temperature 0.7 | Temperature 0.0 |
|---|---:|---:|
| Distinct tag sets | 11 | 1 |
| Latency p50 | 5526.03 ms | 5105.43 ms |
| Latency p95 | 7654.37 ms | 5529.57 ms |
| Latency p99 | 18532.39 ms | 7052.89 ms |

At temperature 0.7, identical inputs produced multiple related tag sets.
At temperature 0.0, all 20 runs produced the same tag set.

See `reports/hw01/METRICS.md` for the complete results.

## Interactive Model Client

Run:

```powershell
python code/hw1_client.py
```

Commands:

```text
/stats
/exit
```

After every model response, the client prints:

- Input tokens
- Output tokens
- Total tokens
- Bullet-only verification result

The `/stats` command displays:

- Turn count
- Cumulative input tokens
- Cumulative output tokens
- Cumulative total tokens
- Serialized conversation-history length

`/stats` does not add anything to the conversation history.

The saved five-turn token data is stored at:

```text
reports/hw01/raw/client_token_counts.json
```

## Token Results

| Turn | Input | Output | Total | Cumulative Input | Cumulative Output | History Length |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 134 | 46 | 180 | 134 | 46 | 249 |
| 2 | 191 | 33 | 224 | 325 | 79 | 469 |
| 3 | 241 | 61 | 302 | 566 | 140 | 881 |
| 4 | 313 | 73 | 386 | 879 | 213 | 1298 |
| 5 | 403 | 53 | 456 | 1282 | 266 | 1667 |

All five displayed model responses passed bullet-only verification.

## Model-Client Questions

### Why is prior conversation context resent with every turn?

A model request is normally stateless. The application must resend earlier
messages so the model can understand references to previous questions and
answers and continue the conversation coherently.

### How is a system prompt different from a user message?

A system prompt defines the model's overall role, behavioral constraints,
and response format. A user message contains the specific request. System
instructions have higher priority and remain applicable throughout the
conversation.

### Why do input tokens grow over a conversation?

Every request contains the system prompt, earlier user messages, earlier
assistant responses, and the newest user message. As the serialized
history grows, the number of input tokens also grows.

### What eventually limits that growth?

The model's context-window limit restricts the number of tokens that can
be included in one request. An application must eventually remove,
summarize, or compress older conversation history.

## Verification

Run:

```powershell
python code/verify_hw1.py
```

The verification script checks:

- Required files
- Supported Python version
- Python source compilation
- HTML requirements
- JavaScript requirements
- Adapter-only model access
- Forty nondeterminism results
- Five-turn token accounting
- Bullet-only verification

The result is written to:

```text
reports/hw01/verification.json
```

A successful result contains:

```json
{
  "passed": true
}
```

## Homework Artifacts

The Homework 1 report and supporting files are located under:

```text
reports/hw01/
```

Important files include:

- `report.pdf`
- `RUN_LOG.txt`
- `METRICS.md`
- `AI_USE.md`
- `verification.json`
- `reproducible_run_instructions.md`
- `raw/nondeterminism_results.json`
- `raw/nondeterminism_results.csv`
- `raw/client_token_counts.json`

## AWS ECS Status

The local Docker deployment was completed successfully.

My student AWS credits were exhausted. The TA approved attempting the ECS
deployment through a classmate's AWS account, but account issues prevented
the deployment from being completed during the available session. The
report documents the deployment status accurately.

## Git Tag

The final Homework 1 submission is tagged:

```text
hw1
```

Tagged version:

```text
https://github.com/sanjana-glitch-art/data260-7801/tree/hw1
```