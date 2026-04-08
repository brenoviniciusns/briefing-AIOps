# Deploy — Daily Tech Intelligence Pipeline

Comportamento e contratos **atuais** (janela D-1, relatório, n8n): **[estado-atual-pipeline.md](estado-atual-pipeline.md)**. **Runbook** (504, logs, reprocessar): **[runbook.md](runbook.md)**. Testes: **[TESTING.md](TESTING.md)**.

## Pré-requisitos

- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) autenticado (`az login`)
- [Bicep CLI](https://learn.microsoft.com/azure/azure-resource-manager/bicep/install) (integrado no `az bicep`)
- [Azure Functions Core Tools v4](https://learn.microsoft.com/azure/azure-functions/functions-run-local)
- Python 3.11 (local, para testes)
- Instância **n8n** (self-hosted ou cloud) com credenciais configuradas **fora** dos JSON de workflow

## 1. Deploy da infraestrutura (Bicep)

Na raiz do repositório:

```bash
cd infra/bicep
az deployment sub create \
  --location eastus \
  --template-file main.bicep \
  --parameters projectPrefix=techintel environment=dev location=eastus \
  --parameters openAiDeploymentName=gpt-4o openAiModelName=gpt-4o openAiModelVersion=2024-08-06
```

Se o resource group já existir:

```bash
az deployment sub create \
  --location eastus \
  --template-file main.bicep \
  --parameters createResourceGroup=false resourceGroupName=meu-rg-existente ...
```

Parâmetros opcionais no template:

- `deployRbacAssignments` — `true` para criar roles MI → Storage, Key Vault e OpenAI (deploy tem de ser feito por **Owner** ou **User Access Administrator**).
- `useManagedIdentityDataPlane` — `true` para omitir `STORAGE_ACCOUNT_KEY` e `OPENAI_API_KEY` nas App Settings e usar Azure AD no código. Ver [rbac-manual.md](rbac-manual.md) para ordem de deploy segura.

### Outputs úteis

```bash
az deployment sub show --name <nome-do-deployment> --query properties.outputs
```

Anote: `functionAppName`, `functionAppUrl`, `storageAccountName`, `openAiEndpoint`, `keyVaultName`.

### Chaves (não estão nos outputs por segurança)

```bash
# Storage connection string
az storage account show-connection-string \
  -g <RG> -n <STORAGE_ACCOUNT_NAME> --query connectionString -o tsv

# OpenAI key
az cognitiveservices account keys list -g <RG> -n <OPENAI_ACCOUNT_NAME> --query key1 -o tsv
```

Opcional: gravar segredos no Key Vault (com permissões adequadas):

```bash
az keyvault secret set --vault-name <KV> --name "storage-connection-string" --value "<connection_string>"
az keyvault secret set --vault-name <KV> --name "openai-api-key" --value "<key>"
```

## 2. Deploy do código da Function App (Python)

```bash
cd function-app
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
func azure functionapp publish <functionAppName> --python
```

Confirme nas App Settings do portal (ou Bicep) que existem: `STORAGE_ACCOUNT_NAME`, `STORAGE_ACCOUNT_KEY`, `OPENAI_*`, contentores `raw`, `processed`, `reports`.

### Chave de função (n8n / testes)

```bash
az functionapp function keys list -g <RG> -n <functionAppName> --function-name check_id
```

Ou no Portal: Function App → App keys → **default** host key.

Use o header `x-functions-key` ou query `?code=` nas chamadas HTTP.

## 3. n8n

1. Importar [`n8n/workflow-ingestion.json`](../n8n/workflow-ingestion.json) e [`n8n/workflow-delivery.json`](../n8n/workflow-delivery.json).
2. Criar credenciais:
   - **HTTP Header Auth**: cabeçalho `x-functions-key` com a function key (host default ou por função)
   - SMTP (ou outro canal) para o nó de email na entrega
3. **Variáveis** (n8n Variables / ambiente), usadas como `$vars.*` nos fluxos:
   - `FUNCTION_APP_URL` — URL sem barra final (ex.: `https://<functionAppName>.azurewebsites.net`)
   - `BLOB_BASE_URL` — `https://<storage>.blob.core.windows.net` (sem `/raw`). O nó de PUT concatena `{BLOB_BASE_URL}/raw/{blob_path}` com `blob_path` = `year=…/month=…/day=…/source=…/{id}.json`.
   - `BLOB_SAS_TOKEN` — SAS de escrita no contentor `raw` (sem `?` inicial)
   - `REPORT_EMAIL_FROM` — remetente (deve coincidir com a conta SMTP autenticada, ex. `user@domain.com`)
   - `REPORT_EMAIL_TO` — destinatário do relatório
   - `NOTION_TOKEN` — secret da integração Notion (valor **sem** o prefixo `Bearer `); marcar como sensível no n8n
   - `NOTION_DATABASE_ID` — UUID da base de dados (URL da base em Notion)
   - `NOTION_DB_TITLE_COLUMN` — opcional (nome mais claro); **nome exato da coluna Título** na base Notion (`Name`, `Nome`, `Título`, …). **Não** uses `LinkedIn` — isso não é coluna; o assunto do email já contém “LinkedIn” no texto.
   - `NOTION_TITLE_PROPERTY` — igual ao anterior (alias suportado pelo workflow); se definires `NOTION_DB_TITLE_COLUMN`, ele tem prioridade
   - `SLACK_WEBHOOK_URL` — opcional; ativar o nó Slack no workflow de entrega

Substituir `REPLACE_ME` nos JSON importados pelos IDs reais das credenciais no n8n.

#### SMTP Microsoft 365 / Outlook (erro `451 5.7.3 STARTTLS is required`)

O servidor exige **STARTTLS** na porta **587**. Na credencial **SMTP** do n8n:

- **Host:** `smtp.office365.com` (ou o que a tua org indicar)
- **Port:** `587`
- **SSL/TLS:** **desligado** (encriptação explícita via STARTTLS, conforme [documentação n8n](https://docs.n8n.io/integrations/builtin/credentials/sendemail/))
- **Disable STARTTLS:** **desligado** (se estiver ligado, o cliente não faz upgrade TLS e o Exchange devolve 451)

Alternativa: porta **465** com **SSL/TLS ligado** (encriptação implícita).

O nó **Enviar email** (v2.1) usa **From Email** / **To Email**; o JSON exportado já traz `REPORT_EMAIL_FROM` e `REPORT_EMAIL_TO`.

#### Notion (página diária na base) — passo a passo

A API do Notion **só** cria páginas dentro de uma **base de dados** (`database`) à qual a tua **integração** tem permissão. Sem isto, o n8n devolve erros como `object_not_found` ou `unauthorized`.

##### A. Criar a integração (obter `NOTION_TOKEN`)

1. Abre **[notion.so/my-integrations](https://www.notion.so/my-integrations)** (com a mesma conta onde vais guardar a base).
2. Clica em **+ New integration** (ou **Criar nova integração**).
3. Dá um nome, por exemplo `n8n Tech Intel`, e escolhe o **workspace** correto.
4. Em **Type**, mantém **Internal** (integração interna).
5. Grava (**Submit** / **Guardar**).
6. No ecrã da integração, em **Secrets**, copia o valor **Internal Integration Secret** (começa por `secret_...`).
7. No n8n, cria a variável **`NOTION_TOKEN`** com **apenas** esse valor (sem a palavra `Bearer` e sem espaços a mais). Marca como **sensível** se o teu plano n8n permitir.

**Importante:** escolhe integração do tipo **Internal**. O formulário **OAuth** (com *Redirect URIs*) **não** é necessário para este pipeline.

##### A1. Já guardaste `NOTION_TOKEN` — faz **nesta ordem**

1. **Cria uma base** (secção B abaixo) ou abre uma base existente com coluna **Title** / **Nome** / **Título**.
2. **Liga a integração à base** (secção D) — sem isto a API falha sempre.
3. Com a base aberta em **página completa**, copia o **URL da barra de endereço**.
4. Obtém o UUID:
   - **Windows (PowerShell)** na raiz do repo:  
     `.\scripts\notion-id-from-url.ps1 "COLA_O_URL_AQUI"`  
     O script imprime `NOTION_DATABASE_ID=...` — copia só o valor (com hífenes).
   - **À mão:** localiza os **32 caracteres hex** no URL e formata como `8-4-4-4-12` com hífenes (secção C).
5. No **n8n → Variables**, cria **`NOTION_DATABASE_ID`** com esse UUID.
6. Se a coluna de título **não** se chama exatamente **`Name`**, cria **`NOTION_DB_TITLE_COLUMN`** (ou `NOTION_TITLE_PROPERTY`) com o nome **igual** ao cabeçalho (ex.: `Nome`). **Nunca** `LinkedIn`.
7. **Reimporta** [`n8n/workflow-delivery.json`](../n8n/workflow-delivery.json) (ou confirma que tens os nós **Preparar corpo Notion** e **Notion — criar página** ligados após **HTML email + texto Slack**).
8. **Executa** o workflow de entrega manualmente (ou espera o cron) e verifica na base uma **nova linha** com o título `Relatório tech + LinkedIn …` (assunto do e-mail).

##### B. Criar uma base de dados adequada ao workflow

O workflow envia um `POST /v1/pages` com:

- `parent.database_id` = a tua base;
- `properties.<NOME_DA_COLUNA_TITLE>` = título da linha (ex.: `Relatório tech + LinkedIn 2026-04-06`);
- `children` = blocos de texto (parágrafos) com o corpo do relatório em texto simples.

Por isso a base precisa de **pelo menos uma propriedade do tipo Title** (ícone “Aa” com destaque de título — é a coluna que o Notion usa como “nome” da linha).

**Opção simples (recomendada):**

1. Num espaço de trabalho, escreve `/database` ou **/base de dados** e escolhe **Database – Inline** ou **Database – Full page**.
2. Abre a base em **vista de tabela** (Table).
3. Confirma a **primeira coluna**: deve ser do tipo **Title**. Em contas em português o nome pode ser **Nome**, **Título**, ou em inglês **Name** — **anota o nome exato** do cabeçalho da coluna (respeita maiúsculas/minúsculas e acentos).
4. Não é obrigatório ter mais colunas; podes apagar colunas extra se quiseres manter só o título.

**`NOTION_DB_TITLE_COLUMN` / `NOTION_TITLE_PROPERTY` no n8n:**

- São o **nome do cabeçalho da coluna do tipo Título** na tabela Notion — **não** o tema do post nem “LinkedIn”.
- Se a coluna se chama **Name** → não precisas de variável (defeito do workflow).
- Se se chama **Nome**, **Título**, etc. → define **`NOTION_DB_TITLE_COLUMN`** (ou `NOTION_TITLE_PROPERTY`) **igualzinho** ao cabeçalho (ex.: `Nome`).
- Erro *«LinkedIn is not a property»* → no n8n apagaste ou definiste mal a variável como `LinkedIn`; **remove** `NOTION_TITLE_PROPERTY` ou corrige para o nome real da coluna Título.

##### C. Obter o `NOTION_DATABASE_ID` (UUID da base)

1. Abre a base como **página completa** (full page), não só o embed pequeno, para a barra de endereço mostrar o ID com clareza.
2. O URL costuma ter uma destas formas:
   - `https://www.notion.so/<workspace>/<DATABASE_ID>?v=...`
   - `https://www.notion.so/<DATABASE_ID>?v=...`
3. O identificador da base no URL é quase sempre um bloco de **32 caracteres hexadecimais** (às vezes **sem** hífenes no browser).
4. A API Notion aceita o ID em formato **UUID com hífenes**: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` (8-4-4-4-12). Se o teu URL tiver só 32 caracteres seguidos, insere hífenes nas posições corretas, por exemplo  
   `a1b2c3d4e5f6478990abcdef12345678` → `a1b2c3d4-e5f6-4789-90ab-cdef12345678`.
5. Coloca o valor **com hífenes** na variável n8n **`NOTION_DATABASE_ID`**.

Exemplo ilustrativo de URL (ID inventado):

- `https://www.notion.so/minha-equipe/a1b2c3d4e5f6478990abcdef12345678?v=...`  
  O segmento `a1b2c3d4e5f6478990abcdef12345678` é o raw ID; converte para UUID antes de colar no n8n.

**Nota:** Se copiares um URL de **página normal** (sem ser base), o ID não serve — tem de ser o da **própria database**.

##### D. Dar permissão à integração na base (indispensável)

Sem este passo, a API responde **401 / 403 / object_not_found**.

1. Abre a **base de dados** em ecrã inteiro.
2. No canto **superior direito**, abre o menu **⋯** (três pontos) **ou** o menu **⋯** ao lado do título da base na barra lateral (conforme a versão da UI).
3. Procura uma destas opções (o Notion muda o texto entre versões/idiomas):
   - **Connections** → **Connect to** / **Add connections** → escolhe a integração `n8n Tech Intel`; **ou**
   - **Add connections** / **Ligações** → seleciona a integração.
4. Confirma que a integração aparece como ligada à base (ícone ou lista de conexões).

Se não vires “Connections”, usa **Share** (Partilhar): às vezes integrações aparecem em **Invite** — o importante é **associar a integração à base** para ela poder criar páginas.

##### E. Resumo das variáveis no n8n

| Variável | Obrigatório | Exemplo / notas |
|----------|-------------|-----------------|
| `NOTION_TOKEN` | Sim | `secret_...` (só o secret) |
| `NOTION_DATABASE_ID` | Sim | UUID com hífenes |
| `NOTION_DB_TITLE_COLUMN` ou `NOTION_TITLE_PROPERTY` | Não | Nome da coluna **Título** na base (`Name`, `Nome`, …) — **não** `LinkedIn` |

##### F. O que o workflow grava no Notion

- **Uma nova linha** (página na base) por execução bem-sucedida do ramo Notion.
- **Título da linha:** igual ao assunto do email (`Relatório tech + LinkedIn <data>`).
- **Corpo:** texto plano derivado de `slack_text` (HTML convertido a texto na mesma lógica do nó anterior), repartido em **blocos parágrafo**; no máximo **99** blocos; cada bloco até ~**1900** caracteres (limite aproximado da API de rich text).

##### G. Problemas frequentes

| Sintoma | Causa provável |
|---------|----------------|
| `401` / `Unauthorized` | `NOTION_TOKEN` errado, revogado, ou com `Bearer ` incluído na variável (deve estar **só** o `secret_...`). |
| `object_not_found` | `NOTION_DATABASE_ID` incorreto ou ID de uma **página** em vez da **database**. |
| `validation_error` / propriedade desconhecida | Nome da coluna errado: deve ser a coluna **Título** (`Name`, `Nome`, …). Mensagem *«LinkedIn is not a property»* = variável definida como `LinkedIn` por engano — apaga ou corrige. |
| Página criada mas sem corpo | Texto vazio ou falha antes do HTTP; confere execução do nó **Preparar corpo Notion**. |

Documentação oficial: [Create a page](https://developers.notion.com/reference/post-page) (parent `database_id` + `properties` + `children`).

**Nota:** Se não existirem candidatos **publicados em ontem (UTC)**, o `SplitInBatches` pode não disparar o ramo de conclusão; nesse caso execute manualmente `POST /api/process` com `date` = ontem UTC e `lookback_days`: 1 (ou maior só se reprocessares várias partições RAW — ver [api-examples.http](api-examples.http)).

Ver notas nos workflows: timezone **UTC**, ingestão no nó Code = **apenas o dia civil anterior (D-1)**. **Header Auth:** nome do cabeçalho = `x-functions-key` (não usar frases com espaços no campo “Header Name”).

## 4. Pós-deploy RBAC (opcional)

Ver [rbac-manual.md](rbac-manual.md).

## 5. Verificação rápida

```http
GET https://<app>.azurewebsites.net/api/check-id?id=<sha256>&source=openai&published_date=2026-04-05
```

```http
POST https://<app>.azurewebsites.net/api/process
Content-Type: application/json

{ "date": "2026-04-05", "lookback_days": 1 }
```

Exemplos completos: [api-examples.http](api-examples.http).

## 6. Runbook de portões entre fases (T1–T6)

Checklist copiável (Azure CLI, curl, n8n, pytest): [phase-gates-checklist.md](phase-gates-checklist.md).

## Notas de modelo OpenAI

Quota e nomes de modelo variam por região. Se o deploy Bicep falhar no recurso `deployments`, ajuste `openAiModelName`, `openAiModelVersion` e `location` nos parâmetros.
