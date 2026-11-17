// Reads posts that are VISIBLE on the page you are browsing. No automation: nothing is clicked or scrolled for you.
// Platform layouts change often – if a site stops working, the right-click "Send selected text" still does.
(() => {
  const host = location.hostname;
  const seen = new Set();
  const txt = (el) => (el?.innerText || "").replace(/\s+\n/g, "\n").trim();
  const abs = (href) => { try { return new URL(href, location.href).href.split("?")[0]; } catch { return ""; } };
  const count = (text, re) => (text.match(re) || [])[1] || "";

  // ---------------- Facebook ----------------
  function facebook() {
    const g = location.pathname.match(/^\/groups\/([^/]+)/);
    const pageText = document.body.innerText.slice(0, 4000);
    const visibility = /Nhóm Công khai|Public group/i.test(pageText) ? "public"
      : /Nhóm Riêng tư|Private group/i.test(pageText) ? "private" : "unknown";
    const community = g
      ? { name: txt(document.querySelector("h1")), url: `https://www.facebook.com/groups/${g[1]}`, visibility }
      : { name: txt(document.querySelector("h1")), url: "", visibility: "unknown" };
    const items = [];
    for (const art of document.querySelectorAll('[role="article"]')) {
      if (art.parentElement?.closest('[role="article"]')) continue; // skip comments nested in posts
      const body = art.querySelector('[data-ad-preview="message"], [data-ad-comet-preview="message"]') || art;
      const text = [...body.querySelectorAll('[dir="auto"]')].map(txt).filter(Boolean)
        .filter((t, i, a) => a.indexOf(t) === i).join("\n") || txt(body);
      const link = art.querySelector('a[href*="/posts/"], a[href*="/permalink/"], a[href*="story_fbid"], a[href*="/videos/"]');
      const all = txt(art);
      items.push({
        url: link ? abs(link.href) : "",
        text,
        author: txt(art.querySelector("h2, h3, strong")),
        likes: count(all, /(?:Tất cả cảm xúc|All reactions):?\s*([\d.,]+\s*[KkNM]?)/),
        comments: count(all, /([\d.,]+\s*[KkNM]?)\s*(?:bình luận|comments?)/i),
        shares: count(all, /([\d.,]+\s*[KkNM]?)\s*(?:lượt chia sẻ|shares?)/i),
      });
    }
    return { source: "facebook", community, items };
  }

  // ---------------- TikTok ----------------
  function tiktok() {
    const items = [];
    const video = document.querySelector('[data-e2e="browse-video-desc"], [data-e2e="video-desc"]');
    if (video) {
      items.push({
        url: location.href.split("?")[0], text: txt(video),
        likes: txt(document.querySelector('[data-e2e="like-count"], [data-e2e="browse-like-count"]')),
        comments: txt(document.querySelector('[data-e2e="comment-count"], [data-e2e="browse-comment-count"]')),
        shares: txt(document.querySelector('[data-e2e="share-count"]')),
      });
      for (const c of document.querySelectorAll('[data-e2e="comment-level-1"]')) {
        items.push({ url: location.href.split("?")[0] + "#c-" + txt(c).slice(0, 30), text: txt(c) });
      }
    }
    for (const a of document.querySelectorAll('a[href*="/video/"]')) { // search / hashtag / profile grids
      const card = a.closest('[data-e2e*="item"], [class*="DivItemContainer"]') || a.parentElement;
      const caption = card?.querySelector('[data-e2e*="desc"], [data-e2e*="caption"]');
      if (caption) items.push({ url: abs(a.href), text: txt(caption), views: txt(card.querySelector('[data-e2e*="views"]')) });
    }
    return { source: "tiktok", community: {}, items };
  }

  // ---------------- Instagram ----------------
  function instagram() {
    const items = [];
    for (const art of document.querySelectorAll("article")) {
      const link = art.querySelector('a[href*="/p/"], a[href*="/reel/"]');
      const caption = art.querySelector("h1") || art.querySelector('span[dir="auto"]');
      const all = txt(art);
      items.push({ url: link ? abs(link.href) : location.href, text: txt(caption),
                   likes: count(all, /([\d.,]+\s*[KkNM]?)\s*(?:lượt thích|likes?)/i) });
    }
    const owner = location.pathname.split("/").filter(Boolean)[0];
    return { source: "instagram", community: owner && !["p", "reel", "explore"].includes(owner)
      ? { name: owner, url: `https://www.instagram.com/${owner}` } : {}, items };
  }

  // ---------------- Threads ----------------
  function threads() {
    const items = [];
    for (const box of document.querySelectorAll('[data-pressable-container="true"]')) {
      const link = box.querySelector('a[href*="/post/"]');
      const text = [...box.querySelectorAll('span[dir="auto"]')].map(txt).filter((t) => t.length > 3).join("\n");
      items.push({ url: link ? abs(link.href) : "", text });
    }
    return { source: "threads", community: {}, items };
  }

  function extract() {
    const data = host.includes("facebook") ? facebook() : host.includes("tiktok") ? tiktok()
      : host.includes("instagram") ? instagram() : threads();
    data.items = data.items.filter((it) => it.text && it.text.length > 10).filter((it) => {
      const key = (it.url || "") + "|" + it.text.slice(0, 80);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
    return { ...data, page_url: location.href, page_title: document.title };
  }

  function capture() {
    const payload = extract();
    if (!payload.items.length) return Promise.resolve({ ok: true, received: 0 });
    return chrome.runtime.sendMessage({ type: "ingest", payload });
  }

  // Popup -> "Capture this page"
  chrome.runtime.onMessage.addListener((msg, _s, reply) => {
    if (msg.type === "capture") { seen.clear(); capture().then(reply); return true; }
  });

  // Auto mode: capture new posts a few seconds after you stop scrolling
  let timer;
  window.addEventListener("scroll", () => {
    clearTimeout(timer);
    timer = setTimeout(async () => {
      const { auto } = await chrome.storage.local.get("auto");
      if (auto) capture();
    }, 2500);
  }, { passive: true });
})();
