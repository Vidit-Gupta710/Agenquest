# AgentLighthouse

**AgentLighthouse** audits how well AI web agents can use a website. Paste a URL — real TinyFish web agents attempt 4 tasks (find price, find policy, reach checkout, etc.) while you watch the live browser stream. Get an Agent-Readiness Score (0–100), letter grade, Agent Tax (cost per task), AI diagnoses with copy-paste fixes, and competitor comparison.

> **Built for the TinyFish Hackathon** — TinyFish is core to the product. Remove TinyFish and nothing is left.

---

## Demo

```bash
# 1. Clone and install
git clone https://github.com/Vidit-Gupta710/Lighthouse.git
cd Lighthouse
pip install -r requirements.txt

# 2. Add your API keys to .env (see .env.example)
cp .env.example .env
# Edit .env with your TINYFISH_API_KEY and LLM keys

# 3. Run the server
uvicorn app.main:app --port 8000

# 4. Open http://localhost:8000
```

**No keys? No problem.** The demo works offline with `DEMO_MODE=1`:

```bash
DEMO_MODE=1 uvicorn app.main:app --port 8000
# Open http://localhost:8000 → click "Try a sample shop"
```

---

## Quick Start (3 commands)

```bash
git clone https://github.com/Vidit-Gupta710/Lighthouse.git
cd Lighthouse
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

Then open http://localhost:8000 and paste a URL (or click a sample button).

---

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   Paste URL │────▶│  TinyFish    │────▶│   6-Step     │
│             │     │  Fetch       │     │   Pipeline   │
└─────────────┘     └──────────────┘     └──────┬───────┘
                                                 │
                    ┌──────────────┐     ┌───────▼───────┐
                    │  TinyFish    │────▶│  1. Signals  │──▶ 6 readability checks
                    │  Search      │     └───────┬───────┘
                    └──────────────┘             │
                                                 ▼
                    ┌──────────────┐     ┌───────▼───────┐
                    │    LLM       │────▶│  2. Classify │──▶ site_type + 4 tasks
                    └──────────────┘     └───────┬───────┘
                                                 │
                    ┌──────────────┐     ┌───────▼───────┐
                    │  TinyFish    │────▶│  3. Run Tasks│──▶ 2 concurrent agents
                    │  Agent       │     └───────┬───────┘
                    └──────────────┘             │
                                                 ▼
                    ┌──────────────┐     ┌───────▼───────┐
                    │    LLM       │────▶│  4. Diagnose │──▶ blocker, root cause, fix
                    └──────────────┘     └───────┬───────┘
                                                 │
                                    ┌────────────▼────────────┐
                                    │  5. Score (pure Python) │──▶ 0-100, grade, Agent Tax
                                    └────────────┬────────────┘
                                                 │
                    ┌──────────────┐     ┌───────▼───────┐
                    │  TinyFish    │────▶│  6. Peers    │──▶ 3 competitors + signals
                    │  Search+Fetch│     └───────────────┘
                    └──────────────┘
```

---

## TinyFish Integration

| Surface | Endpoint | Purpose |
|---------|----------|---------|
| **Agent** | `POST /v1/automation/run-async` + `GET /v1/runs/{id}` | Run 4 web agent tasks per audit (2 concurrent), stream live browser via `streaming_url` |
| **Fetch** | `POST /fetch` | Read homepage, robots.txt, llms.txt, sitemap.xml for 6 readability signals |
| **Search** | `GET /search` | Find 3 competitor domains for relative benchmarking |
| **Live Stream** | `streaming_url` from Agent run | Embedded in UI iframe — watch agents work live |

**Cost**: ~$0.016 per agent step. Failed runs free. Search/Fetch free (daily limits: 12k/1k). Typical audit: ~50 steps = $0.80.

---

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/audit` | Start audit → returns `{audit_id}` |
| `GET` | `/api/audit/{id}/events` | SSE stream: `stage`, `signals`, `tasks`, `task_update`, `task_done`, `diagnosis`, `score`, `peers`, `done`, `error` |
| `GET` | `/api/report/{domain}` | Get saved report JSON |
| `GET` | `/api/leaderboard` | Get benchmark leaderboard |
| `GET` | `/` | Serves UI |

---

## Configuration

Create `.env` from `.env.example`:

```bash
# TinyFish (required)
TINYFISH_API_KEY=sk-tinyfish-...

# LLM (required - any OpenAI-compatible)
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
LLM_API_KEY=...
LLM_MODEL=gemini-flash-latest

# Demo mode (no keys, no network)
DEMO_MODE=0
```

**LLM Providers tested**: Google Gemini (free tier), Groq, OpenRouter, OpenAI.

---

## Project Structure

```
agentlighthouse/
├── app/
│   ├── main.py          # FastAPI + SSE
│   ├── audit.py         # 6-step pipeline
│   ├── tinyfish.py      # All TinyFish calls (cached)
│   ├── cache.py         # Disk cache + DEMO_MODE
│   ├── llm.py           # LLM via openai package
│   ├── tasks.py         # 10 tasks, 4 site types, goals
│   ├── runner.py        # Semaphore(2) task runner
│   ├── signals.py       # 6 readability signals + peers
│   ├── score.py         # Pure scoring (no LLM)
│   └── diagnose.py      # LLM diagnosis of failures
├── web/
│   ├── index.html       # Single-page UI
│   └── app.js           # SSE client + rendering
├── scripts/
│   ├── smoke_tinyfish.py    # Phase 0 check
│   ├── try_task.py          # Test one task
│   ├── audit_cli.py         # Full audit CLI
│   └── benchmark.py         # Batch leaderboard
├── tests/
│   ├── test_signals.py      # Signal parsing unit tests
│   └── test_score.py        # Scoring unit tests
├── data/
│   ├── cache/           # Committed — enables DEMO_MODE=1
│   ├── reports/         # Saved audit JSONs
│   ├── sites.txt        # Benchmark URLs
│   └── leaderboard.json # Generated leaderboard
├── requirements.txt     # Pinned dependencies
├── design.md            # Build contract
├── AGENTS.md            # AI agent rules + work log
└── .env.example         # Template
```

---

## Benchmark Results

| Rank | Domain | Type | Score | Grade | Agent Tax |
|------|--------|------|-------|-------|-----------|
| 1 | example.com | services | 14 | F | $0.052 |

> **Note**: Full benchmark (9 sites) could not complete due to LLM free-tier rate limits (429). The `data/cache/` contains a complete cached audit of `example.com` for offline demo.

---

## Limitations

- **LLM rate limits**: Free tiers (Gemini, Groq) hit 429 quickly. Diagnosis stage fails when quota exhausted.
- **Non-deterministic scores**: Same site may score ±5 points between runs.
- **No auth/payments**: Agents never log in, submit forms, or enter personal data.
- **English only**: Tasks and prompts are English-only.
- **No scheduled monitoring**: Single-shot audits only.
- **Cache grows**: `data/cache/` accumulates JSON files over time.

---

## Roadmap

- [ ] Scheduled monitoring with webhooks
- [ ] PDF/HTML report export
- [ ] User accounts & audit history
- [ ] Multi-language support
- [ ] Auto-generated PR fixes for detected issues
- [ ] Team workspaces & shared leaderboards

---

## License

MIT — Built for the TinyFish Hackathon.