const state = {
  index: null,
  selectedThemeId: null,
  query: "",
  themeCache: new Map(),
};

function $(id) {
  const el = document.getElementById(id);
  if (!el) throw new Error(`Missing element: #${id}`);
  return el;
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderSummaryHtml(summaryText) {
  const raw = String(summaryText || "").replaceAll("\r\n", "\n").trim();
  if (!raw) return "";

  const lines = raw.split("\n");
  const out = [];

  const flushParagraph = (buf) => {
    const text = buf.join(" ").trim();
    if (!text) return;
    out.push(`<p class="themeSummary__p">${escapeHtml(text)}</p>`);
  };

  let paragraph = [];
  for (const lineRaw of lines) {
    const line = lineRaw.trim();

    if (!line) {
      flushParagraph(paragraph);
      paragraph = [];
      continue;
    }

    const bracket = line.match(/^【(.+?)】$/);
    if (bracket) {
      flushParagraph(paragraph);
      paragraph = [];
      out.push(`<h3 class="themeSummary__h">${escapeHtml(bracket[1])}</h3>`);
      continue;
    }

    const mdHeading = line.match(/^(#{1,3})\s+(.+)$/);
    if (mdHeading) {
      flushParagraph(paragraph);
      paragraph = [];
      out.push(`<h3 class="themeSummary__h">${escapeHtml(mdHeading[2].trim())}</h3>`);
      continue;
    }

    paragraph.push(line);
  }
  flushParagraph(paragraph);

  return out.join("");
}

function blockHeading(block) {
  const memberUtterance = block.utterances.find((u) => u.speaker_type === "member");
  if (!memberUtterance) return "";
  const line = (memberUtterance.text || "").split("\n")[0].trim();
  if (line.length <= 80) return line;
  return `${line.slice(0, 80).trim()}…`;
}

function renderThemeList() {
  const list = $("themeList");
  list.innerHTML = "";
  const themes = state.index?.themes || [];
  for (const t of themes) {
    const card = document.createElement("div");
    card.className = "themeCard" + (t.id === state.selectedThemeId ? " is-active" : "");
    card.dataset.themeId = t.id;
    card.innerHTML = `
      <div class="themeCard__title">${escapeHtml(t.title)}</div>
      <div class="themeCard__meta">
        <span>${escapeHtml(t.description || "")}</span>
        <span>${t.block_count}件</span>
      </div>
    `;
    card.addEventListener("click", () => selectTheme(t.id));
    list.appendChild(card);
  }
}

function matchesQuery(block, query) {
  if (!query) return true;
  const q = query.trim();
  if (!q) return true;
  const hay = [
    block.questioner,
    block.meeting_date,
    block.file_name,
    blockHeading(block),
    ...(block.utterances || []).map((u) => u.text),
  ]
    .filter(Boolean)
    .join("\n");
  return hay.includes(q);
}

function renderBlocks(themeData) {
  const blocksEl = $("blocks");
  const blocks = themeData?.blocks || [];
  const filtered = blocks.filter((b) => matchesQuery(b, state.query));

  if (filtered.length === 0) {
    blocksEl.innerHTML = `<div class="muted">該当する質疑が見つかりませんでした。</div>`;
    return;
  }

  blocksEl.innerHTML = "";

  for (const block of filtered) {
    const el = document.createElement("div");
    el.className = "block";

    const summary = document.createElement("div");
    summary.className = "block__summary";
    const themeHits = (block.theme?.hits || []).slice(0, 10);
    const chipHtml =
      themeHits.length > 0
        ? `<div class="chips">${themeHits.map((h) => `<span class="chip">${escapeHtml(h)}</span>`).join("")}</div>`
        : "";
    summary.innerHTML = `
      <div style="min-width: 0">
        <div class="block__title">${escapeHtml(block.questioner)}：${escapeHtml(blockHeading(block))}</div>
        ${chipHtml}
      </div>
      <div style="display:flex; flex-direction:column; align-items:flex-end; gap:10px">
        <div class="block__meta">${escapeHtml(block.meeting_date || "")} / ${escapeHtml(
      block.file_name || ""
    )}</div>
        <button class="btn btn--small js-toggle" type="button">議事録の該当文章を見る</button>
      </div>
    `;

    const body = document.createElement("div");
    body.className = "block__body";

    const source = document.createElement("div");
    source.className = "muted small";
    source.style.marginBottom = "10px";
    source.innerHTML = `
      <div>出典: gikai_9.md の行 ${block.start_line}〜${block.end_line}（概算）</div>
      <div style="margin-top:8px; display:flex; gap:10px; flex-wrap:wrap">
        <a class="btn btn--small" href="../gikai_9.md" target="_blank" rel="noreferrer">統合議事録（原文全体）を開く</a>
      </div>
    `;
    body.appendChild(source);

    for (const u of block.utterances || []) {
      const ut = document.createElement("div");
      ut.className = "utterance";
      const badge = u.speaker_type || "staff";
      const speakerName = u.speaker?.name || "";
      const speakerTitle = u.speaker?.title || "";
      ut.innerHTML = `
        <div class="utterance__head">
          <div>
            <span class="badge ${escapeHtml(badge)}">${escapeHtml(badge)}</span>
            <span class="utterance__name">${escapeHtml(speakerName)}</span>
            <span class="muted small">${escapeHtml(speakerTitle ? `(${speakerTitle})` : "")}</span>
          </div>
          <div class="muted small">${u.start_line}〜${u.end_line}</div>
        </div>
        <div class="utterance__text">${escapeHtml(u.text || "")}</div>
      `;
      body.appendChild(ut);
    }

    const toggle = summary.querySelector(".js-toggle");
    toggle?.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      el.classList.toggle("is-open");
      toggle.textContent = el.classList.contains("is-open")
        ? "閉じる"
        : "議事録の該当文章を見る";
    });

    el.appendChild(summary);
    el.appendChild(body);
    blocksEl.appendChild(el);
  }
}

async function fetchJson(path) {
  const res = await fetch(path, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to load ${path}: ${res.status}`);
  return await res.json();
}

async function selectTheme(themeId) {
  state.selectedThemeId = themeId;
  renderThemeList();

  const themeMeta = (state.index?.themes || []).find((t) => t.id === themeId);
  $("themeTitle").textContent = themeMeta ? themeMeta.title : themeId;
  $("themeDesc").textContent = themeMeta?.description || "";

  if (!state.themeCache.has(themeId)) {
    const data = await fetchJson(`../out/themes/${themeId}.json`);
    state.themeCache.set(themeId, data);
  }
  const themeData = state.themeCache.get(themeId);
  const summaryText = (themeData?.summary || "").trim();
  $("themeSummary").innerHTML =
    renderSummaryHtml(summaryText) ||
    `<p class="themeSummary__p muted">（このテーマの簡単解説は準備中です。<code>NIHO/gikai/theme_explanations.json</code> に追記できます）</p>`;
  renderBlocks(themeData);
}

async function main() {
  state.index = await fetchJson("../out/themes.json");
  renderThemeList();

  const first = state.index?.themes?.[0]?.id;
  if (first) await selectTheme(first);

  $("q").addEventListener("input", (e) => {
    state.query = e.target.value || "";
    if (!state.selectedThemeId) return;
    const data = state.themeCache.get(state.selectedThemeId);
    if (data) renderBlocks(data);
  });
}

main().catch((err) => {
  console.error(err);
  $("themeTitle").textContent = "読み込みに失敗しました";
  $("themeDesc").textContent =
    "このHTMLはローカルサーバー経由で開く必要があります（file://直開きだとJSONを読めません）。URLは http.server の起動場所で変わります：app/ で起動なら /NIHO/gikai/view/、NIHO/gikai/ で起動なら /view/。";
  $("blocks").innerHTML = `<pre class="muted small">${escapeHtml(err.stack || err.message || String(err))}</pre>`;
});
