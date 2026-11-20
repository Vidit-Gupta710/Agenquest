"""Journey library: deep, multi-step jobs an AI agent should finish on each kind of site."""
from app import llm

BLOCKERS = [
    "none", "cookie_or_popup", "captcha_or_bot_block", "login_wall",
    "element_not_found", "unlabeled_control", "slow_or_dynamic_content",
    "confusing_navigation", "no_matching_item", "other",
]

STOP = (
    "Never pay, place an order, create an account, or press a final Send, Submit, Apply, "
    "Book or Confirm button. Stop at the first page that asks for payment details or a final "
    "confirmation, with that button visible. If a form needs details, type only fake test data: "
    "name 'Test Agent', email test@example.com, phone 9999999999. Close cookie banners and "
    "popups and continue."
)
PUBLIC = "Do not sign in. If the site asks you to sign in, stop on that page and report it."
SIGNED_IN = (
    "You are already signed in to the user's own account. Never change settings, address "
    "or payment methods, and never remove or change items already in the cart."
)


def j(label, steps, ms, ask, public_until=None, signed_in_only=False):
    return {
        "label": label, "steps": steps, "milestones": ms.split(), "ask": ask,
        "public_until": public_until, "signed_in_only": signed_in_only,
    }


JOURNEYS = {
    "buy_cheapest": j("Buy the cheapest match", 30,
        "searched sorted_by_price product_opened variant_selected added_to_cart coupon_applied checkout_reached",
        "Search for '{query}'. Sort or filter so the lowest price shows first. Open the cheapest "
        "in-stock item that really matches. Pick a size or variant if asked. Add it to the cart and "
        "open the cart. Find coupons or offers on the product, cart or offers page, try them, and "
        "keep the one that saves the most. Then go to checkout and stop at the payment or sign-in page."),
    "filter_shop": j("Filter like a picky shopper", 18,
        "searched brand_filtered size_filtered rating_filtered top3_listed",
        "Search for '{query}'. Use the site's filters for one popular brand, one common size and a "
        "rating of 4 stars or more. Report the top 3 results with prices."),
    "exchange_flow": j("Find a size exchange", 14,
        "help_opened returns_found exchange_rules_read request_page_reached",
        "Find how to exchange a product for a different size: open help, find the returns or "
        "exchange policy, read the rules and reach the page where an exchange is requested.",
        public_until="request_page_reached"),
    "apply_job": j("Apply to a matching job", 30,
        "searched filtered job_opened apply_started form_filled ready_to_submit",
        "Search jobs for '{query}'. Filter by location and experience level. Open the best match, "
        "start the application and fill every field, then stop with the Submit button visible.",
        public_until="apply_started"),
    "connect_note": j("Write a connection request", 20,
        "people_searched profile_opened connect_clicked note_written ready_to_send",
        "Search people for '{query}', open the most relevant profile, click Connect, add a short "
        "polite note, then stop with the Send button visible.", signed_in_only=True),
    "message_draft": j("Draft a message", 16,
        "messages_opened recipient_chosen message_written ready_to_send",
        "Open messages, choose an existing connection related to '{query}', write a short friendly "
        "message, then stop with the Send button visible.", signed_in_only=True),
    "book_cheapest": j("Book the cheapest trip", 35,
        "route_entered dates_set sorted_by_price cheapest_selected fare_chosen offer_applied details_reached",
        "Search for '{query}' on dates two weeks from today. Sort by price, pick the cheapest option, "
        "choose the basic fare, apply the best offer code you can find, and stop at traveller details."),
    "filter_trip": j("Filter a trip", 22,
        "searched nonstop_filtered time_filtered budget_filtered top3_listed",
        "Search for '{query}'. Filter to non-stop, morning departures and a sensible budget. "
        "Report the top 3 options with prices."),
    "cancel_rules": j("Find the cancellation rules", 14, "fare_opened rules_found refund_reported",
        "Search for '{query}', open any fare and report its cancellation rules and refund amount."),
    "plan_signup": j("Choose a plan and sign up", 20,
        "pricing_opened monthly_selected plan_chosen signup_started form_filled ready_to_create",
        "Open pricing, switch to monthly billing, choose the cheapest paid plan, start sign-up, fill "
        "the form with test data and stop with the create-account button visible."),
    "book_demo": j("Book a demo", 14, "demo_page_found form_filled ready_to_submit",
        "Find where to book a demo or contact sales, fill the form with test data and stop with the "
        "submit button visible."),
    "docs_howto": j("Answer a how-to from the docs", 14, "docs_opened docs_searched guide_found steps_reported",
        "Use the documentation to find how to '{query}' and report the steps in short."),
    "book_slot": j("Book the earliest slot", 22,
        "service_chosen location_chosen slot_chosen details_filled ready_to_confirm",
        "Book '{query}': choose the service and the nearest location, pick the earliest slot, fill "
        "test details and stop with the confirm button visible."),
    "get_quote": j("Get a quote", 12, "quote_page_found form_filled ready_to_submit",
        "Find where to request a quote for '{query}', fill the form with test data and stop with "
        "the submit button visible."),
    "compare_offers": j("Compare offerings", 12, "list_found prices_found best_value_reported",
        "List what this business offers, find prices, and report the best value option for '{query}'."),
}

SITE_JOURNEYS = {
    "ecommerce": ["filter_shop", "exchange_flow"],
    "social":    ["apply_job", "connect_note", "message_draft"],
    "travel":    ["filter_trip", "cancel_rules"],
    "saas":      ["plan_signup", "book_demo", "docs_howto"],
    "services":  ["book_slot", "get_quote", "compare_offers"],
}


def schema(jid):
    text = {"type": "string", "nullable": True}
    return {"type": "object", "required": ["outcome", "furthest_milestone", "blocker"], "properties": {
        "outcome": {"type": "string", "enum": ["success", "partial", "failure"]},
        "furthest_milestone": {"type": "string", "enum": ["none", *JOURNEYS[jid]["milestones"]]},
        "blocker": {"type": "string", "enum": BLOCKERS}, "blocker_detail": text,
        "item_name": text, "item_price": text, "coupon_code": text, "discount": text,
        "total": text, "answer": text, "final_url": text}}


def goal(jid, query, signed_in=False):
    jr = JOURNEYS[jid]
    return (
        "You are testing whether an AI agent can complete a real customer journey on this "
        f"website. Journey: {jr['ask'].format(query=query)} {STOP} "
        f"{SIGNED_IN if signed_in else PUBLIC} Milestones in order: "
        f"{', '.join(jr['milestones'])}. Set furthest_milestone to the last one you truly "
        "completed. Set outcome to 'success' if you reached every milestone you were allowed "
        "to reach, 'partial' if some, otherwise 'failure'. Set blocker to the single main "
        "obstacle, or 'none', and explain it in blocker_detail. Fill item_name, item_price, "
        "coupon_code, discount and total when they apply."
    )


def scoreable(jid, signed_in):
    ms, cut = JOURNEYS[jid]["milestones"], JOURNEYS[jid]["public_until"]
    return ms if signed_in or not cut else ms[: ms.index(cut) + 1]


def progress(t):
    """Share of reachable milestones completed: 0.0 to 1.0."""
    ms = scoreable(t["id"], t.get("signed_in", False))
    full = JOURNEYS[t["id"]]["milestones"]
    f = t.get("furthest_milestone")
    if f not in full:
        return 0.0
    return min(1.0, (full.index(f) + 1) / len(ms))


CLASSIFY = (
    "You classify websites for an AI-agent usability audit. Reply in JSON with: "
    "site_type (one of ecommerce, social, travel, saas, services; social = jobs or networking); "
    "query (a short, realistic search a customer would type on THIS site); "
    "peer_query (a web search that finds this site's direct competitors in the same country); "
    "summary (one sentence)."
)


async def plan(url, homepage_md):
    p = await llm.ask_json(CLASSIFY, f"URL: {url}\n\nHomepage:\n{homepage_md}")
    if p.get("site_type") not in SITE_JOURNEYS:
        p["site_type"] = "services"
    public = [x for x in SITE_JOURNEYS[p["site_type"]] if not JOURNEYS[x]["signed_in_only"]]
    return {**p, "task_ids": public}
