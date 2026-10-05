# Homework 5 AI Use Disclosure

## AI Tools Used

I used ChatGPT as a development assistant while completing Homework 5. I also used the local Ollama model `qwen3:4b` as the required model for the agent scenarios.

## How ChatGPT Was Used

ChatGPT assisted with:

- Interpreting the Homework 5 requirements
- Planning the implementation steps
- Debugging Python import and package-path errors
- Debugging MySQL collation and database-migration errors
- Creating the Redux Toolkit state structure
- Debugging React lint and build errors
- Organizing the metrics, reflection, and report evidence

## Example Prompts

Examples of prompts used during development include:

1. “Explain the Homework 5 requirements and give me the implementation steps in order.”

2. “My MySQL migration fails because of an illegal mix of collations. Explain the cause and help me fix it.”

3. “The React build cannot resolve the Redux slice, API client, store, and TrialForm modules. Help me create and connect these files.”

4. “The Ollama model fails with a memory-allocation error. Help me reduce the context and prediction sizes.”

## Verification and Responsibility

I reviewed and tested the generated suggestions before including them in the project. I ran the database migration, API checks, React lint and build commands, MCP tool calls, deterministic tests, fault-injection experiment, MockModel stopping test, and local Ollama agent scenarios.

The final implementation, test results, screenshots, written interpretations, and submitted repository remain my responsibility. AI-generated suggestions were modified where necessary to match the clinical-trial domain, course requirements, local hardware limitations, and existing project structure.

## Local Model Use

The application agent used the local Ollama model:

- Model: `qwen3:4b`
- Temperature: `0.0`
- Reduced context settings were used because the available hardware encountered memory-allocation errors with larger settings.

The local model selected tools and generated final answers. Application code enforced tool validation, retry limits, maximum steps, structured logging, and privacy safety rules independently of the model.