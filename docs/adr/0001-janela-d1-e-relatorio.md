# ADR 0001 — Janela de ingestão D-1 e formato do relatório

## Estado

Aceite (produção alinhada).

## Contexto

O desenho inicial previa janelas longas (ex.: 30 dias) e três tópicos LinkedIn. O produto evoluiu para **menor latência**, **menos timeout** no `/process` e entrega mais **legível** (Notion/e-mail).

## Decisão

1. **Ingestão:** apenas o **dia civil anterior em UTC** (`published_at` ∈ D-1).
2. **`POST /api/process`:** `lookback_days` **default = 1**; valores maiores só para reprocessamento manual sobre várias partições RAW.
3. **Relatório:** `linkedin_short_topics` (até 3) + `linkedin_deep_topic` (1); `linkedin_topics` espelha os curtos; textos LLM em **pt-BR** com menção de **fonte (feed)**.
4. **Notion:** até **100** blocos por criação de página; estrutura com títulos e links.

## Consequências

- Feeds com pouca atividade em D-1 podem gerar **zero** candidatos — comportamento esperado.
- Documentação canónica: `docs/estado-atual-pipeline.md`. Planos antigos em `.cursor/plans/` são históricos.
