# Runbook operacional — Daily Tech Intelligence

Documento único de **exploração em incidentes** e rotinas. Detalhe de deploy: [deployment.md](deployment.md). Estado canónico do produto: [estado-atual-pipeline.md](estado-atual-pipeline.md).

## 1. Onde ver o que se passou

| O quê | Onde |
|-------|------|
| Logs da Function | Portal Azure → Function App → **Monitor** / **Log stream**; ou Application Insights ligado à app |
| Execuções n8n | n8n Cloud / self-hosted → **Executions** do workflow de ingestão ou entrega |
| Blobs RAW / relatórios | Storage Account → contentores `raw`, `reports` (e `processed` para Delta) |
| Erros OpenAI / quota | Portal → recurso Azure OpenAI → **Metrics**; logs da Function |

## 2. Sintomas frequentes

### 401 / Unauthorized na Function

- Cabeçalho **`x-functions-key`** em falta ou errado (credencial HTTP no n8n).
- URL base errada em `FUNCTION_APP_URL` (sem barra final duplicada no path).

### 504 no `POST /api/process`

- **Gateway** do App Service (~**230 s**), não necessariamente timeout interno da Function. Ver [implementacao-azure.md](implementacao-azure.md) secção sobre 504.
- Mitigação: reduzir **`MAX_ARTICLES_PER_RUN`** nas App Settings; menos artigos por execução.

### Ingestão sem itens (0 candidatos)

- **D-1 UTC** sem publicações nos feeds é normal.
- Reprocessar: `POST /api/process` com `date` e opcionalmente `lookback_days` > 1 se existir RAW noutros dias — [api-examples.http](api-examples.http).

### Notion 400 / validação

- Coluna de título com nome errado (`NOTION_DB_TITLE_COLUMN`). Ver [deployment.md](deployment.md) troubleshooting Notion.

## 3. Variáveis n8n (checklist rápido)

`FUNCTION_APP_URL`, `BLOB_BASE_URL`, `BLOB_SAS_TOKEN`, `REPORT_EMAIL_*`, `NOTION_*`, credencial **Header Auth** `x-functions-key`. Lista completa: [deployment.md](deployment.md) §3.

## 4. Segredos e repositório

- **Nunca** tokens reais nos JSON exportados do n8n — usar placeholders `REPLACE_*` e credenciais na instância.
- `.env` com chaves locais: no `.gitignore`; não fazer commit.

## 5. Backup e recuperação (ligeiro)

| Dado | Notas |
|------|--------|
| RAW / Delta / `reports/` | No Storage (redundância conforme conta). **MERGE** Delta por `id` — reprocessar é idempotente. |
| Relatório JSON | `reports/daily-report-YYYY-MM-DD.json`; pode voltar a gerar com `/process` para o mesmo `date` (e janela RAW coerente). |
| Histórico LinkedIn | Blob `linkedin-featured-article-ids.json` — cópia manual se precisares de rollback de “já sugerido”. |

Reprocessar: `POST /api/process` com `{"date":"<YYYY-MM-DD>","lookback_days":N}` conforme partições existentes.

## 6. Monitorização (recomendado)

- **Application Insights**: falhas 5xx, duração de `/process`, dependências.
- **Alertas** (acordar com a equipa): taxa de falha da Function, ou execuções n8n falhadas em sequência.

Checklist de validação T1–T6: [phase-gates-checklist.md](phase-gates-checklist.md).

## 7. Testes antes de alterar contratos

```bash
cd function-app && python -m pytest tests/ -q
```

Inclui validação dos JSON em `examples/`. Ver [TESTING.md](TESTING.md).

## 8. Sincronizar workflows n8n duplicados

```bash
python scripts/sync_n8n_workflows.py
```

Copia `n8n/workflow-*.json` → `n8n/workflows/*.json`.
