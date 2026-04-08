# Implementação na Azure — treinamento insourcing (dev)

Comportamento atual do pipeline (janela D-1, contratos): [estado-atual-pipeline.md](estado-atual-pipeline.md).

Este guia junta o que precisas de fazer para colocar o **Daily Tech Intelligence Pipeline** a correr, usando o **resource group existente** e a **subscrição** indicadas.

## Dados fixos do teu ambiente

| Item | Valor |
|------|--------|
| **Subscription ID** | `228613b7-1d35-4504-9c66-de7973af9176` |
| **Resource group** | `rg-treinamento-insourcing-dev` |
| **Criar RG novo?** | Não — o deploy Bicep só referencia o RG existente. |
| **Prefixo dos recursos Azure** | `tinsourcing` + sufixo único (gerado pelo Bicep com `uniqueString`). O nome lógico segue o padrão `tinsourcing-dev-<tipo>-<sufixo>`. |

**Nota sobre o prefixo:** o ficheiro de parâmetros usa `tinsourcing` **sem hífens** porque a **Storage Account** só aceita letras minúsculas e números (3–24 caracteres). Outros recursos (Function App, Key Vault, OpenAI) usam o mesmo `projectPrefix` no template.

**Região (`location`):** o ficheiro [`infra/bicep/main.parameters.rg-treinamento-insourcing-dev.json`](../infra/bicep/main.parameters.rg-treinamento-insourcing-dev.json) está com `eastus` por defeito. **Deves alterá-lo** para a mesma região do teu RG (recomendado):

```bash
az account set --subscription 228613b7-1d35-4504-9c66-de7973af9176
az group show -n rg-treinamento-insourcing-dev --query location -o tsv
```

Copia o resultado (ex.: `brazilsouth`) para o parâmetro `location` no JSON acima **antes** do deploy.

---

## 1. Pré-requisitos na tua máquina

- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) (`az login`)
- Bicep via `az bicep version` (ou `az bicep install`)
- [Azure Functions Core Tools v4](https://learn.microsoft.com/azure/azure-functions/functions-run-local)
- Python **3.11** (para empacotar/testar a Function localmente)
- Instância **n8n** (credenciais e variáveis configuradas fora do Git)

---

## 2. Permissões na subscrição

- Para **criar** Storage, Key Vault, OpenAI, Function App e Application Insights no RG: normalmente **Contributor** no RG (ou na subscrição) é suficiente.
- Para **criar atribuições RBAC** a partir do Bicep (`deployRbacAssignments: true`): é necessário **Owner** ou **User Access Administrator** (ou permissão explícita para `roleAssignments`). Caso contrário, mantém `deployRbacAssignments: false` e segue a **opção B** em [rbac-manual.md](rbac-manual.md).
- **Modo Managed Identity no código** (`useManagedIdentityDataPlane: true`): as App Settings deixam de expor `STORAGE_ACCOUNT_KEY` / `OPENAI_API_KEY`; a Function usa Azure AD. Só faz sentido **depois** das roles estarem aplicadas (Bicep ou CLI). Ver [rbac-manual.md](rbac-manual.md) para a ordem em dois passos.
?- **Key Vault** com autorização RBAC: pode ser preciso um admin dar-te permissão para criar/ler secrets, conforme a política da organização.

---

## 3. Deploy da infraestrutura (Bicep)

1. Seleciona a subscrição:

   ```bash
   az account set --subscription 228613b7-1d35-4504-9c66-de7973af9176
   ```

2. **Preferir** [`main.resourceGroup.bicep`](../infra/bicep/main.resourceGroup.bicep) + [`main.parameters.rg-scope.treinamento.json`](../infra/bicep/main.parameters.rg-scope.treinamento.json): deploy **no RG** `rg-treinamento-insourcing-dev`. Muitos perfis têm Contributor no RG mas **não** permissão para `deployments/write` na **subscrição** (o `main.bicep` ao nível da subscrição devolve 403).

3. Ajusta `location` no JSON RG-scope à região do RG (ex.: `eastus2`).

4. **Plano da Function:** o template usa **Elastic Premium EP1** (Linux). O plano **Consumption** é frequentemente bloqueado em sandboxes (`LinuxDynamicWorkersNotAllowedInResourceGroup`). EP1 tem **custo** contínuo — rever na folha Azure.

5. **Modelo OpenAI:** usar versão suportada (ex.: `gpt-4o` + `2024-11-20`); versões antigas podem falhar com `ServiceModelDeprecated`.

6. **Azure CLI:** se `az deployment group create` falhar com `The content for this response was already consumed`, compila e usa o script REST:

   ```bash
   cd infra/bicep
   az bicep build --file main.resourceGroup.bicep
   python ../../scripts/deploy-resource-group-arm.py 228613b7-1d35-4504-9c66-de7973af9176 rg-treinamento-insourcing-dev NOME-DO-DEPLOY main.resourceGroup.json main.parameters.rg-scope.treinamento.json
   ```

7. **Parâmetros opcionais** nos JSON: `deployRbacAssignments`, `useManagedIdentityDataPlane` — ver [rbac-manual.md](rbac-manual.md).

8. **Outputs:** Portal → RG → Deployments, ou `az deployment group show -g rg-treinamento-insourcing-dev -n <nome> --query properties.outputs`.

9. **Chaves** (obter com CLI se necessário):

   ```bash
   az storage account list -g rg-treinamento-insourcing-dev -o table
   az storage account show-connection-string -g rg-treinamento-insourcing-dev -n <STORAGE_NAME> --query connectionString -o tsv

   az cognitiveservices account list -g rg-treinamento-insourcing-dev -o table
   az cognitiveservices account keys list -g rg-treinamento-insourcing-dev -n <OPENAI_ACCOUNT_NAME> --query key1 -o tsv
   ```

10. **OPENAI_ENDPOINT:** se o output tiver `https://https://...`, corrige na Function App (foi corrigido no módulo `openai.bicep` para deploys futuros).

---

## 4. Publicar o código da Function App (Python)

1. Na saída do deploy, anota o **`functionAppName`**.

2. No repositório:

   ```bash
   cd function-app
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   func azure functionapp publish <functionAppName> --python
   ```

3. Confirma nas **Configuration** da Function App que existem `STORAGE_ACCOUNT_NAME`, `STORAGE_ACCOUNT_KEY`, `OPENAI_*`, contentores `raw`, `processed`, `reports` (criados pelo Bicep).

4. Obtém a **function key** para o n8n:

   ```bash
   az functionapp keys list -g rg-treinamento-insourcing-dev -n <functionAppName>
   ```

   Ou por função:

   ```bash
   az functionapp function keys list -g rg-treinamento-insourcing-dev -n <functionAppName> --function-name check_id
   ```

---

## 5. Storage — SAS para o n8n (upload RAW)

O workflow de ingestão faz **PUT** no blob com SAS.

1. Gera um SAS com escrita no contentor **`raw`** (princípio do menor privilégio, data de expiração definida).

2. Define nas variáveis do n8n (ver [deployment.md](deployment.md)):

   - `BLOB_BASE_URL` = `https://<storage>.blob.core.windows.net` (**sem** `/raw`). O workflow monta o URL como `{BLOB_BASE_URL}/raw/{blob_path}` com `blob_path` = `year=…/month=…/day=…/source=…/{id}.json` (caminho **dentro** do contentor `raw`).
   - `BLOB_SAS_TOKEN` = token **sem** `?` no início

---

## 6. n8n

1. Importa [`n8n/workflow-ingestion.json`](../n8n/workflow-ingestion.json) e [`n8n/workflow-delivery.json`](../n8n/workflow-delivery.json) (ou cópias em [`n8n/workflows/`](../n8n/workflows/)).

2. Cria credencial **HTTP Header** com `x-functions-key` = chave obtida acima.

3. Substitui nos JSON os `REPLACE_ME` dos IDs de credencial **depois** de importar (o n8n pode regerar IDs — associa a credencial correta a cada nó).

4. Variáveis (`$vars`): `FUNCTION_APP_URL`, `BLOB_BASE_URL`, `BLOB_SAS_TOKEN`, `REPORT_EMAIL_TO` (e `SLACK_WEBHOOK_URL` se ativares o nó Slack).

5. **D-1 sem candidatos:** se não houver itens publicados em ontem (UTC), o ramo final do Split pode não correr; executa manualmente `POST /api/process` com `date` + `lookback_days` — ver [api-examples.http](api-examples.http).

---

## 7. Key Vault (opcional nesta fase)

O Bicep cria o Key Vault; **não** grava segredos automaticamente. Podes, mais tarde, mover connection strings e keys para o KV e referenciar nas App Settings — coordena com o administrador se o KV usar RBAC.

---

## 8. Erro **504 Gateway Timeout** no `POST /api/process`

O n8n pode ter timeout de **10 minutos**, o `host.json` pode ter `functionTimeout` de **10 minutos**, mas o **proxy HTTP do Azure App Service** mantém um limite de pedido da ordem de **230 segundos**. Se `/process` demorar mais (muitos artigos × resumo LLM por artigo + brief + LinkedIn), o cliente recebe **504** e o n8n falha — **mesmo com a Function ainda a correr ou a ser terminada** consoante o comportamento da plataforma.

**Mitigação imediata (sem alterar código):** na Function App → **Configuration** → **Application settings**, adiciona ou ajusta:

- `MAX_ARTICLES_PER_RUN` = `25` a `40` (experimenta até o `/process` completar em **menos de ~3 minutos** de ponta a ponta).

Guarda e **reinicia** a app. Volta a publicar o código se já tiveres o default novo no repositório.

**Mitigação estrutural:** fila + função disparada por queue, ou Durable Functions, para processar centenas de artigos sem um único HTTP longo.

---

## 9. Verificação rápida das APIs

Com a URL da Function e a key, testa (ajusta datas e id):

- `GET .../api/check-id?...`
- `POST .../api/process` com `{ "date": "YYYY-MM-DD" }`
- `GET .../api/report?date=YYYY-MM-DD`

Exemplos completos: [api-examples.http](api-examples.http).

### Como saber se o processamento até ao Azure OpenAI está OK

O `/process` chama o OpenAI para **resumir cada artigo** (até `MAX_ARTICLES_PER_RUN`), depois para o **brief executivo** (`llm_insights`, compacto) e para o **bundle LinkedIn** (`linkedin_short_topics` + `linkedin_deep_topic`; `linkedin_topics` espelha os 3 curtos). Se falhar de forma irrecuperável, costuma devolver **500** com `error` no JSON; **504** costuma ser timeout do gateway (ver secção 8), não necessariamente falha do OpenAI.

1. **Resposta do `POST /api/process`** (200): corpo com `"ok": true`, `processed_count` > 0 e `report_path` preenchido — indica que a função chegou a gravar o relatório (passo posterior ao Delta e às chamadas LLM principais).
2. **`GET /api/report?date=YYYY-MM-DD`** (200): abre o JSON e confere:
   - **`llm_insights`**: objeto com listas tipo `key_insights`, `trends`, etc. (se estiver vazio ou só texto mínimo, pode ter havido falha ou corpus muito pequeno).
   - **`linkedin_short_topics`**: até 3 ganchos; **`linkedin_deep_topic`**: objeto com texto mais longo (quando o modelo gera JSON válido).
3. **Blob no contentor `reports`**: ficheiro `daily-report-{date}.json` (ver [schemas.md](schemas.md)) — confirma persistência do mesmo conteúdo.
4. **Portal Azure → recurso OpenAI** (`tinsourcing-dev-oai-uixu` ou o nome do teu deploy): **Metrics** (ex.: pedidos ao modelo) com atividade no intervalo da execução — confirma tráfego ao serviço.
5. **Application Insights** ligado à Function: procurar traces/exceções na execução; mensagens de log ou exceções com `OpenAI`, `chat.completions`, ou `Falha ao resumir artigo`.

Se `processed_count` > 0 e o Delta tem linhas mas **`llm_insights` está vazio** e **`linkedin_short_topics` é `[]`**, investiga quotas, `OPENAI_ENDPOINT` / `OPENAI_DEPLOYMENT_NAME`, ou erros nas logs (o código pode continuar com fallbacks parciais consoante o ponto de falha).

---

## 10. Ficheiros de referência no repositório

| Ficheiro | Uso |
|----------|-----|
| [`infra/bicep/main.parameters.rg-treinamento-insourcing-dev.json`](../infra/bicep/main.parameters.rg-treinamento-insourcing-dev.json) | Parâmetros para **este** RG e prefixo `tinsourcing` |
| [`infra/bicep/main.bicep`](../infra/bicep/main.bicep) | Template principal |
| [`docs/deployment.md`](deployment.md) | Deploy genérico e variáveis n8n |
| [`docs/rbac-manual.md`](rbac-manual.md) | RBAC manual para MI |
| [`docs/schemas.md`](schemas.md) | Formatos RAW / Delta / relatório |

---

## Resumo da ordem recomendada

1. Ajustar `location` no ficheiro de parâmetros.  
2. `az account set --subscription 228613b7-1d35-4504-9c66-de7973af9176`  
3. `az deployment sub create` com `@main.parameters.rg-treinamento-insourcing-dev.json`  
4. Corrigir eventual falha de modelo/quota OpenAI.  
5. `func azure functionapp publish`  
6. Definir `MAX_ARTICLES_PER_RUN` (ex.: 35) nas App Settings se vires **504** no `/process` — ver secção 8.  
7. Gerar SAS e configurar n8n + SMTP.  
8. Testar `/api/check-id`, ingestão n8n, `/api/process`, `/api/report` e email.

Se quiseres que o **prefixo literal** seja outro (mantendo regras da storage), altera só `projectPrefix` no mesmo ficheiro JSON e volta a fazer o deploy — **atenção:** nomes já criados não mudam sem novo deploy / recursos novos.
