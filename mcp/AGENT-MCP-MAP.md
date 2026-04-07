# Mapa agente → MCP

Objetivo: cada agente lógico usa ferramentas MCP de forma **explícita**, sem scraping HTML além do permitido na allowlist (**RSS** + **APIs JSON** declaradas, ex. Hacker News Firebase — ver `allowlist_rss.yaml`).

## Orquestrador

- **Postman MCP**: validar `/check-id` e `/process` (corpo com `date` + `lookback_days`), guardar exemplos em `examples/`.
- **GitLens / Git**: versão de workflows n8n e Bicep (se usar repositório git).

## Agente de ingestão (n8n)

- **n8n MCP** (se ativo no workspace): importar/exportar workflows em `n8n/workflows/`.
- Evitar browser para fontes; usar só RSS e APIs JSON da allowlist.

## Agente de processamento (Python + OpenAI)

- **context7**: referência de `openai`, `azure-identity`, `azure-storage-file-datalake`, `deltalake`.
- **Postman MCP**: testes da Function com cabeçalhos e corpos de `examples/`.

## Agente de entrega (n8n)

- **cursor-ide-browser** (se disponível): smoke test do HTML renderizado.
- **Postman MCP**: webhooks Slack simulados (se aplicável).

## Nota

Os servidores MCP efetivos dependem da configuração do Cursor em `mcps/`. Este ficheiro define a **política de uso**, não substitui a lista de servidores ligados.
