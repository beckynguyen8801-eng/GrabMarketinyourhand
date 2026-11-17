const $ = (id) => document.getElementById(id);

async function load() {
  const s = await chrome.storage.local.get(["server", "token", "industry", "auto", "stats"]);
  $("server").value = s.server || "http://127.0.0.1:8765";
  $("token").value = s.token || "";
  $("industry").value = s.industry || "";
  $("auto").checked = !!s.auto;
  if (s.stats) $("stats").textContent = `Sent ${s.stats.sent} posts · ${s.stats.new} new · last ${new Date(s.stats.last).toLocaleTimeString()}`;
  chrome.runtime.sendMessage({ type: "health" }, (r) => {
    $("health").textContent = r?.ok ? "Connected to VN Listen" : "Server offline – run: vnlisten serve";
    $("health").className = r?.ok ? "ok" : "bad";
  });
}

for (const id of ["server", "token", "industry"]) {
  $(id).addEventListener("change", () => chrome.storage.local.set({ [id]: $(id).value.trim() }));
}
$("auto").addEventListener("change", () => chrome.storage.local.set({ auto: $("auto").checked }));

$("capture").addEventListener("click", async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  $("capture").textContent = "Capturing…";
  chrome.tabs.sendMessage(tab.id, { type: "capture" }, (r) => {
    if (chrome.runtime.lastError || !r) {
      $("capture").textContent = "Open Facebook / TikTok / Instagram / Threads first";
    } else {
      $("capture").textContent = r.ok ? `Sent ${r.received || 0} posts (${r.new || 0} new)` : `Error: ${r.error}`;
    }
    setTimeout(() => { $("capture").textContent = "Capture this page"; load(); }, 2500);
  });
});

load();
