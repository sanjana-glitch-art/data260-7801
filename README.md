# DATA-260 Coursework Repository

This repository contains the shared application code and homework evidence for
DATA-260.

## Student Information

| Setting | Value |
|---|---:|
| Student | Sanjana Thummalapalli |
| SID4 | 7801 |
| PORT_BASE | 8601 |
| PREFIX | s7801 |
| SEED | 7801 |
| VERIFY_SEED | 267801 |
| DOMAIN_ID | 1 |
| Assigned domain | Clinical Trial Listings |

## Repository

GitHub repository:

<https://github.com/sanjana-glitch-art/data260-7801>

Required collaborators:

- `Sbnikitha`
- `supriyaselvanganesan`

## Hardware and Software

| Item | Configuration |
|---|---|
| Operating system | Windows 11 |
| Processor | AMD Ryzen 5 7535HS with Radeon Graphics |
| Memory | 8 GB RAM |
| Dedicated GPU | AMD Radeon RX 6550M, 4 GB |
| Python | 3.11 |
| Local model | qwen3:4b |
| Application URL | `http://localhost:8601` |
| FastAPI documentation | `http://localhost:8601/docs` |

The originally requested `qwen3:8b` model was tested during Homework 1, but one
pipeline run took approximately 519 seconds on this hardware. The smaller
tool-capable `qwen3:4b` model is therefore used as the documented local
substitute.

## Repository Structure

```text
data260-7801/
├── code/
│   ├── __init__.py
│   ├── web_application/
│   │   ├── index.html
│   │   ├── styles.css
│   │   └── script.js
│   ├── agent_graph/
│   │   ├── __init__.py
│   │   ├── state.py
│   │   ├── schemas.py
│   │   ├── nodes.py
│   │   ├── router.py
│   │   └── workflow.py
│   ├── main.py
│   ├── run_agent_graph.py
│   ├── run_hw2_experiments.py
│   ├── verify_hw2.py
│   ├── agents_demo.py
│   ├── hw1_client.py
│   ├── run_nondeterminism.py
│   ├── verify_hw1.py
│   └── Dockerfile
├── src/
│   ├── __init__.py
│   └── model_client.py
├── reports/
│   ├── hw01/
│   └── hw02/
│       ├── cases/
│       ├── raw/
│       ├── screenshots/
│       ├── RUN_LOG.txt
│       ├── METRICS.md
│       ├── AI_USE.md
│       ├── report.pdf
│       ├── reproducible_run_instructions.md
│       └── verification.json
├── AGENT.md
├── DOMAIN_SCHEMA.md
├── README.md
└── requirements.txt
```

Application code is maintained in the shared `code/` and `src/` directories.
Homework-specific reports, raw results, logs, and evidence are stored under
`reports/hw01/` and `reports/hw02/`. Application code is not duplicated inside
the report directories.

## Clinical Trial Listing Application

The application manages Clinical Trial Listing records. Its main domain fields
include:

- Trial title
- Sponsor name
- Submitter email
- Trial description
- Trial phase
- Terms-and-conditions acceptance

The primary field is `trialTitle`, and the secondary field is `sponsorName`.

## Homework 1

Homework 1 established:

- The initial HTML and JavaScript clinical-trial form
- Client-side form validation
- JSON serialization and parsing
- Object destructuring and spread syntax
- A closure-based successful-submission counter
- A local Docker deployment
- A sequential Planner and Reviewer pipeline
- A nondeterminism experiment
- The reusable `src/model_client.py` adapter
- A bullet-only local code-review client
- Per-turn token accounting

Homework 1 evidence is stored in:

```text
reports/hw01/
```

## Homework 2

Homework 2 extends the same application with:

- Responsive behavior at a width of 375 pixels
- Visible loading, empty, and error states
- A FastAPI backend running on port 8601
- Clinical-trial creation
- Updating record ID 1
- Deleting the highest-ID record
- Search by trial title or sponsor name
- A stateful LangGraph Planner and Reviewer workflow
- A Supervisor node and conditional routing
- Reviewer-to-Planner correction loops
- Turn-ceiling protection
- Pydantic output validation
- Schema-validation experiments
- Turn-ceiling comparison experiments
- Adversarial-input experiments
- Objective smoke-test verification

Homework 2 evidence is stored in:

```text
reports/hw02/
```

## FastAPI Endpoints

| Method | Route | Purpose |
|---|---|---|
| GET | `/` | Serve the application |
| GET | `/api/trials` | List or search clinical trials |
| GET | `/api/trials/{trial_id}` | Retrieve one record |
| POST | `/api/trials` | Create a JSON API record |
| PUT | `/api/trials/{trial_id}` | Update a JSON API record |
| DELETE | `/api/trials/{trial_id}` | Delete a JSON API record |
| POST | `/trials` | Create through the HTML form |
| POST | `/trials/1/update` | Update record ID 1 and redirect |
| POST | `/trials/delete-highest` | Delete the highest-ID record |

The application uses in-memory data for reproducibility. Restarting FastAPI
restores the initial records.

## Stateful Agent Graph

The Homework 2 agent graph contains:

- `AgentState`: shared graph memory
- `supervisor_node`: increments the Planner-attempt counter
- `planner_node`: produces tags and a summary
- `reviewer_node`: reviews semantic relevance and factual support
- Conditional routing: completes, retries, or stops at the turn ceiling
- Pydantic validation: enforces the Planner output schema

All Planner and Reviewer model calls use:

```text
src/model_client.py
```

The graph nodes do not call Ollama or LangChain model classes directly.

## Planner Output Schema

A valid Planner proposal requires:

- Exactly three tags
- Three distinct tags
- Every tag to contain 3–30 characters
- A summary containing no more than 25 whitespace-separated words
- No unexpected JSON fields

## Homework 2 Experiment Results

### Schema validation

| Outcome | Count | Mean latency |
|---|---:|---:|
| Valid first attempt | 30 | 8,638.34 ms |
| Valid after one retry | 0 | N/A |
| Valid after two or more retries | 0 | N/A |
| Hit turn ceiling | 0 | N/A |

### Turn-ceiling comparison

| Metric | Ceiling 2 | Ceiling 10 |
|---|---:|---:|
| Runs | 20 | 20 |
| Completed | 20 | 20 |
| Completion rate | 100.00% | 100.00% |
| Mean latency | 8,729.50 ms | 6,005.43 ms |
| Mean Planner attempts | 1.00 | 1.00 |

Deployment ceiling selected: **2**

Both ceilings achieved the same completion rate and required the same average
number of Planner attempts. Ceiling 2 provides a tighter upper bound on
correction-loop work.

### Adversarial input

| Metric | Result |
|---|---:|
| Runs | 5 |
| Hit turn ceiling | 5 |
| Hit-ceiling rate | 100.00% |
| Mean latency | 29,699.65 ms |

The prompt-injection-style adversarial input reached the ceiling in all five
observed runs. The result is reported as an experimental observation, not as a
universal deterministic guarantee.

## Environment Setup

Create a Python 3.11 environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Confirm the local model:

```powershell
ollama pull qwen3:4b
ollama list
```

## Run the FastAPI Application

```powershell
python -m uvicorn code.main:app `
    --host 0.0.0.0 `
    --port 8601 `
    --reload
```

Open:

```text
http://localhost:8601
```

API documentation:

```text
http://localhost:8601/docs
```

## Run the Normal Agent Graph

```powershell
python code\run_agent_graph.py `
    --model qwen3:4b `
    --temperature 0.0 `
    --turn-ceiling 2
```

## Run the Correction-Loop Demonstration

```powershell
python code\run_agent_graph.py `
    --model qwen3:4b `
    --temperature 0.0 `
    --turn-ceiling 2 `
    --force-reviewer-issue
```

## Run Homework 2 Experiments

Run or resume all 75 experiments:

```powershell
python code\run_hw2_experiments.py `
    --experiment all `
    --model qwen3:4b `
    --temperature 0.7
```

Individual experiment groups can be run with:

```powershell
python code\run_hw2_experiments.py --experiment schema
python code\run_hw2_experiments.py --experiment ceilings
python code\run_hw2_experiments.py --experiment adversarial
```

## Run Homework 2 Verification

```powershell
python code\verify_hw2.py
```

The verifier writes:

```text
reports/hw02/verification.json
```

A successful final result contains:

```text
"passed": true
```

## Reproducibility and Evidence

Detailed reproduction instructions:

```text
reports/hw02/reproducible_run_instructions.md
```

Machine-readable experiment results:

```text
reports/hw02/raw/
```

Real console output and timestamps:

```text
reports/hw02/RUN_LOG.txt
```

Experiment analysis:

```text
reports/hw02/METRICS.md
```

AI-use disclosure:

```text
reports/hw02/AI_USE.md
```

## Submission Tags

Homework 1 uses:

```text
hw1
```

Homework 2 will use:

```text
hw2
```