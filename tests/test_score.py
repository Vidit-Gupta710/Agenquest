from app.score import agent_tax, grade, score

ALL = {k: True for k in ("fetchable", "text_rendered", "llms_txt", "robots_ok", "sitemap", "meta")}


def task(outcome, steps=6, expected=6):
    return {"outcome": outcome, "steps": steps, "expected_steps": expected}


def test_perfect_site_scores_100():
    assert score([task("success")] * 4, ALL)["total"] == 100


def test_dead_site_scores_0():
    assert score([task("failure", 0)] * 4, {})["total"] == 0


def test_slow_success_loses_efficiency():
    assert score([task("success", 24)] * 4, ALL)["efficiency"] == 5


def test_grades_and_tax():
    assert [grade(x) for x in (85, 70, 55, 40, 39)] == ["A", "B", "C", "D", "F"]
    assert agent_tax([task("success", 10)])["usd_per_task"] == 0.16