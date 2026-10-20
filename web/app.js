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
  const stream = new EventSource(`/api/audit/${audit_id}/events`);
  stream.onmessage = (msg) => {
    const e = JSON.parse(msg.data);
    (render[e.type] || (() => {}))(e);
    if (e.type === "done" || e.type === "error") stream.close();
  };
  stream.onerror = () => stream.close();
}

const render = {
  stage: (e) => {
    document.getElementById("stages").hidden = false;
    document.getElementById("audit-form").querySelector("button").disabled = true;
  },
  signals: (e) => {
    document.getElementById("stage-signals").hidden = false;
    const grid = document.getElementById("signals-grid");
    grid.innerHTML = "";
    for (const [k, v] of Object.entries(e.signals)) {
      if (k === "fetch_error") continue;
      const div = document.createElement("div");
      div.className = `p-3 rounded-lg ${v ? "bg-green-50 text-green-800" : "bg-red-50 text-red-800"}`;
      div.innerHTML = `<div class="font-medium capitalize">${k.replace("_", " ")}</div><div class="text-2xl">${v ? "✓" : "✗"}</div>`;
      grid.appendChild(div);
    }
  },
  tasks: (e) => {
    document.getElementById("stage-tasks").hidden = false;
    const container = document.getElementById("task-cards");
    container.innerHTML = "";
    e.tasks.forEach((t) => {
      const div = document.createElement("div");
      div.id = `task-${t.id}`;
      div.className = "p-3 border rounded-lg bg-gray-50";
      div.innerHTML = `<div class="font-medium">${t.label}</div><div class="text-sm text-gray-600">Pending...</div>`;
      container.appendChild(div);
    }
  },
  task_update: (e) => {
    const card = document.getElementById(`task-${e.task_id}`);
    if (card) {
      card.querySelector("div:last-child").textContent =
        e.status === "RUNNING" ? `Running... ${e.steps} steps` : e.status;
    }
  },
  task_done: (e) => {
    const card = document.getElementById(`task-${e.task.id}`);
    if (card) {
      const color = e.task.outcome === "success" ? "green" : e.task.outcome === "partial" ? "yellow" : "red";
      card.className = `p-3 border rounded-lg bg-${color}-50`;
      card.innerHTML = `<div class="font-medium">${e.task.label}</div><div class="text-sm">Outcome: ${e.task.outcome} | Steps: ${e.task.steps} | Blocker: ${e.task.blocker}</div>`;
    }
  },
  diagnosis: (e) => {
    document.getElementById("stage-diagnose").hidden = false;
    const div = document.createElement("div");
    div.className = "p-3 border rounded-lg bg-orange-50";
    div.innerHTML = `<div class="font-medium">${e.diagnosis.task_id}: ${e.diagnosis.blocker}</div><div class="text-sm mt-1">${e.diagnosis.root_cause}</div><div class="text-sm mt-1"><strong>Fix:</strong> ${e.diagnosis.fix}</div>`;
    document.getElementById("diagnoses").appendChild(div);
  },
  score: (e) => {
    document.getElementById("stage-score").hidden = false;
    document.getElementById("score-total").textContent = e.score.total;
    document.getElementById("score-grade").textContent = e.score.grade;
    document.getElementById("agent-tax").textContent = `$${e.agent_tax.usd_per_task}`;
  },
  peers: (e) => {
    document.getElementById("stage-peers").hidden = false;
    const container = document.getElementById("peers-list");
    container.innerHTML = "";
    e.peers.forEach((p) => {
      const div = document.createElement("div");
      div.className = "p-3 border rounded-lg";
      div.innerHTML = `<div class="font-medium">${p.domain}</div><div class="text-sm">Readability: ${p.readability}/25</div>`;
      container.appendChild(div);
    }
  },
  done: (e) => {
    document.getElementById("done-view").hidden = false;
    document.getElementById("audit-form").querySelector("button").disabled = false;
  },
  error: (e) => {
    document.getElementById("error-msg").textContent = e.message;
    document.getElementById("error-msg").hidden = false;
    document.getElementById("audit-form").querySelector("button").disabled = false;
  },
};

document.getElementById("audit-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  document.getElementById("error-msg").hidden = true;
  document.querySelectorAll("#stages > div").forEach((d) => (d.hidden = true));
  document.getElementById("done-view").hidden = true;
  try {
    await startAudit(document.getElementById("url-input").value);
  } catch (err) {
    document.getElementById("error-msg").textContent = err.message;
    document.getElementById("error-msg").hidden = false;
    document.getElementById("audit-form").querySelector("button").disabled = false;
  }
});

document.getElementById("new-audit").addEventListener("click", () => {
  document.getElementById("stages").hidden = true;
  document.getElementById("done-view").hidden = true;
  document.querySelectorAll("#stages > div").forEach((d) => (d.hidden = true));
  document.getElementById("audit-form").querySelector("button").disabled = false;
});