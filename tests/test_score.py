from app.score import agent_tax, grade, score

ALL = {k: True for k in ("fetchable", "text_rendered", "llms_txt", "robots_ok", "sitemap", "meta")}


def journey(reached, steps=18, jid="filter_shop"):
    return {"id": jid, "furthest_milestone": reached, "steps": steps, "expected_steps": 18}


def test_perfect_site_scores_100():
    assert score([journey("top3_listed")] * 3, ALL)["total"] == 100


def test_dead_site_scores_0():
    assert score([journey("none", 0)] * 3, {})["total"] == 0


def test_halfway_gets_partial_credit():
    # filter_shop has 5 milestones; "size_filtered" is the 3rd -> 3/5 = 0.6; 65*0.6=39
    assert score([journey("size_filtered")] * 3, {})["success"] == 39


def test_sign_in_gate_is_not_a_failure():
    # apply_job public_until=apply_started; reaching apply_started counts as 100% in audit mode
    assert score([journey("apply_started", 18, "apply_job")], {})["success"] == 65


def test_slow_journey_loses_efficiency():
    # top3_listed = full progress (1.0). 18 expected, 72 actual -> eff = 1 * 18/72 = 0.25, *20 = 5
    assert score([journey("top3_listed", 72)] * 3, ALL)["efficiency"] == 5


def test_grades_and_tax():
    assert [grade(x) for x in (85, 70, 55, 40, 39)] == ["A", "B", "C", "D", "F"]
    assert agent_tax([journey("top3_listed", 30)])["usd_per_task"] == 0.48
