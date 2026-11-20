"""Show the TinyFish setup browser to the user and pass their clicks and keys back.
Never log what passes through here: it includes the user's password keystrokes."""
import asyncio
import json

try:
    from playwright.async_api import async_playwright
except ImportError:  # playwright is optional until Phase 6 is turned on
    async_playwright = None

KEYS = {"Enter": 13, "Backspace": 8, "Tab": 9, "Escape": 27, "ArrowLeft": 37,
        "ArrowUp": 38, "ArrowRight": 39, "ArrowDown": 40, "Delete": 46}


async def _send_input(cdp, m):
    if m["type"] == "mouse":
        await cdp.send("Input.dispatchMouseEvent", {
            "type": m["kind"], "x": m["x"], "y": m["y"],
            "button": "left", "clickCount": 1,
        })
    elif m["type"] == "wheel":
        await cdp.send("Input.dispatchMouseEvent", {
            "type": "mouseWheel", "x": m["x"], "y": m["y"],
            "deltaX": 0, "deltaY": m["dy"],
        })
    elif m["type"] == "text":
        await cdp.send("Input.insertText", {"text": m["text"]})
    elif m["type"] == "key" and m["key"] in KEYS:
        code = KEYS[m["key"]]
        for kind in ("keyDown", "keyUp"):
            await cdp.send("Input.dispatchKeyEvent", {
                "type": kind, "key": m["key"], "windowsVirtualKeyCode": code,
            })


async def bridge(ws, cdp_url, start_url):
    if async_playwright is None:
        await ws.send_text(json.dumps({"type": "error", "message": "playwright not installed; pip install playwright && playwright install chromium"}))
        return
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(cdp_url)
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto(start_url)
        cdp = await ctx.new_cdp_session(page)

        async def frame(f):
            await ws.send_text(json.dumps({
                "type": "frame", "jpeg": f["data"],
                "w": f["metadata"]["deviceWidth"],
                "h": f["metadata"]["deviceHeight"], "url": page.url,
            }))
            await cdp.send("Page.screencastFrameAck", {"sessionId": f["sessionId"]})

        cdp.on("Page.screencastFrame", lambda f: asyncio.create_task(frame(f)))
        await cdp.send("Page.startScreencast", {
            "format": "jpeg", "quality": 60, "maxWidth": 1280, "maxHeight": 800,
        })
        while True:
            m = json.loads(await ws.receive_text())
            if m.get("type") == "done":
                break
            await _send_input(cdp, m)
