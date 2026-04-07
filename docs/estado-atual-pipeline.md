# Estado atual do pipeline — referência única

Documento **canónico** para o comportamento em produção após endurecimento pós-entrega. **Runbook** (incidentes, 504, segredos): [runbook.md](runbook.md). Deploy: [deployment.md](deployment.md). Checklist: [phase-gates-checklist.md](phase-gates-checklist.md). **ADR** principal: [adr/0001-janela-d1-e-relatorio.md](adr/0001-janela-d1-e-relatorio.md).

## Objetivo

Ingerir feeds RSS/APIs aprovados, gravar RAW no ADLS Gen2, processar com **Azure Functions (Python)** + **Azure OpenAI**, emitir relatório JSON e entregar **e-mail** + **Notion** (e Slack opcional) via **n8n**.

## Congelamento de contrato e artefactos (matriz)

Esta matriz substitui checklists antigos: indica **fonte de verdade** e o que ainda é **manual / integração**.

| Área | Fonte de verdade | Automatizado | Ainda manual / futuro |
|------|------------------|--------------|------------------------|
| **HTTP `/check-id`, `/process`, forma do relatório** | `docs/schemas.md` + modelos Pydantic em `function-app/shared/models.py` + `examples/*.json` | `pytest` (`test_contract_examples.py`) valida `examples/`; validação cruzada com `docs/api-examples.http` | Chamadas HTTP reais à Function (Postman/curl) contra ambiente deployado |
| **Comportamento runtime** | Código `function-app/` + workflows n8n exportados | Testes unitários em `function-app/tests/` (sem Azure) | Smoke n8n na instância ([phase-gates-checklist.md](phase-gates-checklist.md)) |
| **Workflows n8n duplicados** | **Canónicos:** `n8n/workflow-ingestion.json`, `n8n/workflow-delivery.json`. **Espelho:** `n8n/workflows/*.json` via `scripts/sync_n8n_workflows.py` | Correr o script após editar os canónicos | Remover o espelho só quando a equipa fixar um único path de importação |
| **AGENTS.md vs `agents/`** | **`AGENTS.md` (raiz):** índice para o Cursor. **`agents/`:** prompts, `CONTEXT.md`, fluxos Mermaid | N/A (papéis distintos) | Fundir num único sítio é opcional; não é requisito de contrato |
| **Runbook / deploy** | **[runbook.md](runbook.md)** (incidentes, 504, segredos, backup ligeiro, testes, sync n8n). **[deployment.md](deployment.md)** (provisionamento) | — | Alertas App Insights: recomendado no runbook; regras no portal não estão versionadas no repo |
| **Versão Git** | Tags `v0.1.0`, `v0.1.1` + histórico em `master`/`main` | — | Política de release da equipa |

## Janela temporal

- **Ingestão:** apenas o **dia civil anterior em UTC** (`published_at` ∈ [D-1 00:00, D-1 23:59:59.999]).
- **`POST /api/process`:** `date` = tipicamente ontem UTC; **`lookback_days` default = 1** (podes subir manualmente para reprocessar mais partições RAW).

## Azure Function

| Rota | Método | Função |
|------|--------|--------|
| `/api/check-id` | GET/POST | Idempotência RAW por `id` + `source` + `published_date` |
| `/api/process` | POST | Lê RAW na janela, Delta, LLM (resumos pt-BR, insights, LinkedIn 3+1), relatório |
| `/api/report` | GET | `?date=YYYY-MM-DD` — JSON do relatório |

Saídas LLM em **português (Brasil)**; artigos trazem **`source`** (identificador do feed). Relatório: `linkedin_short_topics`, `linkedin_deep_topic`, espelho `linkedin_topics`, `llm_insights`, `sections`, `sources`, metadados de janela.

## n8n

- **Canónicos (editar estes primeiro):** `n8n/workflow-ingestion.json`, `n8n/workflow-delivery.json` — são os que deves importar no n8n.
- **Espelho:** `n8n/workflows/ingestion.json`, `n8n/workflows/delivery.json` — atualizar com `python scripts/sync_n8n_workflows.py` após mudanças nos canónicos.
- **Snippets (fonte para colar no Code node se não reimportares o JSON completo):**
  - `n8n/snippets/ingestion-fetch-code.js`
  - `n8n/snippets/delivery-email-html.js`
  - `n8n/snippets/notion-prepare-body.js`
- **Variáveis e credenciais:** ver [deployment.md](deployment.md) (`FUNCTION_APP_URL`, `BLOB_*`, SMTP, Notion, etc.).

## Notion

- Página criada com **blocos** (`notion_children`): títulos, separadores e **links clicáveis** para URLs dos artigos (ver [notion-report-structure.md](notion-report-structure.md)).
- Limite de **100** blocos por criação (API Notion); o gerador limita listagens longas nas categorias.

## Testes automatizados (Python)

Ver [TESTING.md](TESTING.md). Contratos JSON de exemplo: pasta **`examples/`** (validados em pytest). Comando rápido a partir de `function-app/`:

```bash
python -m pytest tests/ -q
```

## Índice de documentação

| Documento | Uso |
|-----------|-----|
| [deployment.md](deployment.md) | Deploy Bicep, Function, n8n, Notion, SMTP |
| [implementacao-azure.md](implementacao-azure.md) | Contexto Azure / RG / nomes de recursos exemplo |
| [schemas.md](schemas.md) | Contratos RAW, Delta, relatório, `/process` |
| [api-examples.http](api-examples.http) | Exemplos HTTP |
| [phase-gates-checklist.md](phase-gates-checklist.md) | Validação T1–T6 |
| [notion-report-structure.md](notion-report-structure.md) | Estrutura Notion vs relatório |
| [runbook.md](runbook.md) | Incidentes, 504, reprocessamento, segredos |
| [adr/0001-janela-d1-e-relatorio.md](adr/0001-janela-d1-e-relatorio.md) | Decisão D-1 + relatório 3+1 |
| `agents/CONTEXT.md`, `AGENTS.md` | Contexto para agentes / Cursor |

## Histórico de planeamento

O ficheiro `.cursor/plans/pipeline_tech_intelligence_42c1892a.plan.md` reflete **decisões antigas** (ex. janelas maiores). Em caso de conflito, **prevalece este documento** e o código atual.

## Versão e Git

Repositório Git na raiz do projeto. Tag de referência pós-entrega: **`v0.1.0`** (commit inicial documentado).

```bash
git describe --tags
```

Para marcar nova versão após mudanças de contrato: `git tag -a v0.2.0 -m "…"`.
