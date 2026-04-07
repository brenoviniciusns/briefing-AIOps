# Estrutura do relatório → Notion

O workflow de entrega transforma o JSON do relatório (`daily-report-YYYY-MM-DD.json`) em **e-mail HTML** e, em paralelo, numa **nova linha na base Notion**: a propriedade **Título** vem do assunto do e-mail; o **corpo da página** são blocos `paragraph` com o texto plano equivalente (mesma ordem que o e-mail).

## 1. Do blob JSON à página Notion

```mermaid
flowchart LR
  subgraph src["Armazenamento Azure"]
    R[("reports/daily-report-{date}.json")]
  end

  subgraph api["Function App"]
    GET["GET /api/report?date="]
  end

  subgraph n8n["n8n — entrega"]
    HTML["Montar HTML + slack_text\n+ notion_children (blocos)"]
    PREP["Preparar corpo Notion\nusa notion_children com\ntítulos e links clicáveis"]
    HTTP["POST api.notion.com/v1/pages"]
  end

  subgraph notion["Notion — database"]
    ROW["Nova página / linha"]
    TIT["Propriedade Título\nex.: Relatório tech + LinkedIn 2026-04-05"]
    BODY["Corpo: sequência de parágrafos"]
  end

  R --> GET --> HTML --> PREP --> HTTP
  HTML -->|subject + notion_children| PREP
  HTTP --> ROW
  ROW --> TIT
  ROW --> BODY
```

## 2. Conteúdo lógico (ordem no corpo Notion ≈ ordem do e-mail)

Cada secção abaixo origina **texto contínuo** nos parágrafos; não há colunas Notion por campo JSON — tudo flui como narrativa.

```mermaid
flowchart TB
  ROOT["Página Notion"]

  ROOT --> H["Cabeçalho\nInteligência técnica — {date}"]
  ROOT --> L3["LinkedIn — 3 ganchos rápidos\n• pt-BR; menciona fonte (feed)\n• link + (fonte: …)"]
  ROOT --> LD["LinkedIn — tema em destaque\n• pt-BR; fonte quando relevante\n• link(s) + (fonte: …)"]
  ROOT --> INS["Insights principais\n• pt-BR; (fonte: …) quando aplicável"]
  ROOT --> CAT["Por categoria (rótulos pt)\nIA / Arquitetura / Dados\n• resumo pt-BR com (Fonte: feed) nos bullets"]
  ROOT --> FT["Rodapé\n• Fontes de dados (feeds) • janela RAW"]

  style L3 fill:#e8f4fc
  style LD fill:#e8f4fc
```

## 3. Modelo de dados do relatório (referência)

O Notion **não** guarda este JSON; serve de referência do que alimenta o HTML/texto que vês na página.

```mermaid
flowchart TB
  REP[daily-report JSON]

  REP --> M[Metadados\ndate, lookback_days, window_*, sources, processing_run_id]
  REP --> LI[linkedin_short_topics\naté 3 × hook_line, scores, artigos]
  REP --> LD[linkedin_deep_topic\nangle_for_post longo, artigos]
  REP --> LT[linkedin_topics\nespelho dos 3 curtos]
  REP --> LLM[llm_insights\nkey_insights, trends, …]
  REP --> SEC[sections\nAI | Architecture | Data]

  LI -.->|gera secções LinkedIn no HTML| LD
```

Para o contrato completo dos campos, ver [schemas.md](schemas.md).
