const dbId = ($vars.NOTION_DATABASE_ID || '').trim();
if (!dbId) {
  throw new Error('Variável n8n NOTION_DATABASE_ID em falta (ID da base Notion, UUID com hífenes).');
}
let nameProp = ($vars.NOTION_DB_TITLE_COLUMN || $vars.NOTION_TITLE_PROPERTY || 'Name').trim();
if (nameProp.toLowerCase() === 'linkedin') {
  throw new Error(
    'Variável errada: LinkedIn não é nome de coluna. NOTION_TITLE_PROPERTY / NOTION_DB_TITLE_COLUMN deve ser o nome da coluna Título na base (ex.: Name, Nome, Título). Remove ou corrige no n8n.',
  );
}

const item = $input.first().json;
const title = String(item.subject || `Relatório tech ${item.report_date || ''}`).slice(0, 2000);

function chunks(str, max) {
  const out = [];
  for (let i = 0; i < str.length; i += max) out.push(str.slice(i, i + max));
  return out.length ? out : [''];
}

/** Plain a partir de HTML quando não há notion_children (fallback). */
function htmlToFallbackPlain(html) {
  let t = String(html);
  t = t.replace(/<\/h1>/gi, '\n\n');
  t = t.replace(/<\/h2>/gi, '\n\n');
  t = t.replace(/<\/h3>/gi, '\n\n');
  t = t.replace(/<\/p>/gi, '\n\n');
  t = t.replace(/<br\s*\/?>/gi, '\n');
  t = t.replace(/<\/li>/gi, '\n');
  t = t.replace(/<\/ul>|<\/ol>|<\/div>/gi, '\n\n');
  t = t.replace(/<hr\s*\/?>/gi, '\n\n---\n\n');
  t = t.replace(/<a\s+[^>]*href=["']([^"']+)["'][^>]*>([^<]*)<\/a>/gi, '$2 ($1)');
  t = t.replace(/<[^>]+>/g, '');
  t = t.replace(/&nbsp;/g, ' ');
  t = t.replace(/&amp;/g, '&');
  t = t.replace(/&lt;/g, '<');
  t = t.replace(/&gt;/g, '>');
  t = t.replace(/\n{3,}/g, '\n\n');
  return t.trim();
}

let children;
if (Array.isArray(item.notion_children) && item.notion_children.length > 0) {
  children = item.notion_children.slice(0, 100);
} else {
  let plain = String(item.slack_text || '');
  if (plain.length < 80 && item.html) {
    plain = htmlToFallbackPlain(item.html);
  }
  const parts = chunks(plain, 1900).slice(0, 99);
  children = parts.map((text) => ({
    object: 'block',
    type: 'paragraph',
    paragraph: { rich_text: [{ type: 'text', text: { content: text } }] },
  }));
}

const notion_body = {
  parent: { database_id: dbId },
  properties: {
    [nameProp]: {
      title: [{ type: 'text', text: { content: title } }],
    },
  },
  children,
};

return [{ json: { notion_body } }];
