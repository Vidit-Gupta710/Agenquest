"""Signed-in runs: fill the user's cart or prepare an action, always stopping before the final click."""
import json
import pathlib
import time

from app import runner, tasks, tinyfish

LOG = pathlib.Path("data/activity.jsonl")

CART = (
    "You are working inside the user's own signed-in account on {site}. Request: {request} "
    "\n\nREQUIRED STEPS, in this order: "
    "(1) Search or browse for each requested item. "
    "(2) Open the best matching in-stock product that meets every condition, preferring the "
    "lowest price. (3) Pick size/variant if the product asks for one. "
    "(4) CLICK THE 'Add to cart' (or 'Add to bag') BUTTON. This is a required action, not "
    "optional. Adding to the cart does NOT buy anything; it only puts the item in the basket. "
    "(5) Verify by opening the cart page and confirming the item is listed there. "
    "(6) On the cart or offers page, find coupons / promo codes, try the most promising one, "
    "and keep it if the total drops. "
    "(7) STOP on the cart page. Report cart_url and cart_total from what you see there. "
    "\n\nHARD STOPS: never click 'Proceed to checkout', 'Buy now', 'Place order', 'Pay', "
    "'Confirm order' or any final confirmation button. Never change the saved address or "
    "payment method. Never remove or change items already in the cart from before. "
    "If sign-in is required, stop on the sign-in page and set blocker=login_wall — do NOT "
    "attempt to sign in. If no matching item exists, skip it and explain in blocker_detail."
)

TEXT = {"type": "string", "nullable": True}
ITEM = {"type": "object", "properties": {
    "name": {"type": "string"},
    "price": {"type": "string"},
    "why": {"type": "string"},
}}
SCHEMA = {"type": "object", "required": ["outcome", "blocker"], "properties": {
    "outcome": {"type": "string", "enum": ["success", "partial", "failure"]},
    "blocker": {"type": "string", "enum": tasks.BLOCKERS}, "blocker_detail": TEXT,
    "items_added": {"type": "array", "items": ITEM}, "coupon_code": TEXT,
    "discount": TEXT, "cart_total": TEXT, "cart_url": TEXT,
}}


async def _cart(site, request, pid, emit):
    async def on_update(run):
        steps = run.get("steps") or []
        await emit(
            "task_update", task_id="cart", status=run["status"], steps=len(steps),
            streaming_url=run.get("streaming_url"),
            last_action=(steps[-1].get("action") if steps else None),
        )

    run = await tinyfish.run_agent(
        f"https://{site}", CART.format(site=site, request=request),
        SCHEMA, on_update=on_update, profile_id=pid,
    )
    return {
        "id": "cart", **tinyfish.parse_result(run),
        "steps": run.get("num_of_steps"), "run_id": run.get("run_id"),
    }


async def run(site, request, action, pid, emit):
    if action == "cart":
        res = await _cart(site, request, pid, emit)
    else:  # apply_job, connect_note, message_draft: signed-in journeys that stop before Send
        res = await runner.run_task(f"https://{site}", action, request, emit, profile_id=pid)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(json.dumps({
            "at": int(time.time()), "site": site, "action": action,
            "request": request, "result": res,
        }) + "\n")
    await emit("account_done", result=res)
