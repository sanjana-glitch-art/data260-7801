# Homework 6 Memory-System Comparison

## Overview

Homework 6 implemented two complementary memory systems for the Clinical Trial Listing assistant:

1. MongoDB-backed conversational memory
2. Markdown file-based durable memory using `AGENT.md` and `MEMORY.md`

## Comparison

| Criterion | MongoDB-Backed Memory | File-Based Memory |
|---|---|---|
| Inspectability | Records can be inspected through MongoDB queries, API endpoints, and aggregation pipelines. Inspection requires MongoDB tools or application code. | The memory is immediately readable in `AGENT.md` and `MEMORY.md` using any text editor. Changes are also visible through Git history. |
| Persistence after restart | Messages, summaries, and episodes persist in MongoDB after the FastAPI application and Ollama restart, provided the Docker volume remains available. | Markdown facts persist directly in the repository and remain available after application, model, database, and computer restarts. |
| Scalability across sessions | MongoDB is more suitable for many users and sessions because records are indexed by user ID, session ID, timestamp, and memory type. | Markdown files are less scalable because the entire file must be loaded, searched, and periodically consolidated as it grows. |
| Facts that must not be forgotten | Important facts can be stored as episodes or lifetime summaries, but retrieval depends on queries, embeddings, and relevance ranking. | Critical instructions and durable facts are placed directly in the system prompt, making file memory appropriate for information that must consistently remain visible. |
| Structured queries | MongoDB supports filtering, aggregation, pagination, indexes, and time-based analysis. | Markdown memory does not naturally support complex structured queries. |
| Multi-user isolation | MongoDB records can be separated by user ID and session ID. | A shared Markdown file requires additional organization to safely support multiple users. |
| Version history | Database changes require separate audit or backup mechanisms. | Git provides a clear version history showing the original and consolidated memory states. |
| Consolidation | Summaries and episodes can be created automatically from stored messages. | Consolidation must merge duplicates, resolve contradictions explicitly, and keep the file below the configured line threshold. |

## Consolidation Results

The original `MEMORY.md` contained 55 durable fact lines. It intentionally included repeated and contradictory facts. The `/compact` command:

- Merged exact duplicate facts.
- Explicitly resolved conflicting phase preferences.
- Explicitly resolved conflicting location preferences.
- Explicitly resolved conflicting summary intervals.
- Reduced the file from 55 lines to 35 lines.
- Preserved overflow information in an explicitly labeled retained-facts entry.
- Updated the last-consolidated timestamp.

The `/dream` command then extracted one additional durable fact from recent conversation text. The final file remained below the required 40-line limit.

## Recommended Use

MongoDB-backed memory is the better choice for scalable conversational history, session summaries, episodic retrieval, and multi-user applications. File-based memory is the better choice for stable project instructions, safety rules, coding conventions, and essential facts that should always be placed in the model prompt.

The strongest design is a hybrid system. `AGENT.md` supplies stable behavior and project constraints, `MEMORY.md` supplies a compact set of critical durable facts, and MongoDB supplies scalable conversational history and retrieval.