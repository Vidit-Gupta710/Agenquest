# AgentLighthouse

**Lighthouse for AI agents.** Paste a website URL. We send TinyFish web agents through the real customer journeys (search, sort, add to cart, apply coupon, reach payment; find a job and get the application ready; book the cheapest trip) and return an Agent-Readiness Score (0–100), a grade, the Agent Tax per journey, an AI-written diagnosis of every failure with a copy-paste fix, and a comparison with competitors found via TinyFish Search.

In **My Account mode** the same agents work inside the user's own signed-in account: they fill the cart or prepare an application and stop before anything is bought or sent.

## Why this matters

AI agents are starting to shop, book and apply on people's behalf. Most sites are built only for human eyes — cookie walls, unlabeled icon buttons, CAPTCHAs, infinite scroll, login walls silently turn agents away. Static checkers (robots.txt, llms.txt) can't see this. AgentLighthouse is the behavioural test: it watches an agent try the job, measures how far it gets, and tells the site owner exactly what to fix.

## Quick start

```powershell
pip install -r requirements.txt
cp .env.example .env     # add TINYFISH_API_KEY, LLM_BASE_URL, LLM_API_KEY, LLM_MODEL
uvicorn app.main:app --port 8000
```

Then open http://localhost:8000.

**No keys?** Demo mode replays cached runs:

```powershell
$env:DEMO_MODE=1; uvicorn app.main:app --port 8000
```

## How we use TinyFish

| Surface | Endpoint | Where | Why |
|---|---|---|---|
| Agent API | `POST /v1/automation/run-async`, `GET /v1/runs/{id}` | [app/tinyfish.py](app/tinyfish.py), [app/runner.py](app/runner.py) | Each deep journey; success, step count, step trace are our measurement |
| Live stream | `streaming_url` on the run object | sent to the UI over SSE; iframe in [web/app.js](web/app.js) | Watch the agent work live; the demo's hero moment |
| Fetch API | `POST https://api.fetch.tinyfish.ai` | [app/signals.py](app/signals.py) | Reads `/`, `/robots.txt`, `/llms.txt`, `/sitemap.xml`; error codes are signals |
| Search API | `GET https://api.search.tinyfish.ai` | [app/signals.py](app/signals.py) | Finds competitors so the score is relative |
| Browser Context Profiles | `POST /v1/profiles`, `/setup-session`, `/save` | [app/accounts.py](app/accounts.py), [app/remote_login.py](app/remote_login.py) | Saves the user's own signed-in session; agent never sees the password |

Every TinyFish and LLM call is wrapped with `@cached` in [app/cache.py](app/cache.py). The `data/cache/` directory is committed so `DEMO_MODE=1` works without any API keys or network.

## Architecture

```
URL → signals (Fetch) → classify (LLM) → run 3 deep journeys (Agent)
                                       → diagnose failures (LLM) → score → peers (Search)
```

Each journey is a chain of **milestones**. Example — "buy the cheapest match":

`searched → sorted_by_price → product_opened → variant_selected → added_to_cart → coupon_applied → checkout_reached`

The agent reports `furthest_milestone`. Progress = reached ÷ reachable. The **hard stop**: no agent ever pays, orders, creates an account, or presses a final Send/Submit/Apply/Book/Confirm button. It stops with that button visible and reports.

## Scoring

```
success      = 65 × mean(progress)            (0–65)
efficiency   = 20 × mean(progress × min(1, expected_steps / actual_steps))   (0–20)
readability  = fetchable 4 + text_rendered 3 + llms_txt 2
             + robots_ok 2 + sitemap 2 + meta 2                              (0–15)
total        = round(success + efficiency + readability)                     (0–100)
grade        = A ≥ 85, B ≥ 70, C ≥ 55, D ≥ 40, else F
agent_tax    = avg_steps × $0.016 per journey (TinyFish's per-step price)
```

Scoring is **pure Python** — unit-tested in [tests/test_score.py](tests/test_score.py). The LLM never touches the score; it only writes diagnoses and picks the peer-query.

## Project layout

```
app/
  main.py          FastAPI routes, SSE, serves web/
  jobs.py          background job + event queue
  audit.py         6-step pipeline, emits events
  tinyfish.py      Fetch, Search, Agent, Browser Context Profiles
  runner.py        one journey → one TaskResult, 2 at a time
  tasks.py         journey library (15 journeys across 5 site types)
  signals.py       machine-readability signals
  score.py         score, grade, Agent Tax
  diagnose.py      LLM failure diagnosis
  cache.py         disk cache, DEMO_MODE replay, private cache
  accounts.py      My Account mode routes
  remote_login.py  Playwright CDP bridge for the login window
  cart.py          signed-in goals (cart, apply_job, connect_note, message_draft)
  llm.py           one function: ask_json(system, user) → dict
web/               vanilla HTML + Tailwind CDN + app.js (no build step)
scripts/
  smoke_tinyfish.py   Phase 0 smoke test
  try_task.py         run one journey from the CLI
  audit_cli.py        run a full audit and write data/reports/<domain>.json
  benchmark.py        run data/sites.txt, write data/leaderboard.json
  ci_check.py         Phase 8: block a deploy if the agent gets stuck
.github/workflows/
  agent-check.yml     example CI gate for a store's repo
tests/              pytest on scoring and signal parsing
data/
  sites.txt           benchmark URLs
  cache/              committed; lets anyone run DEMO_MODE=1
  reports/            one JSON report per audited domain
```

## Journey library (5 site types × 3 journeys each)

- **ecommerce**: `buy_cheapest`, `filter_shop`, `exchange_flow`
- **social** (jobs/networking): `apply_job`, `connect_note*`, `message_draft*`
- **travel**: `book_cheapest`, `filter_trip`, `cancel_rules`
- **saas**: `plan_signup`, `book_demo`, `docs_howto`
- **services**: `book_slot`, `get_quote`, `compare_offers`

`*` = signed-in only (My Account mode).

## Safety

- Agents only read public pages. They **never** log in, pay, order, create an account, or press a final Send/Submit. They stop with that button visible.
- No real personal data in code, tests, fixtures, logs or cache. The agent uses fake test data (`name "Test Agent"`, `email test@example.com`).
- **My Account mode**: the user signs in themselves in the TinyFish setup browser; we never see or store passwords. The agent never changes settings, address or payment, and never removes items already in the cart. Disconnect deletes the TinyFish profile.
- At most 3 agent runs per audit. Benchmark results are a dated snapshot, not a judgement of the company.

## Features

- Deep journeys with milestone progress (per-journey % reached)
- Live agent browser stream, embedded in the UI via `streaming_url`
- AI diagnosis of every non-success journey, with copy-paste fix and severity
- Score + grade + Agent Tax per journey
- Peer comparison (3 competitors found via TinyFish Search)
- My Account mode: TinyFish Browser Context Profiles + Playwright-CDP login bridge
- CI check: one agent through staging checkout, blocks the deploy if it gets stuck ([scripts/ci_check.py](scripts/ci_check.py))
- Disk cache + `DEMO_MODE=1` replay (no keys, no network needed for the demo)

## Limitations & Roadmap

- **React/TypeScript front-end** (Phase 5 of the playbook): current UI is vanilla HTML + Tailwind CDN. Works end-to-end but not the polished design in the playbook mockups.
- **My Account login window UI**: backend endpoints (`/api/accounts/connect`, `/ws/login/{session_id}`, `/api/accounts/save/...`) are live, but the browser-side canvas that renders the CDP screencast frames isn't wired in yet.
- **Benchmark**: `data/sites.txt` is set up but a full 8–10 site benchmark hasn't been run with the v2 journey library yet. Run `python -m scripts.benchmark` with credits.
- **CI check**: script and example workflow ship, but haven't been run against a real broken staging page.
- **Vault-based auto re-login**: not implemented. Expired sessions ask the user to sign in again.
- **Multi-user accounts, PDF export, scheduled monitoring**: roadmap only.
- Agents are non-deterministic — scores can move a few points between runs.

## Commit history

Per the playbook: `design.md` + `AGENTS.md` first, then one commit per phase gate.
