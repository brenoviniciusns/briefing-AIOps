# Contexto multi-agente — Daily Tech Intelligence → LinkedIn

Este repositório contém **estrutura**, **contexto dos agentes** e **implementação parcial** (ex.: Azure Functions, workflows n8n exportados). Use este ficheiro como **índice** ao orquestrar trabalho no Cursor.

**Estado operacional do pipeline:** `docs/estado-atual-pipeline.md`.

**Cursor:** o ficheiro **`AGENTS.md`** na raiz espelha índice, mapa MCP e prompts. Ao alterares prompts ou o mapa MCP, atualiza também `AGENTS.md`.

## Estrutura de pastas (reservada)

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
| `.cursor/rules/` | Regras persistentes do Cursor |

## Mapa rápido — agentes

| Agente | Especialidade | Fluxo | Prompt | MCP sugerido |
|--------|---------------|--------|--------|----------------|
| Orquestrador | Pipeline ponta a ponta, **janela D-1 UTC**, LinkedIn **3+1**, idempotência | `flows/multi-agent-mcp.mmd` | `prompts/00-orchestrator.md` | Postman, Azure |
| Ingestão (n8n) | RSS/HN, filtro **só ontem (UTC)**, RAW | `flows/pipeline.mmd` | `prompts/01-ingestion.md` | n8n MCP |
| Processamento (Functions + OpenAI) | Agregar janela, Delta, LLM, **LinkedIn 3+1**, relatório | `flows/pipeline.mmd` | `prompts/02-processing-llm.md` | context7 |
| Entrega (n8n) | E-mail / Slack com **LinkedIn 3 ganchos + 1 destaque** + relatório | `flows/pipeline.mmd` | `prompts/03-delivery.md` | Postman / browser |

## Perfil para ranking LinkedIn

- **`agents/audience-profile-linkedin.md`** — narrativa completa (Breno Paiva / Vale / Azure / Databricks / MLOps…).
- **`function-app/shared/linkedin_audience_summary.md`** — resumo injetado no LLM em deploy.

## Regras Cursor

- Pipeline: `.cursor/rules/daily-tech-pipeline.mdc`
- Azure: `.cursor/rules/agent-azure-platform.mdc`
- n8n: `.cursor/rules/agent-n8n-orchestrator.mdc`
- Functions Python: `.cursor/rules/agent-python-functions.mdc`

## Fontes de ingestão

Allowlist: `allowlist_rss.yaml`. Código do nó n8n: `n8n/snippets/ingestion-fetch-code.js`.

## Mapa MCP por agente

Ver `mcp/AGENT-MCP-MAP.md`.

## Azure e role Contributor

Ver `.cursor/rules/agent-azure-platform.mdc`.
