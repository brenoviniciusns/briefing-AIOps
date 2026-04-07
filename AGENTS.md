# Contexto de agentes — Daily Tech Intelligence → LinkedIn

Este ficheiro existe na **raiz do repositório** para o Cursor (e ferramentas compatíveis) **carregarem o contexto automaticamente** em cada sessão.

**Comportamento atual do pipeline (única referência para drift):** `docs/estado-atual-pipeline.md`. **Runbook:** `docs/runbook.md`. Testes: `docs/TESTING.md`.

**Fonte canónica:** o conteúdo detalhado continua em `agents/` e `mcp/AGENT-MCP-MAP.md`. Ao editar esses ficheiros, **atualiza as secções correspondentes abaixo** (ou mantém este ficheiro como cópia espelhada).

---

## Índice e estrutura (`agents/CONTEXT.md`)

O repositório inclui **estrutura**, **contexto de agentes** e **implementação** (ex.: `function-app/`, workflows n8n exportados em `n8n/workflows/`).

Use este ficheiro como **índice** ao orquestrar trabalho no Cursor ou noutro orquestrador.

### Estrutura de pastas (reservada)

| Pasta | Uso |
|--------|-----|
| `infra/` | IaC (ex.: Bicep, Terraform) |
| `function-app/` | Azure Functions (Python) |
| `n8n/workflows/` | JSON importável dos workflows n8n |
| `schemas/` | Esquemas JSON (RAW, processado, relatório) |
| `examples/` | Exemplos de pedidos/respostas HTTP |
| `docs/` | Documentação operacional / deploy |
| `agents/` | Fluxos (Mermaid), prompts, **perfil LinkedIn** |
| `mcp/` | Política de uso de MCP por agente |
| `.cursor/rules/` | Regras persistentes do Cursor por especialidade |

### Mapa rápido — agentes

| Agente | Especialidade | Fluxo | Prompt | MCP sugerido |
|--------|---------------|--------|--------|----------------|
| Orquestrador | **Janela D-1 UTC**, LinkedIn **3 ganchos + 1 destaque**, anti-repetição, idempotência | `flows/multi-agent-mcp.mmd` | `prompts/00-orchestrator.md` | Postman (contratos), Azure (CLI/portal) |
| Ingestão (n8n) | RSS/HN, filtro **só ontem (UTC)**, RAW | `flows/pipeline.mmd` | `prompts/01-ingestion.md` | n8n MCP (se configurado) |
| Processamento (Functions + OpenAI) | Agregar janela, Delta, LLM, **LinkedIn 3+1**, relatório | `flows/pipeline.mmd` | `prompts/02-processing-llm.md` | context7 (SDKs) |
| Entrega (n8n) | E-mail / Slack com **LinkedIn (3 curtos + 1 detalhe)** + relatório | `flows/pipeline.mmd` | `prompts/03-delivery.md` | Postman / browser (preview HTML) |

### Perfil LinkedIn (ranking)

- Narrativa completa: `agents/audience-profile-linkedin.md`
- Resumo para LLM no deploy: `function-app/shared/linkedin_audience_summary.md`

### Regras Cursor

- Pipeline (sempre aplicável): `.cursor/rules/daily-tech-pipeline.mdc`
- Azure / plataforma: `.cursor/rules/agent-azure-platform.mdc`
- n8n: `.cursor/rules/agent-n8n-orchestrator.mdc`
- Azure Functions Python: `.cursor/rules/agent-python-functions.mdc`

### Fontes de ingestão

Allowlist em `allowlist_rss.yaml` (RSS + **Hacker News** API Firebase). Código do nó: `n8n/snippets/ingestion-fetch-code.js`. HTML e-mail: `n8n/snippets/delivery-email-html.js` (sincronizar com `scripts/update_delivery_workflows.py`).

### Mapa MCP por agente

Ver secção «Mapa agente → MCP» mais abaixo (espelho de `mcp/AGENT-MCP-MAP.md`).

### Azure e role Contributor

Se na subscrição a tua role for **Contributor** (sem Owner / User Access Administrator), o IaC **não deve** incluir atribuições RBAC; acesso da Function ao Storage/OpenAI pode depender de **keys/connection strings** e de um administrador aplicar RBAC à Managed Identity quando a política o permitir. Detalhes: `.cursor/rules/agent-azure-platform.mdc`.

### Credencial HTTP no n8n

No tipo **Header Auth**, o campo **Header Name** deve ser **`x-functions-key`** (token HTTP válido), não uma frase com espaços.

---

## Mapa agente → MCP (`mcp/AGENT-MCP-MAP.md`)

Objetivo: cada agente lógico usa ferramentas MCP de forma **explícita**, sem scraping HTML além do permitido na allowlist (**RSS** + **API JSON** declarada, ex. Hacker News Firebase).

### Orquestrador

- **Postman MCP**: validar `/check-id` e `/process` (`date` + `lookback_days`), guardar exemplos em `examples/`.
- **GitLens / Git**: versão de workflows n8n e Bicep (se usar repositório git).

### Agente de ingestão (n8n)

- **n8n MCP** (se ativo no workspace): importar/exportar workflows em `n8n/workflows/`.
- Evitar browser para fontes; usar apenas RSS e APIs JSON da allowlist (`allowlist_rss.yaml`).

### Agente de processamento (Python + OpenAI)

- **context7**: referência de `openai`, `azure-identity`, `azure-storage-file-datalake`, `deltalake`.
- **Postman MCP**: testes da Function com cabeçalhos e corpos de `examples/`.

### Agente de entrega (n8n)

- **cursor-ide-browser** (se disponível): smoke test do HTML renderizado.
- **Postman MCP**: webhooks Slack simulados (se aplicável).

### Nota

Os servidores MCP efetivos dependem da configuração do Cursor em `mcps/`. Este ficheiro define a **política de uso**, não substitui a lista de servidores ligados.

---

## Prompt — Orquestrador (`agents/prompts/00-orchestrator.md`)

Use este texto como **system** ou **primeira mensagem** ao coordenar os outros agentes.

You are the orchestrator for the **Daily Tech Intelligence → LinkedIn** pipeline on **Azure + n8n + Python Functions**.

Non-negotiables:

1. **Date window**: ingest `published_at` (UTC) on **yesterday’s civil day only**: **`yesterday 00:00:00 UTC`** through **`yesterday 23:59:59.999 UTC`**. Do not use rolling 24h as the definition of the window.
2. **Processing**: `POST /process` with `date` = **yesterday UTC** and `lookback_days` (default **1**).
3. **Idempotency**: article `id` = `SHA256(url)` (hex, lowercase). Call `/check-id` before heavy work. Persist processed ids.
4. **LinkedIn**: **3 short hooks** + **1 deeper topic** (data/platform bias); higher **profile match** → higher `profile_match_score`. Same theme may repeat; **same article id must not** be reused — use persisted featured-id set.
5. **Sources**: only allowlisted **RSS** and **JSON APIs** (`allowlist_rss.yaml`); no HTML scraping unless approved.
6. **Storage**: `/raw/...`, `/processed/` (Delta), `/reports/`.
7. **Security**: secrets via Key Vault / App Settings only; Contributor-only subs: see `.cursor/rules/agent-azure-platform.mdc`.

You assign work to:

- **Ingestion** (n8n): fetch, normalize, **D-1 UTC filter**, dedup, raw upload, trigger `/process`.
- **Processing** (Function): window aggregate, classify, score, summaries, **LinkedIn 3+1**, Delta, report JSON.
- **Delivery** (n8n): email/Slack with **LinkedIn (3+1)** + compact insights.

When uncertain, read `agents/CONTEXT.md` and `docs/schemas.md`.

---

## Prompt — Ingestão (`agents/prompts/01-ingestion.md`)

You are the **ingestion agent** implemented primarily in **n8n**.

Responsibilities:

1. Trigger daily (e.g. 07:00 UTC — document timezone).
2. For each RSS URL: fetch XML, parse. For **Hacker News**, use Firebase API from allowlist.
3. Normalize to RAW shape (`docs/schemas.md`).
4. Filter to **yesterday UTC** only (full civil day). Exclude items without reliable timestamps (default).
5. `id = sha256(url)`; call **`/check-id`**; skip duplicates per policy.
6. Upload RAW under `/raw/year=.../month=.../day=.../source=.../`.
7. Call **`POST /process`** with `{ "date": "<yesterday>", "lookback_days": 1, "archive": false }`.

Resilience: retry with backoff; log feed failures without blocking others.

Workflow: `n8n/workflows/ingestion.json`.

---

## Prompt — Processamento (`agents/prompts/02-processing-llm.md`)

You are the **processing agent**: Azure Functions (Python) plus **Azure OpenAI**.

Endpoints:

- `POST /check-id` — id + source + published_date.
- `POST /process` — `{ "date", "lookback_days": 1, "archive" }`; read RAW for **each day** in the window, dedupe, process, write Delta, emit report with **`linkedin_short_topics`**, **`linkedin_deep_topic`**, mirror **`linkedin_topics`**, and **`llm_insights`**, update **`linkedin-featured-article-ids.json`** for anti-repetition.

(Detalhes completos no ficheiro `agents/prompts/02-processing-llm.md`.)

### Executive analysis (OpenAI)

Short corpus (usually one UTC day): architectural decisions, strategic shifts, patterns, risks. Output JSON: compact `key_insights` (max 3), sparse `trends` / `important_changes` / `actionable_takeaways`.

Code: `function-app/`. Validate against `docs/schemas.md`.

---

## Prompt — Entrega (`agents/prompts/03-delivery.md`)

You are the **delivery agent** in **n8n**.

1. After `/process`, load `daily-report-{date}.json` for the report **`date`** (end of window).
2. Build HTML prioritizing **LinkedIn**: **3 ganchos** (`hook_line` / `topic_label`, scores, links) + **1 tema em destaque** (`linkedin_deep_topic.angle_for_post`), then categories and compact `llm_insights`.
3. Email + optional Slack/Teams. No secrets in JSON — use n8n credentials.

Workflow: `n8n/workflows/delivery.json`.
