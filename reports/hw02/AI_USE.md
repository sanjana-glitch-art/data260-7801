# DATA-260 Homework 2 AI Use

## 1. What did I use an AI assistant for, and what did I do myself?

I used an AI assistant to help interpret the Homework 2 requirements,
troubleshoot errors, and organize the required experiments and documentation.

I personally created and managed the repository files, ran all installation
and execution commands, tested the FastAPI application, tested add, update,
delete, and search operations, captured the responsive and interface-state
screenshots, ran the stateful graph, executed all 75 experimental runs,
inspected the generated JSON and CSV files, and verified that the reported
metrics matched the machine-readable results.

## 2. What AI-produced output was wrong or unsuitable?

During the first normal graph test, the AI Reviewer incorrectly claimed that
a Planner summary contained 27 or 28 words and exceeded the assignment's
25-word limit. The summary actually contained substantially fewer than 25
whitespace-separated words.

The Reviewer also claimed that a relevant tag was invalid because it was not
a standard clinical-trial metadata term. The assignment did not require tags
to come from a controlled vocabulary. It only required exactly three string
tags, each between 3 and 30 characters.

## 3. How did I detect or independently verify the problem?

The Planner proposal had already passed the Pydantic schema. I independently
verified the summary using Python's whitespace-based word-counting behavior,
which is the same deterministic rule used by the validator:

`len(summary.split())`

I also reread the assignment requirements and confirmed that they specify tag
count, type, and length but do not require a standardized clinical vocabulary.
This demonstrated that the Reviewer output was unsuitable even though it was
valid JSON.

## 4. What did I change, and why does it work now?

I kept Pydantic as the authoritative validator for mechanical schema
requirements. The Reviewer prompt was changed to state that the proposal had
already passed deterministic validation. The prompt also supplies the measured
summary word count and instructs the Reviewer to focus only on semantic
relevance and factual support.

This works because exact requirements such as tag count, tag length, and
summary word count are now enforced deterministically in Python. The model
Reviewer is used only for the judgment task it is better suited for: checking
whether the proposed tags and summary are reasonably supported by the source
clinical-trial listing.

I also retained a turn ceiling in the graph so that repeated validation or
review failures cannot create an infinite correction loop.