// AgentLighthouse UI - SSE client + rendering
let currentAuditId = null;
let currentUrl = null;
let currentReport = null;

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

async function startAudit(url) {
  const res = await fetch("/api/audit", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Invalid URL");
  }
  const { audit_id } = await res.json();
  currentAuditId = audit_id;
  currentUrl = url;
  const stream = new EventSource(`/api/audit/${audit_id}/events`);
  console.log("SSE connected to", `/api/audit/${audit_id}/events`);
  stream.onmessage = (msg) => {
    console.log("SSE message:", msg.data);
    const e = JSON.parse(msg.data);
    console.log("Event type:", e.type, e);
    (render[e.type] || (() => {}))(e);
    if (e.type === "done" || e.type === "error") stream.close();
  };
  stream.onerror = (err) => {
    console.error("SSE error:", err);
    stream.close();
  };
  stream.onopen = () => console.log("SSE open");
}

const signalLabels = {
  fetchable: "Fetchable",
  text_rendered: "Text Rendered",
  llms_txt: "LLMs.txt",
  robots_ok: "Robots OK",
  sitemap: "Sitemap",
  meta: "Meta Tags",
};

const render = {
  stage: (e) => {
    console.log("Render stage:", e.stage);
    document.getElementById("stages").hidden = false;
    document.getElementById("submit-btn").disabled = true;
  },
  signals: (e) => {
    console.log("Render signals:", e.signals);
    document.getElementById("stage-signals").hidden = false;
    const grid = document.getElementById("signals-grid");
    grid.innerHTML = "";
    let passed = 0;
    for (const [k, v] of Object.entries(e.signals)) {
      if (k === "fetch_error") continue;
      if (v) passed++;
      const div = document.createElement("div");
      div.className = `p-3 rounded-lg ${v ? "bg-green-50 text-green-800 border border-green-200" : "bg-red-50 text-red-800 border border-red-200"}`;
      div.innerHTML = `<div class="font-medium capitalize text-sm">${signalLabels[k] || k.replace("_", " ")}</div><div class="text-3xl font-bold mt-1">${v ? "Yes" : "No"}</div>`;
      grid.appendChild(div);
    }
    const total = Object.keys(e.signals).filter(k => k !== "fetch_error").length;
    document.getElementById("signals-summary").textContent = `${passed}/${total} passed`;
  },
  tasks: (e) => {
    console.log("Render tasks:", e.tasks);
    document.getElementById("stage-tasks").hidden = false;
    const container = document.getElementById("task-cards");
    container.innerHTML = "";
    e.tasks.forEach((t) => {
      const div = document.createElement("div");
      div.id = `task-${t.id}`;
      div.className = "task-card p-3 border rounded-lg bg-gray-50";
      div.innerHTML = `<div class="font-medium">${t.label}</div><div class="text-sm text-gray-600">Pending...</div>`;
      container.appendChild(div);
    });
  },
  task_update: (e) => {
    console.log("Render task_update:", e.task_id, e.status, e.steps);
    const card = document.getElementById(`task-${e.task_id}`);
    if (card) {
      let statusText = e.status === "RUNNING" ? `Running... ${e.steps} steps` : e.status;
      if (e.streaming_url && e.status === "RUNNING") {
        statusText += ` <a href="${e.streaming_url}" target="_blank" class="text-blue-600 hover:underline text-xs">Live view</a>`;
      }
      card.querySelector("div:last-child").innerHTML = statusText;
    }
  },
  task_done: (e) => {
    console.log("Render task_done:", e.task);
    const card = document.getElementById(`task-${e.task.id}`);
    if (card) {
      const color = e.task.outcome === "success" ? "green" : e.task.outcome === "partial" ? "yellow" : "red";
      card.className = `task-card p-3 border rounded-lg bg-${color}-50 border-${color}-200`;
      card.innerHTML = `
        <div class="font-medium">${e.task.label}</div>
        <div class="text-sm mt-1">
          <span class="font-medium capitalize">${e.task.outcome}</span> -
          ${e.task.steps} steps (expected ${e.task.expected_steps}) -
          Blocker: ${e.task.blocker}
        </div>
        ${e.task.answer ? `<div class="text-xs text-gray-600 mt-1">${e.task.answer.substring(0, 120)}${e.task.answer.length > 120 ? "..." : ""}</div>` : ""}
      `;
    }
  },
  diagnosis: (e) => {
    console.log("Render diagnosis:", e.diagnosis);
    document.getElementById("stage-diagnose").hidden = false;
    const div = document.createElement("div");
    div.className = `diagnosis-card p-4 border rounded-lg bg-white border-l-4 diagnosis-severity-${e.diagnosis.severity || "low"}`;
    const fixHtml = e.diagnosis.fix
      ? `<div class="mt-2"><strong>Fix:</strong><pre class="bg-gray-100 p-2 rounded text-xs mt-1 overflow-x-auto whitespace-pre-wrap">${escapeHtml(e.diagnosis.fix)}</pre></div>`
      : "";
    div.innerHTML = `
      <div class="flex items-start justify-between">
        <div>
          <div class="font-medium">${e.diagnosis.task_id}: <span class="text-gray-600">${e.diagnosis.blocker}</span></div>
          <div class="text-sm text-gray-600 mt-1">${e.diagnosis.root_cause}</div>
          ${fixHtml}
        </div>
        <div class="text-right text-xs text-gray-500">
          <div>Severity: ${e.diagnosis.severity || "low"}</div>
          <div>Confidence: ${Math.round((e.diagnosis.confidence || 0) * 100)}%</div>
        </div>
      </div>
    `;
    document.getElementById("diagnoses").appendChild(div);
  },
  score: (e) => {
    console.log("Render score:", e.score);
    document.getElementById("stage-score").hidden = false;
    animateCount("score-total", e.score.total);
    animateCount("score-success", e.score.success);
    animateCount("score-efficiency", e.score.efficiency);
    animateCount("score-readability", e.score.readability);
    document.getElementById("score-grade").textContent = e.score.grade;
    document.getElementById("agent-tax").textContent = `$${e.agent_tax.usd_per_task}`;
  },
  peers: (e) => {
    console.log("Render peers:", e.peers);
    document.getElementById("stage-peers").hidden = false;
    const container = document.getElementById("peers-list");
    container.innerHTML = "";
    e.peers.forEach((p) => {
      const div = document.createElement("div");
      div.className = "p-3 border rounded-lg bg-gray-50";
      div.innerHTML = `<div class="font-medium">${p.domain}</div><div class="text-sm text-gray-600">Readability: ${p.readability}/25</div>`;
      container.appendChild(div);
    });
  },
  done: (e) => {
    console.log("Render done:", e.report);
    currentReport = e.report;
    document.getElementById("done-view").hidden = false;
    document.getElementById("view-report").hidden = false;
    document.getElementById("view-leaderboard").hidden = false;
    document.getElementById("submit-btn").disabled = false;
  },
  error: (e) => {
    console.error("Render error:", e.message);
    document.getElementById("error-msg").textContent = e.message || "Something went wrong";
    document.getElementById("error-msg").hidden = false;
    document.getElementById("submit-btn").disabled = false;
  },
};

function animateCount(id, target) {
  const el = document.getElementById(id);
  if (!el) return;
  const start = 0;
  const duration = 1200;
  const startTime = performance.now();
  function step(now) {
    const progress = Math.min((now - startTime) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.round(start + (target - start) * eased);
    if (progress < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

function loadLeaderboard() {
  fetch("/api/leaderboard")
    .then(r => r.json())
    .then(data => {
      const tbody = document.getElementById("leaderboard-body");
      tbody.innerHTML = "";
      data.forEach((row, i) => {
        const tr = document.createElement("tr");
        tr.className = "border-b hover:bg-gray-50";
        tr.innerHTML = `
          <td class="py-2 font-medium">${i + 1}</td>
          <td class="py-2">${row.domain}</td>
          <td class="py-2">${row.site_type}</td>
          <td class="py-2 font-medium">${row.total}</td>
          <td class="py-2"><span class="px-2 py-0.5 rounded text-xs font-medium ${gradeColor(row.grade)}">${row.grade}</span></td>
          <td class="py-2">$${row.usd_per_task}</td>
        `;
        tbody.appendChild(tr);
      });
    });
}

function gradeColor(g) {
  const colors = { A: "bg-green-100 text-green-800", B: "bg-blue-100 text-blue-800", C: "bg-yellow-100 text-yellow-800", D: "bg-orange-100 text-orange-800", F: "bg-red-100 text-red-800" };
  return colors[g] || "bg-gray-100 text-gray-800";
}

document.getElementById("audit-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  document.getElementById("error-msg").hidden = true;
  document.querySelectorAll("#stages > div").forEach((d) => (d.hidden = true));
  document.getElementById("done-view").hidden = true;
  document.getElementById("leaderboard-view").hidden = true;
  document.getElementById("view-report").hidden = true;
  document.getElementById("view-leaderboard").hidden = true;
  try {
    await startAudit(document.getElementById("url-input").value);
  } catch (err) {
    document.getElementById("error-msg").textContent = err.message;
    document.getElementById("error-msg").hidden = false;
    document.getElementById("submit-btn").disabled = false;
  }
});

document.getElementById("new-audit").addEventListener("click", () => {
  document.getElementById("stages").hidden = true;
  document.getElementById("done-view").hidden = true;
  document.getElementById("leaderboard-view").hidden = true;
  document.querySelectorAll("#stages > div").forEach((d) => (d.hidden = true));
  document.getElementById("view-report").hidden = true;
  document.getElementById("view-leaderboard").hidden = true;
  document.getElementById("submit-btn").disabled = false;
  document.getElementById("url-input").value = "";
});

document.getElementById("sample-shop").addEventListener("click", () => {
  document.getElementById("url-input").value = "https://example.com";
  document.getElementById("audit-form").dispatchEvent(new Event("submit"));
});

document.getElementById("sample-saas").addEventListener("click", () => {
  document.getElementById("url-input").value = "https://httpbin.org";
  document.getElementById("audit-form").dispatchEvent(new Event("submit"));
});

document.getElementById("view-leaderboard").addEventListener("click", () => {
  document.getElementById("stages").hidden = true;
  document.getElementById("done-view").hidden = true;
  document.getElementById("leaderboard-view").hidden = false;
  loadLeaderboard();
});

document.getElementById("back-from-leaderboard").addEventListener("click", () => {
  document.getElementById("leaderboard-view").hidden = true;
  document.getElementById("done-view").hidden = false;
  document.getElementById("stages").hidden = false;
});

document.getElementById("view-report").addEventListener("click", () => {
  if (currentReport) {
    const blob = new Blob([JSON.stringify(currentReport, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${currentReport.domain}-report.json`;
    a.click();
    URL.revokeObjectURL(url);
  }
});

// Load leaderboard on page load for demo
window.addEventListener("load", () => {
  // Optional: preload leaderboard
});