# Esquemas de dados

Contexto e defaults atuais: [estado-atual-pipeline.md](estado-atual-pipeline.md).

## RAW (ADLS Gen2, contentor `raw`)

Caminho:

`raw/year=YYYY/month=MM/day=DD/source=<source>/<id>.json`

Corpo JSON (um ficheiro por artigo):

| Campo | Tipo | Descrição |
|--------|------|-----------|
| `id` | string (64 hex) | `sha256(url)` minúsculo |
| `source` | string | Identificador curto (`netflix`, `openai`, …) |
| `title` | string | Título do item (RSS ou Hacker News) |
| `url` | string | URL canónica do artigo |
| `published_at` | string (ISO 8601 UTC) | Data/hora de publicação |
| `summary` | string | Resumo/snippet do feed (pode ser vazio) |
| `ingested_at` | string (ISO 8601 UTC) | Momento de ingestão |

## Delta — tabela `articles` (contentor `processed`)

Raiz lógica: `processed/articles/` (Delta Lake).

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | STRING | Chave de idempotência |
| `source` | STRING | Fonte curta |
| `title` | STRING | Título |
| `url` | STRING | URL |
| `published_at` | STRING | ISO 8601 |
| `category` | STRING | `AI`, `Architecture` ou `Data` |
| `score` | INT32 | Relevância heurística 0–100 |
| `summary` | STRING | Resumo gerado por LLM |
| `ingested_at` | STRING | Do RAW ou preenchido na ingestão |
| `processing_run_id` | STRING | UUID da execução de `/process` |

Escrita: **MERGE** por `id` (reprocessamento seguro).

## Relatório diário (contentor `reports`)

Ficheiro: `daily-report-YYYY-MM-DD.json` — o campo `date` é o **último dia da janela de processamento** (em geral **ontem UTC**), não o dia da execução.

**Idioma e proveniência:** textos gerados por LLM (**resumos**, **insights**, **LinkedIn**) em **português do Brasil**. Cada artigo traz `source` (identificador do feed, ex.: `openai`, `databricks`); o relatório inclui também a lista agregada **`sources`**.

Corpo JSON:

```json
{
  "date": "YYYY-MM-DD",
  "lookback_days": 1,
  "window_start": "YYYY-MM-DD",
  "window_end": "YYYY-MM-DD",
  "sections": {
    "AI": [
      {
        "id": "...",
        "title": "...",
        "url": "...",
        "source": "...",
        "score": 0,
        "summary": "..."
      }
    ],
    "Architecture": [],
    "Data": []
  },
  "sources": ["netflix", "openai"],
  "linkedin_short_topics": [
    {
      "rank": 1,
      "topic_label": "Gancho curto",
      "profile_match_score": 92,
      "hook_line": "Uma linha em PT-BR (≤ ~200 caracteres).",
      "angle_for_post": "Igual a hook_line (compatibilidade).",
      "primary_article": {
        "id": "sha256…",
        "title": "…",
        "url": "https://…",
        "source": "identificador do feed (ex.: openai)"
      },
      "extra_articles": []
    }
  ],
  "linkedin_deep_topic": {
    "topic_label": "Tema para post mais longo",
    "profile_match_score": 94,
    "angle_for_post": "3–5 frases PT-BR, mais detalhe técnico.",
    "primary_article": { "id": "sha256…", "title": "…", "url": "https://…", "source": "…" },
    "extra_articles": []
  },
  "llm_insights": {
    "key_insights": [],
    "trends": [],
    "important_changes": [],
    "actionable_takeaways": []
  },
  "processing_run_id": "uuid"
}
```

- **`linkedin_short_topics`**: até **3** ganchos curtos (`hook_line` em PT-BR); `rank` 1 = maior prioridade. **`linkedin_deep_topic`**: um único tema com mais detalhe (`angle_for_post` 3–5 frases). Prioridade editorial: audiência **dados** / plataforma (lakehouse, MLOps, GenAI em produção, Azure/Databricks, governança). Os `id` usados **não devem** repetir entradas já em `linkedin-featured-article-ids.json` (ver abaixo).
- **`linkedin_topics`**: espelho dos **3** ganchos curtos (compatibilidade com consumidores antigos); preferir `linkedin_short_topics` + `linkedin_deep_topic` em novos templates.

## Histórico anti-repetição LinkedIn

- Ficheiro opcional no mesmo contentor: **`linkedin-featured-article-ids.json`**
- Formato: `{ "ids": ["<sha256>", ...] }` — lista de artigos já sugeridos em dias anteriores; o processamento **filtra** esses `id` antes de pedir ao LLM os 3 tópicos e **acrescenta** os novos `id` após sucesso.

Opcionalmente pode existir cópia em `reports/archive/run_id=<uuid>/daily-report-YYYY-MM-DD.json` quando `archive: true` em `/process`.

## Contrato `POST /api/process`

| Campo | Tipo | Obrigatório | Descrição |
|--------|------|-------------|-----------|
| `date` | string `YYYY-MM-DD` | sim | Último dia da janela (tipicamente ontem UTC). |
| `lookback_days` | int | não (default 1) | Número de dias civis inclusivos a ler em RAW, retrocedendo a partir de `date`. |
| `archive` | bool | não | Arquivar cópia do relatório. |
