# Exemplos de contrato HTTP / JSON

Ficheiros usados por **testes automáticos** (`function-app/tests/test_contract_examples.py`) para garantir que os exemplos continuam alinhados aos modelos Pydantic, ao formato mínimo do relatório e aos **corpos POST** de [docs/api-examples.http](../docs/api-examples.http).

Matriz de fonte de verdade: [docs/estado-atual-pipeline.md](../docs/estado-atual-pipeline.md) (secção «Congelamento de contrato»).

| Ficheiro | Uso |
|----------|-----|
| `check-id-post-body.json` | Corpo `POST /api/check-id` |
| `process-post-body.json` | Corpo `POST /api/process` |
| `report-response-minimal.json` | Forma mínima do `GET /api/report` (sem dados reais) |
