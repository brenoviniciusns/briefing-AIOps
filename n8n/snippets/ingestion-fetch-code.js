// Code node "Fetch RSS e janela D-1 UTC" — fonte canónica: allowlist_rss.yaml (raiz do repo)
// HTTP: $helpers.httpRequest no editor; n8n Cloud (task runner JS) usa this.helpers — resolver abaixo.
// SHA-256: globalThis.crypto.subtle (Cloud runner) ou require('crypto') (Node).
// Janela: apenas o dia civil anterior em UTC [00:00:00, 23:59:59.999] (não janela móvel de 24h).

/** n8n Cloud 2.13+ (runner isolado) muitas vezes não define $helpers; expõe this.helpers.httpRequest. */
const httpHelpers =
  typeof $helpers !== 'undefined' && $helpers && typeof $helpers.httpRequest === 'function'
    ? $helpers
    : typeof this !== 'undefined' &&
        this.helpers &&
        typeof this.helpers.httpRequest === 'function'
      ? this.helpers
      : null;
if (!httpHelpers) {
  throw new Error(
    'Sem cliente HTTP no Code node: $helpers e this.helpers.httpRequest indisponíveis.',
  );
}

/** Cada fonte: urls por ordem (tenta a seguinte se falhar). tlsInsecure: só se o runner falhar verificação TLS. */
const feeds = [
  { source: 'netflix', urls: ['https://netflixtechblog.com/feed'], tlsInsecure: true },
  {
    source: 'uber',
    urls: ['https://eng.uber.com/feed/', 'https://www.uber.com/blog/engineering/rss/'],
  },
  { source: 'airbnb', urls: ['https://medium.com/feed/airbnb-engineering'] },
  { source: 'databricks', urls: ['https://www.databricks.com/feed', 'https://www.databricks.com/blog/feed'] },
  { source: 'openai', urls: ['https://openai.com/blog/rss.xml'] },
  { source: 'huggingface', urls: ['https://huggingface.co/blog/feed.xml'] },
  { source: 'deeplearning-ai', urls: ['https://blog.deeplearning.ai/feed/', 'https://www.deeplearning.ai/the-batch/feed/'] },
  {
    source: 'azure-updates',
    urls: ['https://www.microsoft.com/releasecommunications/api/v2/azure/rss'],
  },
  { source: 'azure-blog', urls: ['https://azure.microsoft.com/en-us/blog/feed/'] },
  { source: 'ms-semantic-kernel', urls: ['https://devblogs.microsoft.com/semantic-kernel/feed/'] },
  { source: 'azure-sdk-devblog', urls: ['https://devblogs.microsoft.com/azure-sdk/feed/'] },
  { source: 'ms-research', urls: ['https://www.microsoft.com/en-us/research/feed/'] },
  { source: 'pytorch', urls: ['https://pytorch.org/blog/feed.xml'] },
  { source: 'tensorflow-blog', urls: ['https://blog.tensorflow.org/feeds/posts/default?alt=rss'] },
  { source: 'nvidia-blog', urls: ['https://blogs.nvidia.com/feed/'] },
  { source: 'tdan', urls: ['https://tdan.com/feed'] },
];

async function sha256Hex(s) {
  const str = String(s);
  const g = typeof globalThis !== 'undefined' ? globalThis : {};
  const subtle = g.crypto && g.crypto.subtle ? g.crypto.subtle : null;
  if (subtle) {
    const data = new TextEncoder().encode(str);
    const hashBuffer = await subtle.digest('SHA-256', data);
    return Array.from(new Uint8Array(hashBuffer))
      .map((b) => b.toString(16).padStart(2, '0'))
      .join('');
  }
  try {
    const nodeCrypto = require('crypto');
    return nodeCrypto.createHash('sha256').update(str, 'utf8').digest('hex');
  } catch (e) {
    throw new Error(
      'SHA-256 indisponível: nem globalThis.crypto.subtle nem require("crypto") no runner.',
    );
  }
}

/**
 * Corpo HTTP como texto XML. O helper do n8n pode devolver string, { body }, { data } ou Buffer.
 * Buffer/Uint8Array: comum quando json:false e charset binário.
 */
function httpResponseToText(raw) {
  if (raw == null) return '';
  if (typeof raw === 'string') return raw;

  function bytesToUtf8(buf) {
    if (typeof Buffer !== 'undefined' && Buffer.isBuffer && Buffer.isBuffer(buf)) return buf.toString('utf8');
    if (buf instanceof Uint8Array) return new TextDecoder('utf-8').decode(buf);
    if (buf && typeof buf === 'object' && buf.type === 'Buffer' && Array.isArray(buf.data))
      return new TextDecoder('utf-8').decode(new Uint8Array(buf.data));
    return null;
  }

  if (typeof raw === 'object') {
    const payload = raw.body !== undefined ? raw.body : raw.data !== undefined ? raw.data : raw;
    if (typeof payload === 'string') return payload;
    const fromBuf = bytesToUtf8(payload);
    if (fromBuf != null) return fromBuf;
    if (typeof raw.body === 'object' && raw.body != null && typeof raw.body.data === 'string') return raw.body.data;
    if (typeof raw.data === 'string') return raw.data;
  }
  try {
    return JSON.stringify(raw);
  } catch (e) {
    return String(raw);
  }
}

function rssItemLink(block) {
  const m1 = block.match(/<link[^>]*>([^<]+)<\/link>/i);
  if (m1) return m1[1].trim();
  const m2 = block.match(/<guid[^>]*isPermaLink\s*=\s*[\"']true[\"'][^>]*>([^<]+)<\/guid>/i);
  if (m2) return m2[1].trim();
  const m3 = block.match(/<guid[^>]*>([^<]+)<\/guid>/i);
  if (m3 && /^https?:\/\//i.test(m3[1].trim())) return m3[1].trim();
  const m4 = block.match(/<link[^>]+href=[\"']([^\"']+)[\"']/i);
  return m4 ? m4[1].trim() : null;
}

function rssItemPubDate(block) {
  const patterns = [
    /<pubDate>([^<]*)<\/pubDate>/i,
    /<dc:date>([^<]*)<\/dc:date>/i,
    /<a10:updated>([^<]*)<\/a10:updated>/i,
    /<atom:updated>([^<]*)<\/atom:updated>/i,
    /<updated>([^<]*)<\/updated>/i,
  ];
  for (const re of patterns) {
    const m = block.match(re);
    if (m) return m[1].trim();
  }
  return null;
}

function atomEntryLink(block) {
  const a =
    block.match(/<link[^>]+rel=[\"']alternate[\"'][^>]+href=[\"']([^\"']+)[\"']/i) ||
    block.match(/<link[^>]+href=[\"']([^\"']+)[\"'][^>]*rel=[\"']alternate[\"']/i);
  if (a) return a[1].trim();
  const b = block.match(/<link[^>]+href=[\"']([^\"']+)[\"']/i);
  if (b) return b[1].trim();
  const c = block.match(/<link[^>]*>([^<]+)<\/link>/i);
  return c ? c[1].trim() : null;
}

function atomEntryPubDate(block) {
  const m =
    block.match(/<published>([^<]+)<\/published>/i) ||
    block.match(/<updated>([^<]+)<\/updated>/i) ||
    block.match(/<a10:updated>([^<]+)<\/a10:updated>/i);
  return m ? m[1].trim() : null;
}

function parseRssItems(xml, source) {
  const items = [];
  const str = httpResponseToText(xml);
  if (str.includes('<entry')) {
    const re = /<entry[^>]*>([\s\S]*?)<\/entry>/gi;
    let m;
    while ((m = re.exec(str)) !== null) {
      const block = m[1];
      const link = atomEntryLink(block);
      const titleM = block.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
      const title = titleM ? titleM[1].replace(/<!\[CDATA\[|\]\]>/g, '').trim() : '';
      const pubDate = atomEntryPubDate(block);
      if (link && pubDate) items.push({ link, title, pubDate, source });
    }
    return items;
  }
  const re = /<item[^>]*>([\s\S]*?)<\/item>/gi;
  let m;
  while ((m = re.exec(str)) !== null) {
    const block = m[1];
    const link = rssItemLink(block);
    const titleM = block.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
    const title = titleM ? titleM[1].replace(/<!\[CDATA\[|\]\]>/g, '').trim() : '';
    const pubDate = rssItemPubDate(block);
    if (!link || !pubDate) continue;
    items.push({ link, title, pubDate, source });
  }
  return items;
}

/** Hacker News — API oficial Firebase (https://github.com/HackerNews/API) */
async function fetchHackerNewsStories(helpers, hnSource, startMs, endMs) {
  const base = 'https://hacker-news.firebaseio.com/v0';
  const ids = await helpers.httpRequest({
    method: 'GET',
    url: `${base}/newstories.json`,
    headers: { 'User-Agent': 'n8n-tech-intelligence/1.0', Accept: 'application/json' },
    timeout: 60000,
    json: true,
  });
  if (!Array.isArray(ids)) return [];
  const rows = [];
  const maxIds = Math.min(ids.length, 120);
  for (let i = 0; i < maxIds; i++) {
    const id = ids[i];
    try {
      const it = await helpers.httpRequest({
        method: 'GET',
        url: `${base}/item/${id}.json`,
        headers: { 'User-Agent': 'n8n-tech-intelligence/1.0', Accept: 'application/json' },
        timeout: 20000,
        json: true,
      });
      if (!it || it.type !== 'story' || !it.time) continue;
      const t = it.time * 1000;
      if (t < startMs || t > endMs) continue;
      const url = it.url || `https://news.ycombinator.com/item?id=${id}`;
      const title = (it.title || url).replace(/<[^>]+>/g, '').trim();
      const pubDate = new Date(t).toISOString();
      rows.push({ link: url, title, pubDate, source: hnSource });
    } catch (e) {
      continue;
    }
  }
  return rows;
}

async function pushArticle(out, it, start, end) {
  const t = new Date(it.pubDate).getTime();
  if (Number.isNaN(t) || t < start || t > end) return;
  const url = it.link;
  const id = await sha256Hex(url);
  const pd = new Date(it.pubDate);
  const yy = pd.getUTCFullYear();
  const mm = String(pd.getUTCMonth() + 1).padStart(2, '0');
  const dd = String(pd.getUTCDate()).padStart(2, '0');
  const published_date = pd.toISOString().slice(0, 10);
  out.push({
    json: {
      id,
      source: it.source,
      title: it.title || url,
      url,
      published_at: pd.toISOString(),
      summary: '',
      ingested_at: new Date().toISOString(),
      published_date,
      blob_path: `year=${yy}/month=${mm}/day=${dd}/source=${it.source}/${id}.json`,
    },
  });
}

const now = new Date();
const uy = now.getUTCFullYear();
const um = now.getUTCMonth();
const ud = now.getUTCDate();
const yesterdayStart = Date.UTC(uy, um, ud - 1, 0, 0, 0, 0);
const end = Date.UTC(uy, um, ud - 1, 23, 59, 59, 999);
const start = yesterdayStart;

const out = [];
const feedErrors = [];
const feedDebug = [];

for (const f of feeds) {
  const urls = Array.isArray(f.urls) ? f.urls : [];
  if (!urls.length) continue;
  let raw = null;
  let lastErr = null;
  let fetchedUrl = null;
  for (const url of urls) {
    try {
      const reqOpts = {
        method: 'GET',
        url,
        headers: {
          'User-Agent': 'n8n-tech-intelligence/1.0',
          Accept: 'application/rss+xml, application/xml, text/xml, */*',
        },
        timeout: 60000,
        /** CRÍTICO: o default do helper costuma ser json:true — quebra RSS/Atom (XML). */
        json: false,
      };
      if (f.tlsInsecure) reqOpts.rejectUnauthorized = false;
      raw = await httpHelpers.httpRequest(reqOpts);
      fetchedUrl = url;
      lastErr = null;
      break;
    } catch (e) {
      lastErr = e;
    }
  }
  if (lastErr != null && raw == null) {
    const msg = lastErr && lastErr.message ? lastErr.message : String(lastErr);
    feedErrors.push({ source: f.source, error: msg });
    feedDebug.push({ source: f.source, error: msg, urlsTried: urls });
    console.error('INGEST_FEED_FAIL', f.source, msg);
    continue;
  }
  try {
    const text = httpResponseToText(raw);
    const parsed = parseRssItems(raw, f.source);
    let inWindow = 0;
    for (const it of parsed) {
      const t0 = new Date(it.pubDate).getTime();
      if (!Number.isNaN(t0) && t0 >= start && t0 <= end) inWindow++;
      await pushArticle(out, it, start, end);
    }
    feedDebug.push({
      source: f.source,
      url: fetchedUrl,
      bodyChars: text.length,
      parsedItems: parsed.length,
      parsedInWindow: inWindow,
    });
  } catch (e) {
    const msg = e && e.message ? e.message : String(e);
    feedErrors.push({ source: f.source, error: msg });
    feedDebug.push({ source: f.source, error: msg });
    console.error('INGEST_PARSE_FAIL', f.source, msg);
  }
}

try {
  const hnItems = await fetchHackerNewsStories(httpHelpers, 'hackernews', start, end);
  for (const it of hnItems) {
    await pushArticle(out, it, start, end);
  }
} catch (e) {
  const msg = e && e.message ? e.message : String(e);
  feedErrors.push({ source: 'hackernews', error: msg });
  console.error('INGEST_HN_FAIL', msg);
}

if (out.length === 0) {
  const diag = {
    windowStart: new Date(start).toISOString(),
    windowEnd: new Date(end).toISOString(),
    feedErrors,
    feedDebug,
    feedsAttempted: feeds.length,
  };
  const totalParsed = feedDebug.reduce(
    (s, d) => s + (typeof d.parsedItems === 'number' ? d.parsedItems : 0),
    0,
  );
  const hadBigBodies = feedDebug.some((d) => !d.error && (d.bodyChars ?? 0) > 2000);
  const suspiciousTinyBodies =
    feedDebug.length > 0 &&
    feedDebug.every((d) => !d.error && (d.bodyChars ?? 0) < 400);
  if (feedErrors.length > 0 || suspiciousTinyBodies) {
    diag.hint =
      feedErrors.length > 0
        ? 'Exceções HTTP — ver feedErrors.'
        : 'Respostas muito pequenas (<400 chars) em todos os feeds — possível bloqueio, HTML de erro ou formato inesperado.';
    console.error('INGEST_FAIL', JSON.stringify(diag));
    throw new Error(`INGEST_ZERO_ITEMS: ${JSON.stringify(diag)}`);
  }
  if (totalParsed === 0 && hadBigBodies) {
    diag.hint =
      'Corpo grande mas 0 itens extraídos — confirme json:false nos GET RSS (default json:true estraga XML) e formato do feed.';
    console.error('INGEST_ZERO_PARSED', JSON.stringify(diag));
    throw new Error(`INGEST_ZERO_PARSED: ${JSON.stringify(diag)}`);
  }
  diag.hint = 'Feeds OK mas nenhum item com published_at na janela UTC.';
  console.error('INGEST_NO_MATCH_WINDOW', JSON.stringify(diag));
}

return out;
