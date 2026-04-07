# Testes — Function App (Python)

## Requisitos

- Python 3.11+ recomendado (alinhado ao runtime Azure; 3.14 local funciona para pytest se as dependências instalarem).
- Dependências: `pip install -r requirements.txt` dentro de `function-app/`.

## Executar

```bash
cd function-app
python -m pytest tests/ -q
```

Com verbosidade:

```bash
python -m pytest tests/ -v
```

## O que está coberto

| Ficheiro | Área |
|----------|------|
| `test_models.py` | `ProcessBody`, `CheckIdParams`, `RawArticle` |
| `test_classification.py` | `classify_text`, `relevance_score` |
| `test_report_enrich.py` | `enrich_linkedin_sources` (fonte no relatório LinkedIn) |
| `test_linkedin_parse.py` | `_parse_linkedin_bundle` (validação JSON do bundle LinkedIn, sem chamar OpenAI) |
| `test_contract_examples.py` | Ficheiros em **`examples/`** na raiz (contrato alinhado a `ProcessBody`, `CheckIdParams`, chaves do relatório) e **corpos POST** idênticos aos de `docs/api-examples.http` |

## Fora de âmbito (testes manuais / integração)

- Chamadas reais a Azure OpenAI, Storage e Delta (custam / exigem credenciais).
- Workflows n8n (validar com execução de teste na instância e checklist em [phase-gates-checklist.md](phase-gates-checklist.md)).

## CI sugerido

Num pipeline futuro: `cd function-app && pip install -r requirements.txt && pytest tests/ -q`.
