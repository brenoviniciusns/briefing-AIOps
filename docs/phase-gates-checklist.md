# Runbook — portões de teste entre fases (T1–T6)

Checklist copiável para validar o **Daily Tech Intelligence Pipeline** após deploy ou antes de ir a produção. Alinha-se ao plano em `.cursor/plans/pipeline_tech_intelligence_42c1892a.plan.md` e aos exemplos em [`api-examples.http`](api-examples.http).

**Documentação relacionada:** [`implementacao-azure.md`](implementacao-azure.md), [`deployment.md`](deployment.md), [`rbac-manual.md`](rbac-manual.md), [`schemas.md`](schemas.md).

---

## Ambiente pré-preenchido (SandBox — treinamento insourcing)

Valores obtidos com **Azure CLI** para o RG de desenvolvimento (prefixo **tinsourcing**). A **function key** não fica neste ficheiro: obtê-la com o comando abaixo após `az login`.

| Item | Valor |
|------|--------|
| **Subscrição** | `228613b7-1d35-4504-9c66-de7973af9176` (SandBox) |
| **Resource group** | `rg-treinamento-insourcing-dev` |
| **Região do RG** | `eastus2` |
| **Function App** | `tinsourcing-dev-func-uixu7snhv7bsw` |
| **URL base da Function** | `https://tinsourcing-dev-func-uixu7snhv7bsw.azurewebsites.net` |
| **Storage ADLS Gen2 (pipeline)** | `tinsourcingdevstuixu7snh` (HNS ativo) |
| **Blob service (base URL)** | `https://tinsourcingdevstuixu7snh.blob.core.windows.net` |
| **Key Vault** | `tinsourcing-dev-kv-uixu7` |
| **Azure OpenAI (Cognitive Services)** | `tinsourcing-dev-oai-uixu` |
| **Application Insights** | `tinsourcing-dev-ai-uixu7snhv7bsw` |
| **App Service Plan (Function)** | `tinsourcing-dev-func-uixu7snhv7bsw-plan` |

No mesmo RG existe também a storage `stinsourcing001dev`; o pipeline **Daily Tech Intel** documentado neste repo usa **`tinsourcingdevstuixu7snh`** (contentores `raw`, `processed`, `reports`, `idempotency`, …).

**n8n — variáveis sugeridas (alinhadas ao JSON do workflow):**

| Variável n8n | Valor |
|--------------|--------|
| `FUNCTION_APP_URL` | `https://tinsourcing-dev-func-uixu7snhv7bsw.azurewebsites.net` |
| `BLOB_BASE_URL` | `https://tinsourcingdevstuixu7snh.blob.core.windows.net` (o `blob_path` do workflow já começa por `raw/year=…`, ou seja, contentor **`raw`**) |
| `BLOB_SAS_TOKEN` | token SAS (sem `?`) com permissão de escrita no contentor `raw`; **não** commitar |

---

## Variáveis de sessão (shell)

Ainda precisas de definir **`TEST_DATE`**, **`TEST_ID`** (64 hex de um artigo RAW existente) e carregar **`FUNC_KEY`**.

| Variável | Notas |
|----------|--------|
| `FUNC_KEY` | Host key default: ver comandos abaixo (ou credencial n8n `x-functions-key`) |
| `TEST_DATE` | Data UTC `YYYY-MM-DD` no **fim** da janela (geralmente **ontem**), com RAW nessa partição (D-1) |
| `TEST_ID` | SHA-256 da URL (64 hex minúsculos) de um blob RAW existente para esse dia |

**Descobrir `TEST_DATE` / `TEST_ID` a partir do storage** (contentor `raw`; o nome do blob é `year=YYYY/month=MM/day=DD/source=…/<id>.json`):

- Com **RBAC** no data plane (`Storage Blob Data Reader`, etc.):

```bash
az storage blob list --account-name tinsourcingdevstuixu7snh --container-name raw --auth-mode login --num-results 20 --query "[].name" -o tsv
```

- Se `login` falhar por permissões, perfil **Contributor** costuma conseguir **list keys** (não expor a chave em logs nem colar no Git):

```bash
STKEY="$(az storage account keys list -g rg-treinamento-insourcing-dev -n tinsourcingdevstuixu7snh --query "[0].value" -o tsv)"
az storage blob list --account-name tinsourcingdevstuixu7snh --container-name raw --auth-mode key --account-key "$STKEY" --num-results 20 --query "[].name" -o tsv
```

Extrair `TEST_DATE` do segmento `year=…/month=…/day=…` e `TEST_ID` do ficheiro `<id>.json` (64 caracteres hex antes de `.json`). Alternativa: Portal Azure → Storage → contentores → `raw`.

**bash** (Linux, macOS, Git Bash):

```bash
az account set --subscription 228613b7-1d35-4504-9c66-de7973af9176

export FUNC_HOST="https://tinsourcing-dev-func-uixu7snhv7bsw.azurewebsites.net"
export FUNC_KEY="$(az functionapp keys list -g rg-treinamento-insourcing-dev -n tinsourcing-dev-func-uixu7snhv7bsw --query functionKeys.default -o tsv)"

# Opcional: confirmar recursos
az functionapp show -g rg-treinamento-insourcing-dev -n tinsourcing-dev-func-uixu7snhv7bsw --query "{state:state,host:defaultHostName}" -o json
```

**PowerShell:**

```powershell
az account set --subscription 228613b7-1d35-4504-9c66-de7973af9176

$env:FUNC_HOST = "https://tinsourcing-dev-func-uixu7snhv7bsw.azurewebsites.net"
$env:FUNC_KEY = az functionapp keys list -g rg-treinamento-insourcing-dev -n tinsourcing-dev-func-uixu7snhv7bsw --query functionKeys.default -o tsv

# Nos curls abaixo use: -H "x-functions-key: $env:FUNC_KEY"
```

---

## Testes automatizados (local / CI)

Sem Azure: regras de classificação e modelos Pydantic.

```bash
cd function-app
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest tests -q
```

**Critério:** todos os testes passam (útil antes de cada fase que altere código Python).

---

### Fase 1 — Plataforma e segredos (Azure)

**Objetivo:** RG, storage, contentores, Function publicada, estado saudável.

| # | Ação | Comando / verificação |
|---|------|------------------------|
| 1.1 | Subscrição ativa | `az account show --subscription 228613b7-1d35-4504-9c66-de7973af9176 --query "{name:name,state:state}" -o json` |
| 1.2 | RG existe | `az group show -n rg-treinamento-insourcing-dev --query "{name:name,location:location}" -o json` |
| 1.3 | Function **Running** | `az functionapp show -g rg-treinamento-insourcing-dev -n tinsourcing-dev-func-uixu7snhv7bsw --query "{state:state,httpsOnly:httpsOnly,defaultHostName:defaultHostName}" -o json` |
| 1.4 | Contentores no storage | `az storage container list --account-name tinsourcingdevstuixu7snh --auth-mode login -o table` → confirmar `raw`, `processed`, `reports` (e `idempotency` se usado) |

**Portão T1:** 1.1–1.4 OK.

---

### Fase 2 — API da Function (sem n8n)

**Objetivo:** Contratos HTTP antes de encadear ingestão.

Substituir `TEST_ID` por um id válido de 64 hex; `TEST_DATE` alinhado ao prefixo RAW `year=/month=/day=`.

**check-id (GET)**

```bash
curl -sS -o /tmp/check.json -w "%{http_code}" \
  "$FUNC_HOST/api/check-id?id=TEST_ID&source=openai&published_date=TEST_DATE" \
  -H "x-functions-key: $FUNC_KEY"
```

**check-id (POST)**

```bash
curl -sS -X POST "$FUNC_HOST/api/check-id" \
  -H "Content-Type: application/json" \
  -H "x-functions-key: $FUNC_KEY" \
  -d '{"id":"TEST_ID","source":"openai","published_date":"TEST_DATE"}'
```

**process**

```bash
curl -sS -X POST "$FUNC_HOST/api/process" \
  -H "Content-Type: application/json" \
  -H "x-functions-key: $FUNC_KEY" \
  -d '{"date":"TEST_DATE","archive":false}'
```

**report** (após `process` com sucesso para essa data)

```bash
curl -sS "$FUNC_HOST/api/report?date=TEST_DATE" \
  -H "x-functions-key: $FUNC_KEY"
```

**PowerShell** (definir `$env:FUNC_HOST` e `$env:FUNC_KEY` como acima; substituir `TEST_DATE`):

```powershell
$date = "2026-04-05"   # TEST_DATE
Invoke-RestMethod -Uri "$($env:FUNC_HOST)/api/check-id?id=TEST_ID&source=openai&published_date=$date" -Headers @{"x-functions-key"=$env:FUNC_KEY}
Invoke-RestMethod -Uri "$($env:FUNC_HOST)/api/process" -Method POST -ContentType "application/json" -Headers @{"x-functions-key"=$env:FUNC_KEY} -Body '{"date":"' + $date + '","archive":false}'
Invoke-RestMethod -Uri "$($env:FUNC_HOST)/api/report?date=$date" -Headers @{"x-functions-key"=$env:FUNC_KEY}
```

**Portão T2:**

- `check-id` → HTTP `200`, corpo JSON com `exists` (boolean) e `id`.
- `process` → HTTP `200`, `ok: true`, `processed_count` número (pode ser `0` se não houver RAW válido para `TEST_DATE`, mas **não** 5xx por configuração).
- `report` → `200` com JSON de relatório **ou** `404` se ainda não existir ficheiro para essa data (aceitável só **antes** do primeiro process bem-sucedido).

---

### Fase 3 — Ingestão n8n → ADLS → Function

**Objetivo:** Workflow **Daily Tech Intel — Ingestão** ativo; variáveis e credenciais corretas.

Checklist manual (n8n UI ou API):

| # | Verificação |
|---|-------------|
| 3.1 | Workflow de ingestão **ativo**; cron 07:00 UTC (ou equivalente documentado). |
| 3.2 | Variáveis n8n: `FUNCTION_APP_URL` = `https://tinsourcing-dev-func-uixu7snhv7bsw.azurewebsites.net`; `BLOB_BASE_URL` = `https://tinsourcingdevstuixu7snh.blob.core.windows.net`; `BLOB_SAS_TOKEN` = SAS do contentor `raw` (sem `?`). |
| 3.3 | Credencial HTTP com `x-functions-key` da Function `tinsourcing-dev-func-uixu7snhv7bsw` (a mesma key usada em T2). |
| 3.4 | URL final do PUT: `{BLOB_BASE_URL}/{blob_path}?{BLOB_SAS_TOKEN}` com `blob_path` = `raw/year=…/month=…/day=…/source=…/{id}.json` (primeiro segmento = nome do contentor **`raw`**). |

**Portão T3:**

- Após execução (manual ou agendada), existe pelo menos um blob em  
  `raw/year=YYYY/month=MM/day=DD/source=<fonte>/<id>.json` para um dia onde os feeds tenham itens em D-1 UTC **ou** após upload de teste.
- Reexecução: para o mesmo artigo, `check-id` deve devolver `exists: true` e o fluxo não deve recriar RAW indevidamente.

---

### Fase 4 — Processamento (OpenAI + Delta + relatório)

**Objetivo:** MERGE Delta idempotente e relatório em `reports/`.

| # | Ação |
|---|------|
| 4.1 | Com RAW na janela, `POST /api/process` com `{"date":"TEST_DATE","lookback_days":1}` → `processed_count > 0` (se houver artigos parseáveis). |
| 4.2 | Confirmar blob no contentor **reports** (nome padrão `daily-report-TEST_DATE.json`; contentor configurável por `ADLS_CONTAINER_REPORTS`). Ver [`schemas.md`](schemas.md). |
| 4.3 | Repetir `POST /api/process` com a mesma `date` → sem duplicar linhas por `id` na tabela Delta; resposta `ok: true`. |

**Portão T4:** 4.1–4.3 OK.

---

### Fase 5 — Entrega n8n (email / Slack)

**Objetivo:** Workflow de entrega importado e configurado.

| # | Verificação |
|---|-------------|
| 5.1 | Workflow **Daily Tech Intel — Entrega** presente e ativo (cron sugerido 07:30 UTC ou após duração do `/process`). |
| 5.2 | `GET /api/report?date=<fim da janela>` com a mesma key → `200` num dia já processado; corpo inclui `linkedin_short_topics` / `linkedin_deep_topic` (e `linkedin_topics` espelho) quando gerado. |
| 5.3 | Credencial SMTP (ou provedor) e `REPORT_EMAIL_TO` (ou equivalente) definidos. |
| 5.4 | Execução de teste: email recebido **ou** execução sem erro no nó de envio (conforme política). |
| 5.5 | Slack: opcional — ativar nó e definir `SLACK_WEBHOOK_URL`; testar com webhook de staging. |

**Portão T5:** 5.2 + 5.4 OK (e 5.5 se Slack estiver no âmbito).

---

### Fase 6 — Robustez, observabilidade e contratos (opcional / contínuo)

**Objetivo:** Fechar lacunas de produção.

| # | Tema | Verificação sugerida |
|---|------|----------------------|
| 6.1 | Retries n8n | HTTP Request: retry/backoff em feeds e chamadas à Function. |
| 6.2 | RSS | Parser tolerante; feeds que falham não bloqueiam os outros; logs revistos. |
| 6.3 | Schemas | Pasta `schemas/` + validação de payloads (CI ou script) quando existir. |
| 6.4 | App Insights | Falhas e latência de `/process` visíveis; alertas acordados com a equipa. |
| 6.5 | RBAC / MI | Se `useManagedIdentityDataPlane: true`, roles aplicadas conforme [`rbac-manual.md`](rbac-manual.md). |

**Portão T6:** critérios acordados com a equipa (ex.: 6.1 + 6.4 mínimos).

---

## Ordem recomendada

1. Testes pytest (`function-app/tests`).
2. **T1** → **T2** → configurar n8n ingestão → **T3** → **T4** → importar entrega → **T5** → **T6** em iterações.

---

## Registo de execução (copiar para ticket / email)

| Data | Responsável | T1 | T2 | T3 | T4 | T5 | T6 | Notas |
|------|-------------|----|----|----|----|----|-----|-------|
| | | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
