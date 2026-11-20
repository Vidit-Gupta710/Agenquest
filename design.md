# AgentLighthouse: design.md
## 1. Product
AgentLighthouse audits how well AI web agents can use a website. Input: one URL.
Output: a report with an Agent-Readiness Score (0-100), grade, Agent Tax,
per-task results, AI diagnoses with fixes, and a comparison with 2-3 competitors.

## 2. Users
- Primary: D2C / e-commerce owners and their dev agencies.
- Secondary: SaaS growth teams, SEO/GEO agencies, platform teams.

## 3. Scope
IN: single-URL audit, 4 tasks per site, live agent view, diagnosis, score,
peer comparison (signals only), leaderboard of benchmarked sites, DEMO_MODE.
OUT (roadmap only): logins, scheduled monitoring, PDF export, user accounts,
auto-generated pull requests, non-English sites.

## 4. Pipeline (app/audit.py)
1. signals   : TinyFish Fetch on /, /robots.txt, /llms.txt, /sitemap.xml
2. classify  : LLM on homepage markdown -> site_type, product query, peer query
3. run tasks : TinyFish Agent, 4 tasks, max 2 concurrent, 150 s cap each
4. diagnose  : LLM on each non-success task's step trace
5. score     : pure Python (section 7)
6. peers     : TinyFish Search(peer query) -> 3 other domains -> signals only

Every TinyFish and LLM call goes through app/cache.py.

## 5. Site types and task library (app/tasks.py)
site_type in [ecommerce, saas, travel, services]
| type      | task ids                                   |
| ecommerce | find_contact, find_policy, find_price, reach_checkout |
| saas      | find_contact, find_policy, find_pricing, reach_signup |
| travel    | find_contact, find_policy, search_options, list_services |
| services  | find_contact, find_policy, list_services, reach_enquiry |

Each task = {id, label, goal_template, expected_steps}.
Goals follow the 6 goal-writing rules. No login, no personal data,
no payment, no form submission, ever.

## 6. Blocker taxonomy
none, cookie_or_popup, captcha_or_bot_block, login_wall, element_not_found,
unlabeled_control, slow_or_dynamic_content, confusing_navigation, other

## 7. Scoring (app/score.py)
outcome value: success 1.0, partial 0.5, failure 0.0
success     = 55 * mean(outcome value)
efficiency  = 20 * mean(min(1, expected_steps / steps) * outcome value)
readability = fetchable 6 + text_rendered 5 + llms_txt 4 + robots_ok 4
              + sitemap 3 + meta 3                       (max 25)
total = round(success + efficiency + readability)
grade: A >= 85, B >= 70, C >= 55, D >= 40, else F
agent_tax.avg_steps = mean(steps over all tasks)
agent_tax.usd_per_task = avg_steps * 0.016

## 8. Signals (app/signals.py)
fetchable     : homepage not in Fetch errors as bot_blocked / login_required / http error
text_rendered : homepage text length > 500 characters
llms_txt      : /llms.txt fetched and non-empty, final_url still ends in llms.txt
robots_ok     : robots.txt exists and does not block all agents or named AI agents
sitemap       : /sitemap.xml fetched
meta          : homepage title and description both present

## 9. API (app/main.py)
POST /api/audit            {url}            -> {audit_id}
GET  /api/audit/{id}/events  SSE stream of events (section 10)
GET  /api/report/{domain}                    -> report JSON
GET  /api/leaderboard                        -> [{domain, total, grade, usd_per_task}]
GET  /                                       -> web/index.html

## 10. Events (SSE, one JSON object per message)
stage        {stage: signals|classify|tasks|diagnose|score|peers}
signals      {signals}
tasks        {tasks: [{id, label}]}
task_update  {task_id, status, steps, streaming_url}
task_done    {task: TaskResult}
diagnosis    {diagnosis}
score        {score, agent_tax}
peers        {peers}
done         {report}
error        {message, recoverable}

## 11. Non-functional
- Full audit under 4 minutes. Cached audit under 3 seconds.
- One failed task never fails the audit.
- DEMO_MODE=1 runs with no keys and no network from data/cache.
- No secrets in git. .env in .gitignore.

## 12. Safety and ethics
Agents only read public pages and never log in, submit, pay or enter personal
data. Each audit makes at most 4 agent runs per site. Benchmark results are
presented as a snapshot, with the date, not as a judgement of the company.
