# Homework 3 Reproducible Run Instructions

## Student Configuration

| Setting | Value |
|---|---|
| Student | Sanjana Thummalapalli |
| SID4 | 7801 |
| PORT_BASE | 8601 |
| PREFIX | s7801 |
| SEED | 7801 |
| VERIFY_SEED | 267801 |
| DOMAIN_ID | 1 |
| Assigned domain | Clinical Trial Listings |

## Requirements

The project was developed and tested using:

- Windows 11
- PowerShell
- Python 3.11
- Git
- Internet access for the initial Hugging Face model download
- At least 4 GB of available memory
- Repository: `data260-7801`

The retrieval experiment uses the public embedding model:

`sentence-transformers/all-MiniLM-L6-v2`

No OpenAI API key or paid cloud service is required.

## 1. Clone the Repository

```powershell
git clone https://github.com/sanjana-glitch-art/data260-7801.git

cd data260-7801
```

## 2. Create and Activate the Python Environment

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

## 3. Install Dependencies

```powershell
python -m pip install --upgrade pip

python -m pip install -r requirements.txt
```

The first installation may take several minutes because it installs
LlamaIndex, sentence-transformers, PyTorch dependencies, and FAISS.

## 4. Compile the Main Python Files

```powershell
python -m py_compile `
    code\main.py `
    code\auth.py `
    code\prepare_hw3_corpus.py `
    code\run_hw3_retrieval.py
```

No output means compilation passed.

## 5. Configure Authentication

The application provides default demonstration credentials, but the
values can be explicitly configured through environment variables:

```powershell
$env:SESSION_SECRET="s7801-hw3-local-secret"
$env:SESSION_IDLE_SECONDS="120"
$env:HW3_USERNAME="sanjana"
$env:HW3_PASSWORD="Data260!7801"
```

The session secret shown here is for local homework reproduction only. A
production deployment should use a strong secret stored outside the
repository.

## 6. Start the FastAPI Application

```powershell
python -m uvicorn code.main:app `
    --host 127.0.0.1 `
    --port 8601 `
    --reload
```

Keep this terminal open.

Open the following pages:

- Home: `http://127.0.0.1:8601/`
- Login: `http://127.0.0.1:8601/login`
- Protected dashboard: `http://127.0.0.1:8601/dashboard`
- Clinical-trial listings: `http://127.0.0.1:8601/trials`
- FastAPI documentation: `http://127.0.0.1:8601/docs`

Use these local demonstration credentials:

```text
Username: sanjana
Password: Data260!7801
```

## 7. Verify the Registered Routes

In a second PowerShell terminal with the virtual environment activated,
run:

```powershell
python -c "from code.main import app; [print(','.join(sorted(getattr(r,'methods',[]) or [])) or 'MOUNT', r.path) for r in app.routes]"
```

The output should include:

```text
GET /
GET /login
POST /login
GET /dashboard
GET /logout
GET /trials
GET /api/trials
POST /api/trials
GET /api/trials/{trial_id}
PUT /api/trials/{trial_id}
DELETE /api/trials/{trial_id}
```

## 8. Test Authentication

Perform the following checks:

1. Open `/dashboard` without logging in.
2. Confirm that the application redirects to `/login`.
3. Enter an incorrect password.
4. Confirm that a Bootstrap invalid-credentials alert appears.
5. Log in using the valid credentials.
6. Confirm that the application redirects to `/dashboard`.
7. Confirm that the dashboard displays the user's name.
8. Log out.
9. Attempt to access `/dashboard` again.
10. Confirm that the logged-out session cannot access the dashboard.

## 9. Test the Idle Timeout

For a faster timeout test, stop Uvicorn and set:

```powershell
$env:SESSION_IDLE_SECONDS="30"
```

Restart Uvicorn:

```powershell
python -m uvicorn code.main:app `
    --host 127.0.0.1 `
    --port 8601 `
    --reload
```

Log in, remain inactive for at least 31 seconds, and refresh the
dashboard.

The application should redirect to:

```text
/login?expired=1
```

The login page should display an inactivity-expiration message.

After testing, restore the normal setting:

```powershell
$env:SESSION_IDLE_SECONDS="120"
```

## 10. Inspect the Session Cookie

In Chrome DevTools:

1. Open the Network panel.
2. Enable **Keep log**.
3. Log in.
4. Select the `POST /login` request.
5. Open the response headers.
6. Inspect the `Set-Cookie` header.

The cookie should use the name:

```text
s7801_session
```

It should include:

- `HttpOnly`
- `Secure`
- `SameSite=Lax`
- `Path=/`

## 11. Rebuild the Domain Corpus

The repository already contains local text snapshots and a corpus
manifest. To rebuild the corpus from the documented public sources, run:

```powershell
python code\prepare_hw3_corpus.py
```

This creates or updates:

```text
reports/hw03/corpus/
reports/hw03/SOURCES.md
reports/hw03/CORPUS_MANIFEST.json
```

Verify the corpus size:

```powershell
python -c "import json; d=json.load(open('reports/hw03/CORPUS_MANIFEST.json')); print('Total bytes:',d['totalTextBytes']); print('Meets 200 KB:',d['meetsMinimumSize'])"
```

The output must report:

```text
Meets 200 KB: True
```

## 12. Validate the Questions

```powershell
@'
from pathlib import Path

import yaml

path = Path("reports/hw03/questions.yaml")

data = yaml.safe_load(
    path.read_text(encoding="utf-8")
)

questions = data["questions"]

print("Question count:", len(questions))

for question in questions:
    print(
        question["id"],
        "|",
        question["expected_source_file"]
    )
'@ | python -
```

The file contains five preregistered graded questions and one additional
question used for false-positive analysis.

## 13. Run the Retrieval Experiment

Optional environment variables can suppress harmless Hugging Face cache
warnings on Windows:

```powershell
$env:HF_HUB_DISABLE_SYMLINKS_WARNING="1"
$env:HF_HUB_VERBOSITY="error"
$env:TOKENIZERS_PARALLELISM="false"
```

Run the experiment:

```powershell
python code\run_hw3_retrieval.py
```

The first run downloads the embedding model. Later runs reuse the local
cache.

The experiment implements:

1. `TokenTextSplitter`
2. `SemanticSplitterNodeParser`
3. `SentenceWindowNodeParser`

It creates:

```text
reports/hw03/raw/retrieval_results.jsonl
reports/hw03/raw/retrieval_results.csv
reports/hw03/raw/retrieval_metrics.json
```

## 14. Validate the Retrieval Outputs

```powershell
@'
import csv
import json

with open(
    "reports/hw03/raw/retrieval_results.jsonl",
    encoding="utf-8"
) as file:
    runs = [
        json.loads(line)
        for line in file
        if line.strip()
    ]

with open(
    "reports/hw03/raw/retrieval_results.csv",
    encoding="utf-8"
) as file:
    rows = list(csv.DictReader(file))

print("Retrieval runs:", len(runs))
print("Retrieved chunks:", len(rows))
print("Run-count PASS:", len(runs) == 18)
print("Chunk-count PASS:", len(rows) == 90)
'@ | python -
```

Expected:

```text
Retrieval runs: 18
Retrieved chunks: 90
Run-count PASS: True
Chunk-count PASS: True
```

## 15. Inspect the Retrieval Metrics

```powershell
python -m json.tool `
    reports\hw03\raw\retrieval_metrics.json
```

The summary measurements are also documented in:

```text
reports/hw03/METRICS.md
```

## 16. Run the Homework Verification

After `code/verify_hw3.py` has been created, run:

```powershell
python code\verify_hw3.py
```

The command creates:

```text
reports/hw03/verification.json
```

The final JSON should contain:

```json
{
  "passed": true
}
```

## 17. Important Output Locations

| Artifact | Location |
|---|---|
| Authentication router | `code/auth.py` |
| Main FastAPI application | `code/main.py` |
| HTML templates | `code/templates/` |
| Corpus preparation | `code/prepare_hw3_corpus.py` |
| Retrieval experiment | `code/run_hw3_retrieval.py` |
| Corpus sources | `reports/hw03/SOURCES.md` |
| Corpus manifest | `reports/hw03/CORPUS_MANIFEST.json` |
| Questions | `reports/hw03/questions.yaml` |
| Raw retrieval data | `reports/hw03/raw/` |
| Metrics | `reports/hw03/METRICS.md` |
| AI-use disclosure | `reports/hw03/AI_USE.md` |
| Run log | `reports/hw03/RUN_LOG.txt` |
| Verification results | `reports/hw03/verification.json` |
| Final report | `reports/hw03/report.pdf` |