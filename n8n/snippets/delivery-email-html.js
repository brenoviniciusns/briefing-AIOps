const r = $input.first().json;
const esc = (s) => String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

/** Link clicável “Fonte” → URL do artigo (validação). */
function fmtFonteHtml(source, articleUrl) {
  const u = String(articleUrl || '').trim();
  const src = esc(String(source || 'artigo'));
  if (!u) {
    return source ? ` <small>(fonte: ${src})</small>` : '';
  }
  return ` <small>— <a href="${esc(u)}">Fonte: ${src}</a></small>`;
}

const sections = r.sections || {};
const cats = ['AI', 'Architecture', 'Data'];
const catLabels = { AI: 'IA', Architecture: 'Arquitetura', Data: 'Dados' };

let body = `<html><head><style>
body{font-family:Segoe UI,Arial,sans-serif;line-height:1.55;color:#222;max-width:720px;}
h1{font-size:1.35rem;margin:0 0 1em 0;}
h2{font-size:1.15rem;margin:2em 0 0.6em 0;padding-bottom:0.25em;border-bottom:1px solid #e0e0e0;}
h3{font-size:1.05rem;margin:1.35em 0 0.4em 0;color:#333;}
.topic-block{margin:0 0 1.75em 0;padding-bottom:1.25em;border-bottom:1px dashed #ddd;}
.topic-block:last-of-type{border-bottom:none;}
p{margin:0.5em 0;}
ul{margin:0.4em 0 0.8em 1.2em;}
hr.major{border:0;border-top:1px solid #ccc;margin:2em 0;}
</style></head><body>`;

body += `<h1>Inteligência técnica — ${esc(r.date)}</h1>`;

const shorts = r.linkedin_short_topics || r.linkedin_topics || [];
if (shorts.length) {
  body += `<hr class="major"/>`;
  body += `<h2>LinkedIn — 3 ganchos rápidos</h2>`;
  const sorted = [...shorts].sort((a, b) => (a.rank || 99) - (b.rank || 99));
  sorted.forEach((t, idx) => {
    const pa = t.primary_article || {};
    const hook = esc(t.hook_line || t.angle_for_post || '');
    body += `<div class="topic-block">`;
    body += `<h3>${esc(t.topic_label)}</h3>`;
    body += `<p><strong>Match:</strong> ${esc(String(t.profile_match_score || ''))}/100</p>`;
    body += `<p>${hook}</p>`;
    body += `<p><a href="${esc(pa.url)}">${esc(pa.title)}</a>${fmtFonteHtml(pa.source, pa.url)}</p>`;
    const ex = t.extra_articles || [];
    if (ex.length) {
      body += `<p><small>Mais: ${ex.map((e) => `<a href="${esc(e.url)}">${esc(e.title)}</a>${fmtFonteHtml(e.source, e.url)}`).join(' · ')}</small></p>`;
    }
    body += `</div>`;
  });
}

const deep = r.linkedin_deep_topic;
if (deep && typeof deep === 'object' && deep.topic_label) {
  body += `<hr class="major"/>`;
  body += `<h2>LinkedIn — tema em destaque (mais detalhe)</h2>`;
  const pa = deep.primary_article || {};
  body += `<div class="topic-block">`;
  body += `<h3>${esc(deep.topic_label)}</h3>`;
  body += `<p><strong>Match:</strong> ${esc(String(deep.profile_match_score || ''))}/100</p>`;
  body += `<p>${esc(deep.angle_for_post || '')}</p>`;
  body += `<p><a href="${esc(pa.url)}">${esc(pa.title)}</a>${fmtFonteHtml(pa.source, pa.url)}</p>`;
  const ex = deep.extra_articles || [];
  if (ex.length) {
    body += `<p><small>Mais: ${ex.map((e) => `<a href="${esc(e.url)}">${esc(e.title)}</a>${fmtFonteHtml(e.source, e.url)}`).join(' · ')}</small></p>`;
  }
  body += `</div>`;
}

const ins = r.llm_insights || {};
if (ins.key_insights && ins.key_insights.length) {
  body += `<hr class="major"/>`;
  body += `<h2>Insights principais</h2><ul>`;
  body += ins.key_insights.map((x) => `<li>${esc(x)}</li>`).join('');
  body += `</ul>`;
}

for (const c of cats) {
  const items = sections[c] || [];
  if (!items.length) continue;
  body += `<hr class="major"/>`;
  body += `<h2>${esc(catLabels[c] || c)}</h2>`;
  for (const it of items) {
    body += `<div class="topic-block">`;
    body += `<h3>${esc(it.title)}</h3>`;
    body += `<p><a href="${esc(it.url)}">Abrir artigo</a>${fmtFonteHtml(it.source, it.url)}</p>`;
    body += `<p style="color:#444">${esc((it.summary || '').slice(0, 220))}</p>`;
    body += `</div>`;
  }
}

body += `<hr class="major"/>`;
body += `<p><small><strong>Fontes de dados (feeds / APIs):</strong> ${esc((r.sources || []).join(', ') || '—')}</small></p>`;
if (r.window_start && r.window_end) {
  body += `<p><small>Janela RAW: ${esc(r.window_start)} → ${esc(r.window_end)} (${esc(String(r.lookback_days || ''))} dia(s))</small></p>`;
}
body += `</body></html>`;

/** Texto para Slack / fallback Notion: preserva quebras; links como "texto (url)". */
function htmlToReadablePlain(html) {
  let t = String(html);
  t = t.replace(/<\/h1>/gi, '\n\n');
  t = t.replace(/<\/h2>/gi, '\n\n═══ ');
  t = t.replace(/<\/h3>/gi, '\n\n▸ ');
  t = t.replace(/<\/p>/gi, '\n\n');
  t = t.replace(/<br\s*\/?>/gi, '\n');
  t = t.replace(/<\/div>/gi, '\n\n');
  t = t.replace(/<hr[^>]*>/gi, '\n\n────────\n\n');
  t = t.replace(/<\/li>/gi, '\n');
  t = t.replace(/<\/ul>|<\/ol>/gi, '\n\n');
  t = t.replace(/<a\s+[^>]*href=["']([^"']+)["'][^>]*>([^<]*)<\/a>/gi, '$2 ($1)');
  t = t.replace(/<[^>]+>/g, '');
  t = t.replace(/&nbsp;/g, ' ');
  t = t.replace(/&amp;/g, '&');
  t = t.replace(/&lt;/g, '<');
  t = t.replace(/&gt;/g, '>');
  t = t.replace(/\n{3,}/g, '\n\n');
  return t.trim();
}

const MAX_NOTION = 100;

function rt(content) {
  return [{ type: 'text', text: { content: String(content || ' ').slice(0, 2000) } }];
}

function blkHeading2(text) {
  return { object: 'block', type: 'heading_2', heading_2: { rich_text: rt(text) } };
}

function blkHeading3(text) {
  return { object: 'block', type: 'heading_3', heading_3: { rich_text: rt(text) } };
}

function blkDivider() {
  return { object: 'block', type: 'divider', divider: {} };
}

function blkParaPlain(text) {
  const s = String(text || '');
  const blocks = [];
  for (let i = 0; i < s.length; i += 1900) {
    blocks.push({
      object: 'block',
      type: 'paragraph',
      paragraph: { rich_text: rt(s.slice(i, i + 1900)) },
    });
  }
  return blocks.length ? blocks : [{ object: 'block', type: 'paragraph', paragraph: { rich_text: rt(' ') } }];
}

function blkParaArtigoComFonte(title, url, source) {
  const u = String(url || '').trim();
  const parts = [];
  parts.push({ type: 'text', text: { content: 'Artigo: ' } });
  if (u) {
    parts.push({ type: 'text', text: { content: String(title || 'Abrir').slice(0, 1800), link: { url: u.slice(0, 1990) } } });
  } else {
    parts.push({ type: 'text', text: { content: String(title || '').slice(0, 1900) } });
  }
  if (source && u) {
    parts.push({ type: 'text', text: { content: '  ·  Validar na fonte: ' } });
    parts.push({
      type: 'text',
      text: { content: String(source).slice(0, 500), link: { url: u.slice(0, 1990) } },
    });
  }
  return { object: 'block', type: 'paragraph', paragraph: { rich_text: parts } };
}

function blkBullet(text) {
  return {
    object: 'block',
    type: 'bulleted_list_item',
    bulleted_list_item: { rich_text: rt(text) },
  };
}

function buildNotionChildren(rep) {
  const out = [];
  const push = (b) => {
    if (out.length >= MAX_NOTION) return false;
    if (Array.isArray(b)) {
      for (const x of b) {
        if (!push(x)) return false;
      }
      return true;
    }
    out.push(b);
    return true;
  };

  push(blkHeading2(`Inteligência técnica — ${rep.date}`));
  push(blkDivider());

  const sh = rep.linkedin_short_topics || rep.linkedin_topics || [];
  if (sh.length) {
    push(blkHeading2('LinkedIn — 3 ganchos rápidos'));
    const sorted = [...sh].sort((a, b) => (a.rank || 99) - (b.rank || 99));
    sorted.forEach((t) => {
      if (out.length >= MAX_NOTION - 8) return;
      const pa = t.primary_article || {};
      push(blkHeading3(String(t.topic_label || 'Assunto')));
      push(blkParaPlain(`Match: ${t.profile_match_score ?? ''}/100`));
      push(blkParaPlain(t.hook_line || t.angle_for_post || ''));
      push(blkParaArtigoComFonte(pa.title, pa.url, pa.source));
      const ex = t.extra_articles || [];
      for (const e of ex) {
        if (out.length >= MAX_NOTION - 2) break;
        push(blkParaArtigoComFonte(e.title, e.url, e.source));
      }
      push(blkDivider());
    });
  }

  const dp = rep.linkedin_deep_topic;
  if (dp && typeof dp === 'object' && dp.topic_label && out.length < MAX_NOTION - 6) {
    push(blkHeading2('LinkedIn — tema em destaque'));
    push(blkHeading3(String(dp.topic_label)));
    push(blkParaPlain(`Match: ${dp.profile_match_score ?? ''}/100`));
    push(blkParaPlain(dp.angle_for_post || ''));
    const pa = dp.primary_article || {};
    push(blkParaArtigoComFonte(pa.title, pa.url, pa.source));
    const ex = dp.extra_articles || [];
    for (const e of ex) {
      if (out.length >= MAX_NOTION - 2) break;
      push(blkParaArtigoComFonte(e.title, e.url, e.source));
    }
    push(blkDivider());
  }

  const ins2 = rep.llm_insights || {};
  if (ins2.key_insights && ins2.key_insights.length && out.length < MAX_NOTION - 5) {
    push(blkHeading2('Insights principais'));
    for (const x of ins2.key_insights) {
      if (out.length >= MAX_NOTION - 1) break;
      push(blkBullet(x));
    }
    push(blkDivider());
  }

  for (const c of cats) {
    const items = (rep.sections || {})[c] || [];
    if (!items.length) continue;
    if (out.length >= MAX_NOTION - 3) break;
    push(blkHeading2(catLabels[c] || c));
    let n = 0;
    for (const it of items) {
      if (out.length >= MAX_NOTION - 2 || n >= 12) break;
      push(blkHeading3(String(it.title || '').slice(0, 200)));
      push(blkParaArtigoComFonte(it.title, it.url, it.source));
      push(blkParaPlain((it.summary || '').slice(0, 400)));
      push(blkDivider());
      n += 1;
    }
  }

  if (out.length < MAX_NOTION) {
    push(blkParaPlain(`Fontes de dados: ${(rep.sources || []).join(', ') || '—'}`));
  }
  return out.slice(0, MAX_NOTION);
}

const notion_children = buildNotionChildren(r);

return [
  {
    json: {
      html: body,
      subject: `Relatório tech + LinkedIn ${r.date}`,
      report_date: r.date,
      slack_text: htmlToReadablePlain(body),
      notion_children,
    },
  },
];
