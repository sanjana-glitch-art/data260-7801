# Homework 5 Reflection

Homework 5 extended the clinical-trial application into a more complete full-stack and agent-based system. The relational database was expanded with a sponsors table, and each clinical trial was connected to a sponsor through a foreign key. The React frontend was updated to use Redux Toolkit for shared trial state and to support listing, creating, updating, and deleting records.

Two MCP servers were implemented. The MealDB server demonstrated tools that call an external API, while the clinical-trial server exposed three domain-specific database tools: searching trials, retrieving trial details, and summarizing trials by phase. All domain tools returned a consistent envelope containing `ok`, `data`, and `error`, which made successful and unsuccessful results easier to process.

The fault-injection experiment demonstrated why retry logic is important. Calls were tested at 0%, 20%, and 50% injected-failure rates, with 50 calls per rate. The retry implementation used a timeout, a maximum of three attempts, and exponential backoff. Higher failure rates required more attempts and produced more exhausted calls.

The local Ollama agent used `qwen3:4b` to select and execute tools. In the search scenario, it found three sleep-related clinical trials. It also retrieved details for trial ID 1 and produced phase-summary information. The privacy scenario demonstrated the safety rule by blocking a request for a submitter email address. A deterministic `MockModel` test verified that the agent stops after reaching its maximum step count.

The main lesson was that reliable agents require more than model output. Structured tool results, input validation, retry limits, safety checks, deterministic tests, and execution logs are necessary to make agent behavior observable and controlled.