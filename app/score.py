"""Agent-Readiness Score, grade and Agent Tax. Pure functions, unit-tested."""
from statistics import mean

from app.tasks import progress

WEIGHTS = {
    "fetchable": 4, "text_rendered": 3, "llms_txt": 2,
    "robots_ok": 2, "sitemap": 2, "meta": 2,
}
USD_PER_STEP = 0.016  # TinyFish published per-step price


def readability(signals):
    return sum(w for k, w in WEIGHTS.items() if signals.get(k))


def grade(total):
    return next(g for g, cut in (("A", 85), ("B", 70), ("C", 55), ("D", 40), ("F", 0)) if total >= cut)


def score(tasks, signals):
    prog = [progress(t) for t in tasks] or [0.0]
    eff = [
        p * min(1, t["expected_steps"] / max(t["steps"], 1))
        for p, t in zip(prog, tasks)
    ] or [0.0]
    s, e, r = 65 * mean(prog), 20 * mean(eff), readability(signals)
    total = round(s + e + r)
    return {
        "total": total, "grade": grade(total),
        "success": round(s), "efficiency": round(e), "readability": r,
    }


def agent_tax(tasks):
    steps = mean([t["steps"] for t in tasks]) if tasks else 0
    return {"avg_steps": round(steps, 1), "usd_per_task": round(steps * USD_PER_STEP, 3)}
