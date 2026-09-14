FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r /app/requirements.txt

COPY code /app/code
COPY src /app/src
COPY AGENT.md /app/AGENT.md
COPY DOMAIN_SCHEMA.md /app/DOMAIN_SCHEMA.md

EXPOSE 8601

CMD ["python", "-m", "uvicorn", "code.main:app", "--host", "0.0.0.0", "--port", "8601"]