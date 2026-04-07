# Atribuições RBAC (Managed Identity da Function → Storage / Key Vault / OpenAI)

## Opção A — Automático no Bicep (recomendado se tiveres permissão)

No [`main.bicep`](../infra/bicep/main.bicep) existem os parâmetros:

- `deployRbacAssignments` — cria três `Microsoft.Authorization/roleAssignments` (Storage Blob Data Contributor, Key Vault Secrets User, Cognitive Services OpenAI User) no módulo [`modules/rbac.bicep`](../infra/bicep/modules/rbac.bicep).
- `useManagedIdentityDataPlane` — define `STORAGE_ACCOUNT_KEY` e `OPENAI_API_KEY` vazios nas App Settings e ativa `USE_MANAGED_IDENTITY_DATA_PLANE` / `OPENAI_USE_AZURE_AD` para o código Python usar `DefaultAzureCredential`.

**Quem pode fazer o deploy com `deployRbacAssignments: true`:** perfil **Owner** ou **User Access Administrator** (ou equivalente com `Microsoft.Authorization/roleAssignments/write` no âmbito). Um **Contributor** puro continua a falhar neste passo — nesse caso usa a opção B.

**Ordem sugerida (primeira vez com MI):** deploy com `deployRbacAssignments: true` e `useManagedIdentityDataPlane: false` (app ainda com chaves); após as roles propagarem (pode levar alguns minutos), faz um segundo deploy com `useManagedIdentityDataPlane: true` **ou** altera as App Settings no portal. Assim reduzes o risco de a app ficar sem chaves antes das roles existirem.

## Opção B — Manual com Azure CLI (Contributor-friendly no deploy IaC)

Se o template **não** criar roles (valor por defeito `deployRbacAssignments: false`), um administrador aplica os comandos abaixo.

Substitua os placeholders:

- `<SUBSCRIPTION_ID>`
- `<RESOURCE_GROUP>`
- `<STORAGE_ACCOUNT_NAME>`
- `<KEY_VAULT_NAME>`
- `<OPENAI_ACCOUNT_NAME>` (nome do recurso Cognitive Services / OpenAI)
- `<FUNCTION_PRINCIPAL_ID>` (output `functionPrincipalId` do deploy Bicep, ou Portal → Function App → Identity)

## Storage (Data Lake Gen2)

```bash
az role assignment create \
  --assignee-object-id <FUNCTION_PRINCIPAL_ID> \
  --assignee-principal-type ServicePrincipal \
  --role "Storage Blob Data Contributor" \
  --scope "/subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RESOURCE_GROUP>/providers/Microsoft.Storage/storageAccounts/<STORAGE_ACCOUNT_NAME>"
```

## Key Vault (ler segredos com referências `@Microsoft.KeyVault(...)`)

```bash
az role assignment create \
  --assignee-object-id <FUNCTION_PRINCIPAL_ID> \
  --assignee-principal-type ServicePrincipal \
  --role "Key Vault Secrets User" \
  --scope "/subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RESOURCE_GROUP>/providers/Microsoft.KeyVault/vaults/<KEY_VAULT_NAME>"
```

## Azure OpenAI

```bash
az role assignment create \
  --assignee-object-id <FUNCTION_PRINCIPAL_ID> \
  --assignee-principal-type ServicePrincipal \
  --role "Cognitive Services OpenAI User" \
  --scope "/subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RESOURCE_GROUP>/providers/Microsoft.CognitiveServices/accounts/<OPENAI_ACCOUNT_NAME>"
```

Após atribuir roles ao Storage, pode alterar o código da Function para usar `DefaultAzureCredential` e remover `STORAGE_ACCOUNT_KEY` das App Settings (opcional, melhor prática).

---

## FAQ: “Contornar” RBAC e onde ficam os segredos

### Dá para usar Managed Identity sem pedir roles a ninguém?

**Não de forma útil.** Para a MI da Function aceder ao **data plane** do Storage (blobs), ao **Key Vault** (ler secrets) ou ao **Azure OpenAI** (chamadas com identidade em vez de key), a plataforma **sempre** precisa de **RBAC** (ou, no KV clássico, *access policies*) atribuídas a essa identidade. Quem só tem **Contributor** na subscrição **não consegue** criar essas atribuições via Bicep/CLI — daí o padrão “Contributor-friendly” do projeto: **connection string / account keys** nas App Settings (o segredo ainda existe; só evita o passo de `roleAssignments`).

**Contorno real** em ambientes restritos: manter chaves em App Settings (ou em variáveis de pipeline) até um **Owner** ou **User Access Administrator** aplicar as três roles acima; depois migrar para MI + `DefaultAzureCredential` e/ou referências ao Key Vault.

### Os segredos podem ficar “no próprio recurso” (Function)?

**Parcialmente.** O recurso **Azure Function App** não substitui o Key Vault: não há um “cofre embutido” genérico para todos os segredos.

O padrão Azure é:

1. **Segredos no Key Vault** (recurso dedicado que já está no Bicep).
2. Nas **Application settings** da Function, em vez do valor em claro, usar **referência ao Key Vault**, por exemplo:  
   `@Microsoft.KeyVault(SecretUri=https://<vault>.vault.azure.net/secrets/<nome>/<versão>)`  
   No portal o valor aparece mascarado; em runtime a plataforma resolve o secret **desde que** a identidade da app tenha permissão de leitura no KV (**Key Vault Secrets User** com RBAC no cofre, ou *access policy* equivalente).

Ou seja: o segredo **mora no Key Vault**; na Function fica só a **referência** (metadado), não o texto do secret. Ainda assim é **obrigatório** RBAC (ou policy) da MI → KV para isso funcionar.

### OpenAI e Storage “sem key” na app?

- **Storage / Delta:** com **Storage Blob Data Contributor** na MI e código a usar `DefaultAzureCredential`, pode evitar `STORAGE_ACCOUNT_KEY` nas settings (o runtime da Function continua a precisar de `AzureWebJobsStorage` para o próprio host; isso é separado do pipeline ADLS).
- **Azure OpenAI:** com role **Cognitive Services OpenAI User** na MI e SDK a usar credencial Azure AD (`DefaultAzureCredential` / token), pode evitar `OPENAI_API_KEY` nas settings (depende de versão do SDK e do padrão suportado na sua conta).

Em qualquer um destes modos “sem key”, **continua a haver RBAC** — apenas deixa de haver key estática na configuração.
