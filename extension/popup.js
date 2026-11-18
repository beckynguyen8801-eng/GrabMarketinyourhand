const $ = (id) => document.getElementById(id);

async function load() {
  const s = await chrome.storage.local.get(["mode", "repo", "ghToken", "server", "token", "industry", "auto", "stats"]);
  $("mode").value = s.mode || "github";
  $("repo").value = s.repo || "";
  $("ghToken").value = s.ghToken || "";
  toggleFields();
  $("server").value = s.server || "http://127.0.0.1:8765";
  $("token").value = s.token || "";
  $("industry").value = s.industry || "";
  $("auto").checked = !!s.auto;
  if (s.stats) $("stats").textContent = `Sent ${s.stats.sent} posts · ${s.stats.new} new · last ${new Date(s.stats.last).toLocaleTimeString()}`;
  chrome.runtime.sendMessage({ type: "health" }, (r) => {
    $("health").textContent = r?.ok
      ? (r.mode === "local" ? "Connected to local VN Listen" : "Connected to GitHub – appears on the dashboard after the next scheduled run")
      : r?.missing ? "Open Settings: add repository + token"
      : r?.mode === "local" ? "Server offline – run: vnlisten serve" : "Cannot reach the repository – check name and token";
    $("health").className = r?.ok ? "ok" : "bad";
  });
}

function toggleFields() {
  const local = $("mode").value === "local";
  $("localFields").style.display = local ? "" : "none";
  $("githubFields").style.display = local ? "none" : "";
}
$("mode").addEventListener("change", () => { toggleFields(); chrome.storage.local.set({ mode: $("mode").value }).then(load); });

for (const id of ["repo", "ghToken", "server", "token", "industry"]) {
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
      $("capture").textContent = !r.ok ? `Error: ${r.error}`
        : r.queued ? `Queued ${r.received || 0} posts for the next run` : `Sent ${r.received || 0} posts (${r.new || 0} new)`;
    }
    setTimeout(() => { $("capture").textContent = "Capture this page"; load(); }, 2500);
  });
});

load();
