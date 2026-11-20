// My Account UI. Backend untouched; DOM rewritten.

Object.defineProperty(HTMLElement.prototype, "hidden", {
  set(v) { this.toggleAttribute("hidden", !!v); this.classList.toggle("hidden", !!v); },
  get() { return this.hasAttribute("hidden") || this.classList.contains("hidden"); },
  configurable: true,
});

const $ = (id) => document.getElementById(id);
const esc = (s) => { const d = document.createElement("div"); d.textContent = s ?? ""; return d.innerHTML; };

let ws = null;
let sessionId = null;
let canvas, ctx, W = 1280, H = 800;
let expiresTimer = null;

function toast(msg, cls = "") {
  const t = document.createElement("div");
  t.className = "toast " + cls;
  t.textContent = msg;
  $("toasts").appendChild(t);
  setTimeout(() => t.remove(), 4000);
}

const DONE_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>';
function setStep(n) {
  [1, 2, 3].forEach((i) => {
    const el = $(`step-${i}`);
    const num = el.querySelector(".step-num");
    el.classList.remove("active", "done");
    if (i < n) { el.classList.add("done"); num.innerHTML = DONE_SVG; }
    else if (i === n) { el.classList.add("active"); num.textContent = String(i); }
    else { num.textContent = String(i); }
  });
}

async function loadAccounts() {
  const r = await fetch("/api/accounts");
  const sites = await r.json();
  const names = Object.keys(sites);
  const list = $("accounts-list");
  list.innerHTML = "";
  if (!names.length) {
    list.innerHTML = `
      <div class="empty-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
        <strong>No accounts connected yet</strong>
        <div class="hint">Open the TinyFish setup browser in step 2 and sign in to your first site.</div>
      </div>`;
    $("disconnect-all").hidden = true;
    setStep(2);
    return;
  }
  names.forEach((s) => {
    const letter = s.replace(/^www\./, "").charAt(0);
    const row = document.createElement("div");
    row.className = "account-row";
    row.innerHTML = `
      <div class="site-icon">${esc(letter)}</div>
      <div>
        <span class="site-name">${esc(s)}</span>
        <span class="site-status">connected</span>
      </div>
      <span class="saved-at">saved ${new Date(sites[s].saved_at * 1000).toLocaleString()}</span>`;
    list.appendChild(row);
  });
  $("disconnect-all").hidden = false;
  if (!$("run-site").value) $("run-site").value = names[0];
  setStep(3);
}

$("disconnect-all").addEventListener("click", async () => {
  if (!confirm("Delete the TinyFish profile and disconnect every saved account?")) return;
  const r = await fetch("/api/accounts", { method: "DELETE" });
  if (r.ok) { toast("All accounts disconnected"); loadAccounts(); }
  else toast("Could not disconnect", "err");
});

$("connect-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("connect-err").hidden = true;
  $("connect-btn").disabled = true;
  try {
    const r = await fetch("/api/accounts/connect", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ login_url: $("login-url").value }),
    });
    if (!r.ok) throw new Error((await r.json()).detail || "connect failed");
    const { session_id, expires_at } = await r.json();
    sessionId = session_id;
    openLoginWindow(session_id, expires_at);
  } catch (err) {
    $("connect-err").textContent = err.message;
    $("connect-err").hidden = false;
    $("connect-btn").disabled = false;
  }
});

function openLoginWindow(session_id, expires_at) {
  $("login-wrap").hidden = false;
  canvas = $("login-canvas");
  ctx = canvas.getContext("2d");
  canvas.width = W; canvas.height = H;
  canvas.focus();

  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  ws = new WebSocket(`${proto}//${location.host}/ws/login/${session_id}`);
  ws.onmessage = (msg) => {
    const m = JSON.parse(msg.data);
    if (m.type === "frame") paintFrame(m);
    else if (m.type === "error") { toast(m.message, "err"); }
  };
  ws.onclose = () => { stopLoginWindow(); };

  if (expires_at) {
    const deadline = typeof expires_at === "number" ? expires_at * 1000 : Date.parse(expires_at);
    expiresTimer = setInterval(() => {
      const left = Math.max(0, Math.floor((deadline - Date.now()) / 1000));
      $("expires-in").textContent = left ? `${Math.floor(left / 60)}m ${String(left % 60).padStart(2,"0")}s` : "expired";
      if (!left) stopLoginWindow();
    }, 1000);
  }
}

function paintFrame(m) {
  const img = new Image();
  img.onload = () => {
    if (canvas.width !== m.w || canvas.height !== m.h) {
      canvas.width = m.w; canvas.height = m.h; W = m.w; H = m.h;
    }
    ctx.drawImage(img, 0, 0);
  };
  img.src = "data:image/jpeg;base64," + m.jpeg;
  $("live-url").textContent = m.url;
}

function pageCoord(ev) {
  const r = canvas.getBoundingClientRect();
  return {
    x: Math.round((ev.clientX - r.left) * W / r.width),
    y: Math.round((ev.clientY - r.top)  * H / r.height),
  };
}
function send(obj) { if (ws && ws.readyState === 1) ws.send(JSON.stringify(obj)); }

document.addEventListener("mousedown", (ev) => {
  if (!ws || ev.target !== canvas) return;
  const { x, y } = pageCoord(ev); send({ type: "mouse", kind: "mousePressed", x, y });
});
document.addEventListener("mouseup", (ev) => {
  if (!ws || ev.target !== canvas) return;
  const { x, y } = pageCoord(ev); send({ type: "mouse", kind: "mouseReleased", x, y });
});
document.addEventListener("mousemove", (ev) => {
  if (!ws || ev.target !== canvas) return;
  const { x, y } = pageCoord(ev); send({ type: "mouse", kind: "mouseMoved", x, y });
});
document.addEventListener("wheel", (ev) => {
  if (!ws || ev.target !== canvas) return;
  ev.preventDefault();
  const { x, y } = pageCoord(ev); send({ type: "wheel", x, y, dy: Math.round(ev.deltaY) });
}, { passive: false });

const SPECIAL = new Set(["Enter","Backspace","Tab","Escape","ArrowLeft","ArrowUp","ArrowRight","ArrowDown","Delete"]);
document.addEventListener("keydown", (ev) => {
  if (!ws || document.activeElement !== canvas) return;
  if (SPECIAL.has(ev.key)) { ev.preventDefault(); send({ type: "key", key: ev.key }); return; }
  if (ev.key.length === 1 && !ev.ctrlKey && !ev.metaKey) { ev.preventDefault(); send({ type: "text", text: ev.key }); }
});

$("signed-in-btn").addEventListener("click", async () => {
  if (!ws) return;
  try { send({ type: "done" }); } catch {}
  try { ws.close(); } catch {}
  const r = await fetch(`/api/accounts/save/${sessionId}`, { method: "POST" });
  if (!r.ok) { toast((await r.json()).detail || "save failed", "err"); return; }
  toast("Account saved");
  stopLoginWindow();
  loadAccounts();
});

$("cancel-login").addEventListener("click", () => {
  if (ws) try { ws.close(); } catch {}
  stopLoginWindow();
});

function stopLoginWindow() {
  $("login-wrap").hidden = true;
  $("connect-btn").disabled = false;
  clearInterval(expiresTimer);
  expiresTimer = null;
  ws = null;
}

$("run-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("run-btn").disabled = true;
  $("run-panel").hidden = false;
  $("run-status").textContent = "Starting…";
  $("run-trace").textContent = "";
  $("run-stream").innerHTML = "";
  $("run-result").hidden = true;
  try {
    const r = await fetch("/api/accounts/run", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        site: $("run-site").value.trim(),
        request: $("run-request").value.trim(),
        action: $("run-action").value,
      }),
    });
    if (!r.ok) throw new Error((await r.json()).detail || "run failed");
    const { audit_id } = await r.json();
    streamJob(audit_id);
  } catch (err) {
    $("run-status").textContent = "Error: " + err.message;
    toast(err.message, "err");
    $("run-btn").disabled = false;
  }
});

function streamJob(jobId) {
  const es = new EventSource(`/api/audit/${jobId}/events`);
  es.onmessage = (msg) => {
    const e = JSON.parse(msg.data);
    if (e.type === "task_update") {
      $("run-status").textContent = `${e.status.toLowerCase()} · ${e.steps} steps`;
      if (e.last_action) $("run-trace").textContent = "› " + e.last_action;
      const stream = $("run-stream");
      if (e.streaming_url && !stream.dataset.loaded) {
        stream.dataset.loaded = "1";
        stream.innerHTML = `
          <details class="task-stream" open>
            <summary>Live agent view</summary>
            <iframe src="${e.streaming_url}" allow="autoplay"></iframe>
          </details>`;
      }
    } else if (e.type === "account_done") {
      $("run-status").textContent = "Done — nothing was bought or sent";
      $("run-stream").innerHTML = "";
      $("run-result").hidden = false;
      $("run-result").textContent = JSON.stringify(e.result, null, 2);
      $("run-btn").disabled = false;
      es.close();
      toast("Agent finished");
    } else if (e.type === "error") {
      $("run-status").textContent = "Error: " + e.message;
      toast(e.message, "err");
      $("run-btn").disabled = false;
      es.close();
    }
  };
  es.onerror = () => { es.close(); $("run-btn").disabled = false; };
}

loadAccounts();
