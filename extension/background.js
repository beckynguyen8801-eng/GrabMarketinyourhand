// Background service worker: the only place that talks to the local VN Listen server.
const DEFAULTS = { server: "http://127.0.0.1:8765", token: "", industry: "", auto: false };

async function settings() {
  return { ...DEFAULTS, ...(await chrome.storage.local.get(Object.keys(DEFAULTS))) };
}

async function send(payload) {
  const s = await settings();
  if (s.industry) payload.industry = s.industry;
  const res = await fetch(`${s.server}/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(s.token ? { "X-VNListen-Token": s.token } : {}) },
    body: JSON.stringify(payload),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.error || `HTTP ${res.status}`);
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
      .then((s) => fetch(`${s.server}/health`))
      .then((r) => reply({ ok: r.ok }))
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
