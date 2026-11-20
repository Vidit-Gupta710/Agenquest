// AgentLighthouse audit UI. Keeps the backend untouched; only the DOM changed.

// Tailwind's `hidden` class isn't used anymore, but the shim is cheap and keeps
// legacy `el.hidden = …` calls working alongside CSS `.hidden`.
Object.defineProperty(HTMLElement.prototype, "hidden", {
  set(v) { this.toggleAttribute("hidden", !!v); this.classList.toggle("hidden", !!v); },
  get() { return this.hasAttribute("hidden") || this.classList.contains("hidden"); },
  configurable: true,
});

const $ = (id) => document.getElementById(id);
const esc = (s) => { const d = document.createElement("div"); d.textContent = s ?? ""; return d.innerHTML; };

// --- SVG icon helpers (inline so CSS 'currentColor' works) ---
const ICONS = {
  check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>',
  x:     '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6L6 18M6 6l12 12"/></svg>',
  steps: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 20V10"/><path d="M12 20V4"/><path d="M6 20v-6"/></svg>',
  clock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
  globe: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>',
  copy:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>',
};

const SIGNAL_LABELS = {
  fetchable: "Fetchable", text_rendered: "Text rendered", llms_txt: "LLMs.txt",
  robots_ok: "Robots OK", sitemap: "Sitemap", meta: "Meta tags",
};
const SIGNAL_HINT = {
  fetchable: "TinyFish Fetch gets the homepage",
  text_rendered: "Homepage HTML has real text, not JS-only shell",
  llms_txt: "/llms.txt exists and non-empty",
  robots_ok: "robots.txt doesn't block AI agents",
  sitemap: "/sitemap.xml exists",
  meta: "title + meta description present",
};

// --- Toasts ---
function toast(msg, cls = "") {
  const t = document.createElement("div");
  t.className = "toast " + cls;
  t.textContent = msg;
  $("toasts").appendChild(t);
  setTimeout(() => t.remove(), 4000);
}

// --- Audit SSE pipeline ---
let auditDone = false;

async function startAudit(url) {
  resetStages();
  $("stages").hidden = false;
  $("stage-indicator").hidden = false;
  $("submit-btn").disabled = true;

  const res = await fetch("/api/audit", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail?.[0]?.msg || err.detail || "Invalid URL");
  }
  const { audit_id } = await res.json();
  const stream = new EventSource(`/api/audit/${audit_id}/events`);
  stream.onmessage = (msg) => {
    const e = JSON.parse(msg.data);
    (render[e.type] || (() => {}))(e);
    if (e.type === "done" || e.type === "error") stream.close();
  };
  stream.onerror = () => { stream.close(); if (!auditDone) toast("Connection to audit stream lost", "err"); };
}

function resetStages() {
  auditDone = false;
  ["stage-signals","stage-tasks","stage-score","stage-diagnose","stage-peers","done-view"].forEach((id) => $(id).hidden = true);
  $("task-cards").innerHTML = "";
  $("diagnoses").innerHTML = "";
  $("peers-list").innerHTML = "";
  $("signals-grid").innerHTML = "";
  $("error-msg").hidden = true;
}

const STAGE_LABELS = {
  signals: "Reading the site",
  classify: "Picking journeys",
  tasks: "Running agents",
  diagnose: "Writing diagnoses",
  score: "Scoring",
  peers: "Finding peers",
};

const render = {
  stage: (e) => {
    $("stage-text").textContent = STAGE_LABELS[e.stage] || e.stage;
  },

  signals: (e) => {
    $("stage-signals").hidden = false;
    const grid = $("signals-grid");
    grid.innerHTML = "";
    let passed = 0, total = 0;
    for (const [k, v] of Object.entries(e.signals)) {
      if (k === "fetch_error") continue;
      total++; if (v) passed++;
      const div = document.createElement("div");
      div.className = `signal ${v ? "ok" : "bad"}`;
      div.innerHTML = `
        <span class="pill">${v ? ICONS.check : ICONS.x}</span>
        <div>
          <div class="label">${SIGNAL_LABELS[k] || k}</div>
          <div style="font-size:11.5px;color:var(--text-muted);margin-top:1px">${SIGNAL_HINT[k] || ""}</div>
        </div>`;
      grid.appendChild(div);
    }
    $("signals-summary").textContent = `${passed} of ${total} passed`;
  },

  tasks: (e) => {
    $("stage-tasks").hidden = false;
    const container = $("task-cards");
    container.innerHTML = "";
    e.tasks.forEach((t) => container.appendChild(taskCard(t)));
  },

  task_update: (e) => {
    const card = $(`task-${e.task_id}`);
    if (!card) return;
    card.dataset.status = e.status;
    card.querySelector(".badge").className = "badge running";
    card.querySelector(".badge").textContent = `${e.status.toLowerCase()} · ${e.steps} steps`;
    if (e.last_action) card.querySelector(".task-trace").textContent = "› " + e.last_action;
    const streamWrap = card.querySelector(".stream-slot");
    if (e.streaming_url && !streamWrap.dataset.loaded) {
      streamWrap.dataset.loaded = "1";
      streamWrap.innerHTML = `
        <details class="task-stream" open>
          <summary>Live agent view</summary>
          <iframe src="${e.streaming_url}" allow="autoplay"></iframe>
        </details>`;
    }
  },

  task_done: (e) => {
    const card = $(`task-${e.task.id}`);
    if (!card) return;
    const t = e.task;
    const outcomeCls = t.outcome === "success" ? "ok" : t.outcome === "partial" ? "partial" : "err";
    card.classList.remove("ok","partial","err"); card.classList.add(outcomeCls);
    const badge = card.querySelector(".badge");
    badge.className = `badge ${outcomeCls}`;
    badge.textContent = t.outcome;

    // voyage track fill
    const ms = t.milestones || [];
    const idx = ms.indexOf(t.furthest_milestone);
    const reached = idx >= 0 ? idx + 1 : 0;
    const pct = ms.length ? Math.round((reached / ms.length) * 100) : 0;
    const voyage = card.querySelector(".voyage");
    voyage.classList.remove("running");
    voyage.querySelector(".voyage-fill").style.width = pct + "%";
    const stops = voyage.querySelectorAll(".stop");
    stops.forEach((s, i) => {
      s.classList.remove("current", "reached");
      if (i < reached) s.classList.add("reached");
    });

    // meta line
    const meta = card.querySelector(".task-meta");
    meta.innerHTML = `
      <span class="m">${ICONS.steps}${t.steps} of ~${t.expected_steps} steps</span>
      ${t.seconds ? `<span class="m">${ICONS.clock}${Math.round(t.seconds)}s</span>` : ""}
      <span class="m">reached <strong>${reached}/${ms.length}</strong> milestones (${pct}%)</span>
      ${t.blocker && t.blocker !== "none" ? `<span class="m" style="color:var(--danger)">blocker: ${t.blocker}</span>` : ""}
    `;
    // close stream once finished
    const stream = card.querySelector(".stream-slot");
    if (stream.dataset.loaded) stream.innerHTML = "";
  },

  diagnosis: (e) => {
    $("stage-diagnose").hidden = false;
    const d = e.diagnosis;
    if ((d.confidence ?? 0) < 0.4) return;  // per design.md: hide low-confidence
    const sev = (d.severity || "low").toLowerCase();
    const div = document.createElement("div");
    div.className = `diag ${sev}`;
    div.innerHTML = `
      <div class="diag-head">
        <span class="diag-ref">${esc(humanJourney(d.task_id))}</span>
        <span class="badge ${sev === "high" ? "err" : sev === "medium" ? "partial" : "ok"}">${sev}</span>
        <span class="badge">${esc(d.blocker || "other")}</span>
        <span class="diag-conf">confidence ${Math.round((d.confidence || 0) * 100)}%</span>
      </div>
      <div class="diag-body">${esc(d.root_cause || "insufficient evidence")}</div>
      ${d.fix ? `
        <div class="fix">
          <div class="fix-head">
            <span>Suggested fix</span>
            <button class="copy-btn" type="button">${ICONS.copy}<span>Copy</span></button>
          </div>
          <pre>${esc(d.fix)}</pre>
        </div>` : ""}`;
    if (d.fix) {
      div.querySelector(".copy-btn").addEventListener("click", async () => {
        try { await navigator.clipboard.writeText(d.fix); toast("Fix copied"); } catch { toast("Copy failed", "err"); }
      });
    }
    $("diagnoses").appendChild(div);
  },

  score: (e) => {
    $("stage-score").hidden = false;
    const s = e.score;
    animate($("score-total"), 0, s.total, 1100);
    $("score-grade").textContent = s.grade;
    animate($("score-success"), 0, s.success, 900);
    animate($("score-efficiency"), 0, s.efficiency, 900);
    animate($("score-readability"), 0, s.readability, 900);
    requestAnimationFrame(() => {
      $("fill-success").style.width     = Math.min(100, (s.success / 65) * 100) + "%";
      $("fill-efficiency").style.width  = Math.min(100, (s.efficiency / 20) * 100) + "%";
      $("fill-readability").style.width = Math.min(100, (s.readability / 15) * 100) + "%";
      const C = 2 * Math.PI * 88;  // circumference
      $("score-ring-fg").setAttribute("stroke-dasharray", C.toFixed(2));
      $("score-ring-fg").setAttribute("stroke-dashoffset", (C * (1 - Math.min(100, s.total) / 100)).toFixed(2));
    });
    const tax = e.agent_tax || {};
    $("agent-tax").textContent = "$" + (tax.usd_per_task ?? 0).toFixed(2);
    $("tax-steps").textContent = tax.avg_steps ?? "—";
  },

  peers: (e) => {
    $("stage-peers").hidden = false;
    const list = $("peers-list");
    list.innerHTML = "";
    if (!e.peers.length) {
      list.innerHTML = `<div class="muted" style="font-size:13px">No comparable peers found.</div>`;
      return;
    }
    e.peers.forEach((p) => {
      const pct = Math.min(100, (p.readability / 15) * 100);
      const div = document.createElement("div");
      div.className = "peer";
      div.innerHTML = `
        <div class="peer-domain">${ICONS.globe}${esc(p.domain)}</div>
        <div class="peer-bar"><div class="peer-fill" style="width:${pct}%"></div></div>
        <div class="peer-score">${p.readability} of 15 readability</div>`;
      list.appendChild(div);
    });
  },

  done: (e) => {
    auditDone = true;
    $("stage-indicator").hidden = true;
    $("done-view").hidden = false;
    $("view-report").hidden = false;
    $("submit-btn").disabled = false;
    $("done-time").textContent = e.report?.audited_at
      ? `Finished ${new Date(e.report.audited_at).toLocaleString()}` : "";
    window.__report = e.report;
  },

  error: (e) => {
    $("stage-indicator").hidden = true;
    $("submit-btn").disabled = false;
    toast(e.message || "Something went wrong", "err");
  },
};

function taskCard(t) {
  const card = document.createElement("div");
  card.id = `task-${t.id}`;
  card.className = "task";
  const ms = t.milestones || [];
  const stops = ms.map((m, i) => `
    <div class="stop${i === 0 ? ' current' : ''}">
      <div class="dot"></div>
      <div class="label" title="${esc(m)}">${esc(m.replace(/_/g, " "))}</div>
    </div>`).join("");
  card.innerHTML = `
    <div class="task-head">
      <div class="task-title">
        <h3>${esc(t.label)}</h3>
        <div class="sub">${esc(t.id)} · ~${t.expected_steps || "?"} step budget</div>
      </div>
      <span class="badge running">pending</span>
    </div>
    <div class="voyage running">
      <div class="voyage-rail"><div class="voyage-fill" style="width:0%"></div></div>
      <div class="voyage-stops">${stops}</div>
    </div>
    <div class="task-meta"><span class="m muted">waiting for the agent to launch…</span></div>
    <div class="task-trace"></div>
    <div class="stream-slot"></div>`;
  return card;
}

function humanJourney(id) {
  return {
    buy_cheapest: "Buy the cheapest match",
    filter_shop:  "Filter like a picky shopper",
    exchange_flow:"Find a size exchange",
    apply_job:    "Apply to a matching job",
    connect_note: "Write a connection request",
    message_draft:"Draft a message",
    book_cheapest:"Book the cheapest trip",
    filter_trip:  "Filter a trip",
    cancel_rules: "Find cancellation rules",
    plan_signup:  "Choose a plan and sign up",
    book_demo:    "Book a demo",
    docs_howto:   "Answer a how-to from the docs",
    book_slot:    "Book the earliest slot",
    get_quote:    "Get a quote",
    compare_offers:"Compare offerings",
  }[id] || id;
}

function animate(el, from, to, ms) {
  const t0 = performance.now();
  function step(now) {
    const p = Math.min(1, (now - t0) / ms);
    const eased = 1 - Math.pow(1 - p, 3);
    el.textContent = Math.round(from + (to - from) * eased);
    if (p < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

// --- Leaderboard modal ---
async function openLeaderboard() {
  const res = await fetch("/api/leaderboard");
  const rows = await res.json();
  const backdrop = document.createElement("div");
  backdrop.className = "modal-backdrop";
  backdrop.innerHTML = `
    <div class="modal-card">
      <div class="modal-head">
        <h2>Leaderboard</h2>
        <button class="btn btn-ghost" id="lb-close">Close</button>
      </div>
      ${rows.length ? `
        <table class="lb-table">
          <thead><tr><th>#</th><th>Domain</th><th>Type</th><th>Score</th><th>Grade</th><th>Agent Tax</th></tr></thead>
          <tbody>
            ${rows.map((r, i) => `
              <tr>
                <td class="muted">${i+1}</td>
                <td>${esc(r.domain)}</td>
                <td class="muted">${esc(r.site_type || "")}</td>
                <td><strong>${r.total}</strong></td>
                <td><span class="grade ${r.grade}">${r.grade}</span></td>
                <td>$${(r.usd_per_task ?? 0).toFixed(2)}</td>
              </tr>`).join("")}
          </tbody>
        </table>` : `<p class="muted">Leaderboard is empty. Run <code>python -m scripts.benchmark</code> to populate it.</p>`}
    </div>`;
  document.body.appendChild(backdrop);
  const close = () => backdrop.remove();
  backdrop.addEventListener("click", (e) => { if (e.target === backdrop) close(); });
  backdrop.querySelector("#lb-close").addEventListener("click", close);
  document.addEventListener("keydown", function k(e) { if (e.key === "Escape") { close(); document.removeEventListener("keydown", k); } });
}

// --- Event wiring ---
$("audit-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try { await startAudit($("url-input").value); }
  catch (err) { $("error-msg").textContent = err.message; $("error-msg").hidden = false; $("submit-btn").disabled = false; }
});
$("sample-shop").addEventListener("click", () => { $("url-input").value = "https://example.com"; $("audit-form").dispatchEvent(new Event("submit")); });
$("sample-saas").addEventListener("click", () => { $("url-input").value = "https://httpbin.org"; $("audit-form").dispatchEvent(new Event("submit")); });
$("new-audit").addEventListener("click", () => { resetStages(); $("stages").hidden = true; $("url-input").value = ""; $("url-input").focus(); });
$("view-report").addEventListener("click", () => {
  const r = window.__report; if (!r) return;
  const blob = new Blob([JSON.stringify(r, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `${r.domain}-report.json`;
  a.click();
  URL.revokeObjectURL(a.href);
});
$("nav-leaderboard").addEventListener("click", openLeaderboard);
