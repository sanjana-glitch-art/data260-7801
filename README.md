# DATA-260 Homework 1

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
- Python: 3.11
- Ollama model: qwen3:4b
- Local application URL: http://localhost:8601

The required qwen3:8b model was tested first. One pipeline run took
approximately 519 seconds on this hardware. The smaller tool-capable
qwen3:4b model was therefore used for the repeated experiment.

## Application

The application provides a form for submitting clinical trial listings.
It collects:

- Trial title
- Sponsor name
- Submitter email
- Trial description
- Trial phase
- Terms-and-conditions acceptance

The JavaScript validates that the description contains more than 25
characters and that the terms checkbox is selected. Successful submissions
are converted to JSON, parsed, destructured, extended with a submission
date, and counted using a closure.

## Prerequisites

- Git
- Python 3.11 or 3.12
- Docker Desktop
- Ollama
- qwen3:4b

## Python Setup

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
ollama pull qwen3:4b