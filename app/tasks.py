"""Task library: which jobs an AI agent should try on each kind of site."""

BLOCKERS = [
    "none",
    "cookie_or_popup",
    "captcha_or_bot_block",
    "login_wall",
    "element_not_found",
    "unlabeled_control",
    "slow_or_dynamic_content",
    "confusing_navigation",
    "other",
]
SCHEMA = {
    "type": "object",
    "properties": {
        "outcome": {"type": "string", "enum": ["success", "partial", "failure"]},
        "answer": {"type": "string", "nullable": True},
        "blocker": {"type": "string", "enum": BLOCKERS},
        "blocker_detail": {"type": "string", "nullable": True},
        "final_url": {"type": "string", "nullable": True},
    },
    "required": ["outcome", "blocker"],
}

SAFETY = (
    "Browse anonymously. Never log in, create an account, enter personal or "
    "payment details, or submit any form. If a cookie banner or popup appears, "
    "try to close it and continue."
)
REPORT = (
    "Set outcome to 'success' if you {done}, 'partial' if you got close but could "
    "not finish, otherwise 'failure'. Set blocker to the single main obstacle you "
    "hit, or 'none', and describe it in blocker_detail. Put what you found in answer."
)

TASKS = {
    "find_contact": {
        "label": "Find support contact",
        "steps": 6,
        "done": "found a contact method",
        "ask": "Find how to contact customer support: an email, phone number or contact page.",
    },
    "find_policy": {
        "label": "Find refund policy",
        "steps": 6,
        "done": "found the policy and its time window",
        "ask": "Find the return, refund or cancellation policy and state the time window it allows.",
    },
    "find_price": {
        "label": "Find a product price",
        "steps": 8,
        "done": "found a product name and price",
        "ask": "Use the site's search or menus to find a product matching '{query}' and report its name and price.",
    },
    "reach_checkout": {
        "label": "Reach checkout",
        "steps": 14,
        "done": "reached checkout or sign-in-to-checkout",
        "ask": "Add any in-stock product to the cart and go to checkout. Stop as soon as the checkout or sign-in-to-checkout page is visible.",
    },
    "find_pricing": {
        "label": "Find plan pricing",
        "steps": 6,
        "done": "listed plan names and prices",
        "ask": "Find the pricing page and list each plan name with its monthly price.",
    },
    "reach_signup": {
        "label": "Reach sign-up",
        "steps": 6,
        "done": "reached the sign-up form",
        "ask": "Find the sign-up or free-trial page. Stop when the sign-up form is visible.",
    },
    "search_options": {
        "label": "Search options",
        "steps": 15,
        "done": "reported the cheapest option and price",
        "ask": "Search for '{query}' and report the cheapest option shown with its price.",
    },
    "list_services": {
        "label": "List offerings",
        "steps": 5,
        "done": "listed three offerings",
        "ask": "Find what this business offers and list three of its products or services.",
    },
    "reach_enquiry": {
        "label": "Reach enquiry form",
        "steps": 8,
        "done": "reached the enquiry or booking form",
        "ask": "Find the page to book, enquire or request a quote. Stop when the form is visible.",
    },
}

SITE_TASKS = {
    "ecommerce": ["find_contact", "find_policy", "find_price", "reach_checkout"],
    "saas": ["find_contact", "find_policy", "find_pricing", "reach_signup"],
    "travel": ["find_contact", "find_policy", "search_options", "list_services"],
    "services": ["find_contact", "find_policy", "list_services", "reach_enquiry"],
}


def goal(task_id, query):
    t = TASKS[task_id]
    return (
        "You are testing whether an AI agent can use this website. "
        f"Task: {t['ask'].format(query=query)} {SAFETY} {REPORT.format(done=t['done'])}"
    )


CLASSIFY = (
    "You classify websites for an AI-agent usability audit. Reply in JSON with: "
    "site_type (one of ecommerce, saas, travel, services); query (a short, realistic "
    "search a customer would type on THIS site); peer_query (a web search that finds "
    "this site's direct competitors in the same country); summary (one sentence)."
)


async def plan(url, homepage_md):
    from app import llm

    p = await llm.ask_json(CLASSIFY, f"URL: {url}\n\nHomepage:\n{homepage_md}")
    if p.get("site_type") not in SITE_TASKS:
        p["site_type"] = "services"
    return {**p, "task_ids": SITE_TASKS[p["site_type"]]}
