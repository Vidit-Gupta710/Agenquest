# AGENTS.md

Rules for any AI coding agent working in this repo. Read fully before writing code. Read `design.md` too: it is the source of truth for scope, data shapes, scoring and the API. Re-read the "Golden rules" at the start of every phase.

## Project

**AgentLighthouse** ("Lighthouse for AI agents"). The user pastes a website URL. TinyFish web agents attempt real tasks on it (find the price, find the return policy, reach checkout) while the user watches the live browser stream. We return an Agent-Readiness Score (0-100), a letter grade, the Agent Tax (steps and dollars an AI agent pays per task), an AI-written diagnosis of every failure with a copy-paste fix, and a comparison with 2-3 competitors.

Pipeline (`app/audit.py`): 1. read the site (TinyFish Fetch) 2. classify and pick 4 tasks (LLM) 3. run web agents, 2 at a time (TinyFish Agent + live stream) 4. diagnose failures (LLM) 5. score (pure Python) 6. benchmark peers (TinyFish Search + Fetch).

Hackathon rule: TinyFish must be core to the product, visibly. Remove TinyFish and nothing is left.

## Stack (do not swap without asking)

- **Backend:** Python 3.11, FastAPI, httpx, Pydantic, `openai` package (any OpenAI-compatible LLM), python-dotenv, pytest, ruff.
- **Frontend:** one `web/index.html` + `web/app.js`. Tailwind via CDN, vanilla JS. No build step, no frameworks.
- **TinyFish (REST via httpx):** Agent `POST https://agent.tinyfish.ai/v1/automation/run-async` + `GET /v1/runs/{id}`, Fetch `POST https://api.fetch.tinyfish.ai`, Search `GET https://api.search.tinyfish.ai`, and the `streaming_url` live stream. The official `tinyfish` Python SDK is an allowed swap.
- **Storage:** JSON files in `data/`. No database.
- **Hosting:** local demo is enough. Render or Railway free tier only after submission-critical work is done.
- **Never use:** a database, a JS build tool, or any extra dependency without listing it and the reason first.
- Pin all dependency versions. LLM base URL, key and model come from environment variables.

## Golden rules (in priority order)

1. **Phase gate.** Work on exactly one phase at a time, in order. Do not start phase N+1 until phase N's "Done when" check passes with evidence and a human has seen the gate pass. No jumping ahead, no "while I'm here" extras.
2. **Verify everything.** After every code change, run it and check it. Never write "should work". Show the command output.
3. **Minimal code.** Write the least code that meets the requirement. After it works, look for ways to shrink it, then re-verify. Target: under 900 lines of Python and under 500 lines of HTML and JS in total.
4. **Never guess external facts.** Check the TinyFish docs (https://docs.tinyfish.ai) for endpoints, parameters, field names and limits before coding. If you cannot verify, say so and make it configurable.
5. **Never claim what doesn't run.** A feature that does not work goes under "Roadmap" in the README, not "Features".
6. **Safety and ethics are not optional.** Section "Safety" below overrides convenience.

## Phases

| # | Phase | Done when |
|---|-------|-----------|
| 0 | Setup: public repo, folders, `.env.example`, `app/tinyfish.py`, `app/cache.py`, `app/llm.py`, `scripts/smoke_tinyfish.py` | Smoke test prints `FETCH OK`, `SEARCH OK`, `AGENT COMPLETED` with a parsed result, `LLM OK`; `data/cache/` holds 4 JSON files; `DEMO_MODE=1` prints the same 4 lines offline |
| 1 | Task library + runner: `app/tasks.py`, `app/runner.py`, `scripts/try_task.py` | `python -m scripts.try_task <shop url> find_price "running shoes"` prints a TaskResult with outcome, blocker, steps > 0, non-empty trace; rerun is a cache hit under 1 s; bad domain returns `outcome: failure` without crashing |
| 2 | Signals, task planning, peers: `app/signals.py`, `readability()` in `app/score.py`, `plan()` in `app/tasks.py` | `pytest -q tests/test_signals.py` passes; six signals correct on 3 sites checked by hand; `plan()` sensible for a shop, a SaaS and a travel site; `peers()` returns 3 domains, none the audited one, none from the SKIP list |
| 3 | Score, AI diagnosis, full pipeline: `app/score.py`, `app/diagnose.py`, `app/audit.py`, `scripts/audit_cli.py`, `scripts/benchmark.py`, `tests/test_score.py` | `python -m scripts.audit_cli <shop url>` finishes under 4 min and writes `data/reports/<domain>.json` with every key of the data contract; at least one diagnosis names a specific UI element; a site that failed checkout scores lower than one that succeeded; `DEMO_MODE=1` rerun is identical and under 3 s |
| 4 | API with live SSE: `app/main.py` | Server starts; `POST /api/audit` returns an `audit_id`; events stream `stage, signals, tasks, task_done, diagnosis, score, peers, done` then close; fresh site emits `task_update` with a `streaming_url`; unknown id gives 404, `ftp://x` gives 422, `/api/report/..%2F..%2F.env` gives 404 |
| 5 | UI: `web/index.html`, `web/app.js` | Cached sample renders under 3 s with no console errors; fresh URL shows a live agent iframe; every diagnosis card shows blocker, root cause, fix (copyable), severity; leaderboard sorted by score; no sideways overflow at 390 px; `not a url` shows a friendly message |
| 6 | Freeze, benchmark, ship: `data/sites.txt`, `data/leaderboard.json`, README | Benchmark of 8-10 real sites committed with `data/cache/` and `data/reports/`; clean clone + `DEMO_MODE=1` works on a second laptop; README has GIF, quick start, TinyFish table, architecture, benchmark, limitations, roadmap |

Feature freeze at phase 6. After that: only bug fixes, docs and media. If time runs short, cut in this order: peers, leaderboard view, sample buttons. Never cut: live agent view, score, diagnosis, README.

### Phase gate protocol

1. **Start:** state the phase number and a plan of at most 5 bullets: files, functions, gate commands. Wait for the human's "go".
2. **Build:** only the files listed. Nothing outside the phase.
3. **Verify:** run the verification checklist below, then run every gate command again with `DEMO_MODE=1`.
4. **Minimise:** run the minimise pass below, then re-run verification.
5. **Report:** post the status block (format below) with real command output, a list of changed files with line counts, and one new row in the AI work log at the bottom of this file.
6. **Stop** and say `PHASE <n> READY FOR HUMAN GATE`. A human re-runs the gate commands and ticks the checklist. Commit as `phase N: <what works now>` and push. Proceed to the next phase only after that, or if the human has explicitly said to continue through phases, and still only after the gate passes.

If a phase fails its check, fix it inside the same phase. **Two strikes:** if a gate check fails twice, stop and report what was tried; the human decides to fix, cut scope, or use a fallback. Never move on with a known failure or a skipped check. If blocked, say what is blocked and why.

## Verification checklist (after every code change, not only at phase end)

- Run the code you wrote. For logic, write or update unit tests first or alongside.
- `pytest -q` passes. Do not delete, skip or weaken a test to make it pass; fix the cause.
- `ruff format .` then `ruff check .` clean (line length 100).
- Run the gate commands a second time with `DEMO_MODE=1` to prove the cache replays.
- Check at least one failure path (bad URL, blocked site, failed agent run).
- Frontend touched: open it in a browser, check the console, check at 390 px and 1440 px.
- List every changed file with its line count. Any file over 150 lines is split before declaring done.
- Read your own diff: remove debug prints, unused imports, commented-out code, leftover TODOs.
- Compare behaviour to the phase's "Done when" line, item by item.

## Minimal code rules

- Before writing, search the repo and the standard library for something that already does the job. Reuse it.
- Functions over classes. Pydantic models are for data shapes only; logic lives in plain functions.
- Each function under 30 lines; each file under 150 lines. If a file grows past that, split it by job, not by type.
- Every file starts with a one-line docstring stating its single job. Type hints on every function signature.
- Names say what things are (`run_agent`, `parse_result`, `score_report`). No `utils.py`, `helpers.py` or `manager.py`.
- No speculative features, config options, abstractions or base classes. One use means no wrapper.
- No duplicate logic. Extract only when the same code appears 3 or more times.
- Delete dead code, unused parameters and unused dependencies as you go.
- Short does not mean clever: no code golf. Brief comments only for "why".
- **Minimise pass (end of each phase):** re-read the new code and cut anything that can go without changing behaviour. Re-run the full verification checklist after any cut.

## Architecture rules

- **One place per external service:** all TinyFish calls live in `app/tinyfish.py`. All LLM calls go through `app/llm.py` `ask_json()`. Nothing else imports `httpx` or `openai` for these.
- **Cache everything:** every TinyFish and LLM call is wrapped with `@cached` (`app/cache.py`). Never cache infra failures (`status == "FAILED"`). Never run an uncached audit twice for the same URL.
- **DEMO_MODE=1:** replays only from `data/cache/`, needs no keys and no network, and raises a clear error if something is not cached. `data/cache/` is committed so anyone can run the demo.
- **Pure scoring:** `app/score.py` and the parsing in `app/signals.py` are pure functions with unit tests. The LLM never decides the score, grade, weights or Agent Tax.
- **Thin routes:** `app/main.py` parses input, calls the pipeline, streams events. Logic lives elsewhere.
- **Errors at the edges:** catch in `app/audit.py` and `app/main.py`, turn them into an SSE `error` or a friendly UI message, and keep the audit going. One failed task or peer lookup must never crash an audit.
- **Config only through environment variables**, loaded once with python-dotenv in `app/main.py` (and scripts). Keys: `TINYFISH_API_KEY`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `DEMO_MODE`.
- **Data contract:** one report object (see `design.md` and the Pydantic models in `app/models.py`) is what everything passes around. Event names and shapes (`stage, signals, tasks, task_update, task_done, diagnosis, score, peers, done, error`) and the `app.js` function names are fixed. Change them in `design.md` first.
- **The UI never talks to TinyFish directly.** It only receives SSE from our API, including each agent's `streaming_url`, shown in an iframe with a fallback (step counter and last action) if no URL arrives within 10 s.
- **Security of file routes:** report lookups use `pathlib.Path(domain).name` to block path tricks.

## TinyFish facts the code depends on (verify against docs before changing)

- Auth is one header, `X-API-Key`, from `TINYFISH_API_KEY`.
- Run statuses: `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`. `COMPLETED` only means the browser worked, not that the goal succeeded. Always read our own `outcome` field from the result.
- The run object carries `num_of_steps`, `streaming_url`, `video_url` (expires in 15 minutes) and a `steps` array.
- `output_schema` must be an object at the top level, enum values must be strings, and `additionalProperties`, `const` and `oneOf` are rejected.
- `agent_config.max_duration_seconds` caps run time. Do not rely on `max_steps` (beta only).
- Pay-as-you-go runs 2 agents at once: keep the semaphore at 2.
- Agent steps cost about $0.016 each; failed runs are free. Search is free up to 12,000 requests a day, Fetch up to 1,000 URLs a day.

## Agent task goals

Every agent goal follows these rules:

1. State the role: "You are testing whether an AI agent can use this website."
2. One concrete task with a clear finish line.
3. Safety limits: browse anonymously, no login, no account creation, no personal or payment data, no form submission.
4. Say what to do about obstacles (for example, try to close a popup and continue).
5. Define success, partial and failure in one sentence each.
6. Ask the agent to pick the single main blocker from the fixed enum: `none, cookie_or_popup, captcha_or_bot_block, login_wall, element_not_found, unlabeled_control, slow_or_dynamic_content, confusing_navigation, other`.

Vague goals fail. If a task fails on a site where a human succeeds in 20 seconds, tighten the goal before blaming the site.

## Safety, privacy, ethics

- Agents only read public pages. They never log in, submit forms, pay, or enter personal data. At most 4 agent runs per site per audit. Never weaken this.
- No real personal data in code, tests, fixtures, logs, cache or the repo. Use fake test data. Check cached pages before committing.
- Benchmark results are a dated snapshot of AI-agent usability, not a judgement of the company. Say so in the UI and README.
- Diagnoses use only evidence in the step trace. If the trace is too thin, the output says "insufficient evidence" with confidence below 0.4; the UI hides diagnoses under 0.4.
- Use only numbers from our own benchmark run in the post, deck and README. Never invent statistics.
- README keeps an honest "Limitations" and "Roadmap" section. Agents are non-deterministic and scores can move a few points between runs.

## Security and cost

- No secrets in code or git. `.env` is in `.gitignore` from the first commit. `.env.example` has empty values. Never print secrets. `git grep TINYFISH_API_KEY=` must show only `.env.example`.
- Credit budget (about $13, roughly 800 agent steps, about 50 steps per audit): phase 1 smoke and debugging 2 audits, phase 3 report checks 2, benchmark 9, video recording 1, spare 1. Do not run live agents outside these without asking. Post the wallet status when it is low.
- Add a dependency only if the stdlib or existing libraries cannot do the job; list it and the reason.
- Free hosting only, no always-on paid resources.

## Git and commits

- Commit #1 contains only `design.md`, `AGENTS.md` and `.gitignore`, so history shows design before code.
- Commit at every phase gate, and every 30-45 minutes, with `phase N: <what works now>`, for example `phase 1: agent task runner with cache and parsed results`.
- Only the backend lead merges to `main`. Other roles work on branches named after their role. Two people never edit the same file at the same time.

## Status block (post after every phase)

```
Phase: <n> - <name>
Status: PASSED | FAILED | BLOCKED
Done-when check: <how it was met, with command output>
Verification: pytest <result>, ruff <result>, DEMO_MODE=1 rerun <result>, browser check <result if relevant>
Minimise pass: <what was removed or simplified, lines before/after if useful>
Changed files: <file: line count>
Assumptions: <list>
Open issues: <list or none>
Next phase: <n+1> (waiting for go-ahead)
```

## When unsure

Ask one clear question, or state your assumption and continue only if it is low-risk and reversible. Anything not in `design.md` needs a human "yes" and a `design.md` edit first. Never invent API parameters, library behaviour or results.

## Run commands

- install: `pip install -r requirements.txt`
- server: `uvicorn app.main:app --reload --port 8000`
- tests: `pytest -q`
- smoke: `python -m scripts.smoke_tinyfish`
- format: `ruff format .`
- demo (no keys): `DEMO_MODE=1 uvicorn app.main:app --port 8000`

---

## AI work log

Every time a coding agent writes or changes code, it appends one row before reporting done. A human fills "Verified by" only after running the gate check. No verification, no merge. Summarise prompts in one line.

| # | Time (IST) | Phase | Tool and model | What the AI did | Files | Human decision | Verified by |
|---|------------|-------|----------------|-----------------|-------|----------------|-------------|
| 1 | | 0 | | | | | |

## AI suggestions we rejected

| Suggestion | Why we rejected it |
|------------|--------------------|
| Use a database for reports | JSON files are enough for a demo and easier to inspect |

## What humans did (not AI)

- Chose the problem, the behavioural-testing angle and the Agent Tax metric.
- Designed the scoring weights and blocker taxonomy.
- Picked and reviewed the benchmark sites and checked every diagnosis shown in the demo.
- Wrote the pitch, recorded the video, made the deck.
