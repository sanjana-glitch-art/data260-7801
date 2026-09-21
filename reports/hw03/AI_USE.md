# Homework 3 AI Use Statement

## 1. What I Used an AI Assistant For

I used an AI assistant to help interpret the Homework 3 requirements,
organize the implementation steps, troubleshoot FastAPI and PowerShell
errors.

## 2. What I Did Myself

I created and maintained the GitHub repository, ran all commands locally,
installed the dependencies, started the FastAPI application, tested each
route, entered credentials, inspected the session cookie, and captured
the required screenshots.

I also downloaded and prepared the corpus, ran the three chunking
pipelines on my computer, reviewed the output, checked the retrieved
sources, examined the false-positive results, and recorded the actual
measurements produced by my system.

I verified the application and retrieval results before including them in
the report.

## 3. AI Output That Was Wrong or Unsuitable

One AI-produced version of `auth.py` annotated some FastAPI route
functions with the union type:

`HTMLResponse | RedirectResponse`

With the installed FastAPI version, the application failed during import
because FastAPI attempted to treat that union as a Pydantic response
model. The error reported that the response field arguments were invalid.

Another initial issue was that the expired-session check inspected the
session only after the timeout helper had already cleared it. That could
prevent the application from distinguishing an expired session from a
user who had never logged in.

## 4. How I Detected or Verified the Problem

I detected the response-annotation problem by importing the FastAPI
application and printing its registered routes. The import produced a
`FastAPIError` before the server could start.

I verified the corrected application by:

- Compiling `code/main.py` and `code/auth.py`
- Importing the FastAPI application
- Printing its registered routes
- Opening the login page
- Testing invalid credentials
- Testing valid credentials
- Opening the protected dashboard
- Logging out
- Attempting to reuse the logged-out session
- Waiting for the configured idle timeout
- Attempting to access the dashboard after expiration
- Inspecting the `Set-Cookie` response header

For the retrieval experiment, I verified the result counts, source
matches, cosine similarities, vector dimensions, chunk counts, and raw
CSV and JSONL files.

## 5. What I Changed and Why It Works

I replaced the unsupported union return annotations with the general
FastAPI `Response` type. The route functions can now return either an
HTML template response or a redirect without FastAPI attempting to
construct an invalid Pydantic response model.

I also recorded whether the session contained a user before calling the
timeout-validation helper. This allows an expired session to redirect to
`/login?expired=1` and show the appropriate Bootstrap warning.

For retrieval evaluation, the first five questions produced no source
mismatches. Following the assignment instructions, I added and committed
an additional broad domain question before rerunning the experiment. The
additional question produced several confidently related passages from
the wrong source, allowing me to examine a real false-positive retrieval.

These changes work because they were tested using the running FastAPI
application and the machine-readable retrieval results generated on my
local computer.