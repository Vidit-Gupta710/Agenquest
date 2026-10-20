"""Agent-Readiness Score, grade and Agent Tax. Pure functions, unit-tested."""
from statistics import mean

OUTCOME = {"success": 1.0, "partial": 0.5, "failure": 0.0}
WEIGHTS = {
    "fetchable": 6,
    "text_rendered": 5,
    "llms_txt": 4,
    "robots_ok": 4,
    "sitemap": 3,
    "meta": 3,
}
USD_PER_STEP = 0.016  # TinyFish published per-step price


def readability(signals):
    return sum(w for k, w in WEIGHTS.items() if signals.get(k))


def grade(total):
    return next(g for g, cut in (("A", 85), ("B", 70), ("C", 55), ("D", 40), ("F", 0)) if total >= cut)


def score(tasks, signals):
    val = [OUTCOME.get(t.get("outcome"), 0.0) for t in tasks] or [0.0]
    eff = [
        v * min(1, t["expected_steps"] / max(t["steps"], 1))
        for v, t in zip(val, tasks)
    ] or [0.0]
    s, e, r = 55 * mean(val), 20 * mean(eff), readability(signals)
    total = round(s + e + r)
    return {
        "total": total,
        "grade": grade(total),
        "success": round(s),
        "efficiency": round(e),
        "readability": r,
    }


def agent_tax(tasks):
    steps = mean([t["steps"] for t in tasks]) if tasks else 0
    return {"avg_steps": round(steps, 1), "usd_per_task": round(steps * USD_PER_STEP, 3)}