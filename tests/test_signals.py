from app.signals import robots_ok, root, signals_from


def test_root():
    assert root("shop.in/x?y=1") == "https://shop.in"


def test_robots():
    assert robots_ok("User-agent: *\nDisallow: /admin")
    assert not robots_ok("User-agent: *\nDisallow: /")
    assert not robots_ok("User-agent: GPTBot\nDisallow: /")
    assert not robots_ok("")


def test_bot_blocked_home():
    s = signals_from(
        "https://a.com", {"results": [], "errors": [{"url": "https://a.com/", "error": "bot_blocked"}]}
    )
    assert not s["fetchable"] and s["fetch_error"] == "bot_blocked"