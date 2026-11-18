// Background service worker: the only place that talks to the local VN Listen server.
const DEFAULTS = { mode: "github", repo: "", ghToken: "", server: "http://127.0.0.1:8765", token: "", industry: "", auto: false };

async function settings() {
  return { ...DEFAULTS, ...(await chrome.storage.local.get(Object.keys(DEFAULTS))) };
}

// Base64 for UTF-8 text (Vietnamese) – btoa() alone breaks on non-Latin characters
function b64(text) {
  const bytes = new TextEncoder().encode(text);
  let bin = "";
  for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(bin);
}

async function gh(s, path, init = {}) {
  const res = await fetch(`https://api.github.com/repos/${s.repo}${path}`, {
    ...init,
    headers: { Accept: "application/vnd.github+json", Authorization: `Bearer ${s.ghToken}`,
               "X-GitHub-Api-Version": "2022-11-28", ...(init.headers || {}) },
  });
  const body = await res.json().catch(() => ({}));
  return { ok: res.ok, status: res.status, body };
}

// GitHub mode: each capture becomes one JSON file on the `captures` branch.
// The scheduled GitHub Actions run ingests them into the dashboard, then deletes them.
async function sendToGitHub(s, payload) {
  if (!s.repo || !s.ghToken) throw new Error("Set Repository and GitHub token in Settings");
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const path = `captures/${stamp.slice(0, 10)}/${stamp}-${Math.random().toString(36).slice(2, 8)}.json`;
  const put = () => gh(s, `/contents/${path}`, {
    method: "PUT",
    body: JSON.stringify({ message: `capture: ${payload.items.length} ${payload.source} post(s)`,
                           content: b64(JSON.stringify(payload)), branch: "captures" }),
  });
  let r = await put();
  if (r.status === 404 || r.status === 422) {          // first time: create the captures branch from main
    const main = await gh(s, "/git/ref/heads/main");
    if (!main.ok) throw new Error(`Cannot read repo (${main.status}) – check repository name and token`);
    await gh(s, "/git/refs", { method: "POST", body: JSON.stringify({ ref: "refs/heads/captures", sha: main.body.object.sha }) });
    r = await put();
  }
  if (!r.ok) throw new Error(r.body.message || `GitHub HTTP ${r.status}`);
  return { received: payload.items.length, new: payload.items.length, queued: true };
}

async function sendToLocal(s, payload) {
  const res = await fetch(`${s.server}/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(s.token ? { "X-VNListen-Token": s.token } : {}) },
    body: JSON.stringify(payload),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.error || `HTTP ${res.status}`);
  return body;
}

async function send(payload) {
  const s = await settings();
  if (s.industry) payload.industry = s.industry;
  const body = s.mode === "local" ? await sendToLocal(s, payload) : await sendToGitHub(s, payload);
  const stats = (await chrome.storage.local.get("stats")).stats || { sent: 0, new: 0 };
  stats.sent += body.received || 0;
  stats.new += body.new || 0;
  stats.last = new Date().toISOString();
  await chrome.storage.local.set({ stats });
  return body;
}

chrome.runtime.onMessage.addListener((msg, _sender, reply) => {
  if (msg.type === "ingest") {
    send(msg.payload).then((r) => reply({ ok: true, ...r })).catch((e) => reply({ ok: false, error: e.message }));
    return true; // async reply
  }
  if (msg.type === "health") {
    settings()
      .then(async (s) => {
        if (s.mode === "local") return { ok: (await fetch(`${s.server}/health`)).ok, mode: "local" };
        if (!s.repo || !s.ghToken) return { ok: false, mode: "github", missing: true };
        return { ok: (await gh(s, "")).ok, mode: "github" };
      })
      .then(reply)
      .catch(() => reply({ ok: false }));
    return true;
  }
});

// Right-click any selected text on any site -> send it (works even when page layouts change)
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({ id: "vnlisten-selection", title: "Send selected text to VN Listen", contexts: ["selection"] });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId !== "vnlisten-selection" || !info.selectionText) return;
  const host = new URL(tab.url).hostname;
  const source = host.includes("facebook") ? "facebook" : host.includes("tiktok") ? "tiktok"
    : host.includes("instagram") ? "instagram" : host.includes("threads") ? "threads" : "web";
  send({ source, page_url: tab.url, page_title: tab.title,
         items: [{ url: tab.url, text: info.selectionText }] }).catch((e) => console.warn("VN Listen:", e));
});
