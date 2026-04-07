# Briefing AIOps — Daily Tech Intelligence Pipeline

Pipeline **RSS/API → Azure Data Lake → Azure Functions (Python) + Azure OpenAI → n8n** (e-mail, Notion, Slack opcional). Relatórios diários com foco **D-1 UTC**, conteúdo **pt-BR** e sugestões **LinkedIn** (3 ganchos + 1 tema detalhado).

## Início rápido

1. **Documentação canónica (comportamento atual):** [docs/estado-atual-pipeline.md](docs/estado-atual-pipeline.md)
2. **Runbook (incidentes, 504, segredos):** [docs/runbook.md](docs/runbook.md)
3. **Deploy:** [docs/deployment.md](docs/deployment.md)
4. **Testes Python:** [docs/TESTING.md](docs/TESTING.md) — `cd function-app && python -m pytest tests/ -q`
5. **Sincronizar espelho n8n:** `python scripts/sync_n8n_workflows.py`
6. **Agentes / Cursor:** [AGENTS.md](AGENTS.md) e [agents/CONTEXT.md](agents/CONTEXT.md)

## Estrutura principal

| Pasta | Conteúdo |
|-------|----------|
| `function-app/` | Azure Functions, lógica de processamento |
| `infra/bicep/` | IaC |
| `n8n/` | Workflows exportáveis + `snippets/` para nós Code |
| `docs/` | Deploy, esquemas, testes, estado atual |
| `agents/` | Prompts e fluxos para orquestração |

## Versão

Com Git inicializado na raiz, após deploy estável: `git tag -a v0.1.0 -m "Pipeline D-1 + entrega pt-BR/Notion"` (ver `docs/estado-atual-pipeline.md`).
