from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from openai import AzureOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from shared.config import openai_api_key, openai_deployment, openai_endpoint

logger = logging.getLogger(__name__)

_OPENAI_API_VERSION = "2024-08-01-preview"


def _azure_openai_client() -> AzureOpenAI:
    endpoint = openai_endpoint()
    if not endpoint:
        raise RuntimeError("OPENAI_ENDPOINT não configurado.")
    key = openai_api_key()
    if key:
        return AzureOpenAI(
            api_key=key,
            api_version=_OPENAI_API_VERSION,
            azure_endpoint=endpoint,
        )
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider

    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(),
        "https://cognitiveservices.azure.com/.default",
    )
    return AzureOpenAI(
        azure_ad_token_provider=token_provider,
        api_version=_OPENAI_API_VERSION,
        azure_endpoint=endpoint,
    )

SYSTEM_JSON_PT = (
    "És um arquiteto sénior de IA/dados. Sê conciso e técnico. "
    "Toda a linguagem natural nas tuas respostas deve estar em português do Brasil (pt-BR). "
    "Responde apenas com JSON válido, sem cercas markdown."
)

SYSTEM_SUMMARY_PT = (
    "És um arquiteto sénior de IA/dados. Sê conciso e técnico. "
    "Escreve sempre em português do Brasil (pt-BR). "
    "Não uses JSON; usa linhas de texto começadas por '- '."
)


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential_jitter(initial=1, max=60),
    reraise=True,
)
def _chat(messages: list[dict[str, str]], max_tokens: int = 800) -> str:
    client = _azure_openai_client()
    resp = client.chat.completions.create(
        model=openai_deployment(),
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.35,
    )
    choice = resp.choices[0].message
    content = (choice.content or "").strip()
    if not content:
        raise RuntimeError("Resposta vazia do Azure OpenAI")
    return content


def summarize_article(title: str, url: str, source: str, snippet: str) -> str:
    user = (
        f"Título: {title}\nFonte do feed (identificador): {source}\nURL: {url}\n\nTrecho:\n{snippet[:6000]}\n\n"
        "Resume em 1-2 bullets técnicos em português do Brasil. Cada linha começa com '- '. "
        f"Em cada bullet inclui explicitamente a fonte, no formato '(Fonte: {source})' no texto."
    )
    try:
        return _chat(
            [
                {"role": "system", "content": SYSTEM_SUMMARY_PT},
                {"role": "user", "content": user},
            ],
            max_tokens=220,
        )
    except Exception:
        logger.exception("Falha ao resumir artigo: %s", url)
        return "- (Resumo indisponível — ver URL)"


def _linkedin_audience_text() -> str:
    p = Path(__file__).resolve().parent / "linkedin_audience_summary.md"
    if p.is_file():
        return p.read_text(encoding="utf-8")[:12000]
    return "Technical AI/Data platform leader; Azure, Databricks, MLOps, GenAI, governance."


def daily_executive_brief(articles_payload: list[dict[str, Any]]) -> dict[str, Any]:
    user = (
        "Analisa as atualizações seguintes (corpus do dia ou curto). "
        "Cada objeto tem title, url, source (identificador do feed, ex.: openai, databricks), category.\n"
        "Foco: decisões de arquitetura, mudanças estratégicas, padrões novos, riscos.\n\n"
        f"Artigos (JSON):\n{json.dumps(articles_payload, ensure_ascii=False)[:120000]}\n\n"
        "Resposta: apenas JSON. Todas as strings em português do Brasil.\n"
        "Quando uma frase se referir a um anúncio concreto, indica a fonte entre parênteses "
        "com o valor do campo `source` (ex.: … (fonte: openai)).\n"
        "key_insights: array, no máx. 3 itens, cada um no máx. ~18 palavras.\n"
        "trends: array, no máx. 2 frases curtas.\n"
        "important_changes: array, no máx. 2 itens curtos.\n"
        "actionable_takeaways: array, no máx. 3 itens de uma linha."
    )
    raw = _chat(
        [
            {"role": "system", "content": SYSTEM_JSON_PT},
            {"role": "user", "content": user},
        ],
        max_tokens=520,
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("LLM não devolveu JSON válido no brief; a encapsular texto bruto.")
        return {
            "key_insights": [raw[:2000]],
            "trends": [],
            "important_changes": [],
            "actionable_takeaways": [],
        }


def _primary_id(item: dict[str, Any]) -> str | None:
    pa = item.get("primary_article")
    if not isinstance(pa, dict):
        return None
    pid = str(pa.get("id", "")).strip().lower()
    if len(pid) != 64:
        return None
    return pid


def _parse_linkedin_bundle(
    raw: str, allowed_ids: set[str], expect_short: int
) -> tuple[list[dict[str, Any]], dict[str, Any] | None, list[str]]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("linkedin bundle: JSON inválido")
        return [], None, []
    if not isinstance(data, dict):
        return [], None, []
    shorts_raw = data.get("linkedin_short_topics")
    if not isinstance(shorts_raw, list):
        shorts_raw = []
    deep_raw = data.get("linkedin_deep_topic")
    out_short: list[dict[str, Any]] = []
    seen_primary: set[str] = set()
    for item in shorts_raw:
        if not isinstance(item, dict):
            continue
        pid = _primary_id(item)
        if not pid or pid not in allowed_ids or pid in seen_primary:
            continue
        seen_primary.add(pid)
        hook = str(item.get("hook_line") or item.get("angle_for_post") or "").strip()
        if hook:
            item["hook_line"] = hook
            item["angle_for_post"] = hook
        out_short.append(item)
        if len(out_short) >= expect_short:
            break
    for i, t in enumerate(out_short, start=1):
        t["rank"] = i

    deep_out: dict[str, Any] | None = None
    if isinstance(deep_raw, dict):
        pid = _primary_id(deep_raw)
        if pid and pid in allowed_ids:
            deep_out = deep_raw

    new_ids: list[str] = []
    seen_all: set[str] = set()

    def _add_id(hex_id: str) -> None:
        if hex_id in seen_all:
            return
        seen_all.add(hex_id)
        new_ids.append(hex_id)

    for t in out_short:
        pid = _primary_id(t)
        if pid and pid in allowed_ids:
            _add_id(pid)
        extras = t.get("extra_articles")
        if isinstance(extras, list):
            for ex in extras:
                if isinstance(ex, dict):
                    eid = str(ex.get("id", "")).strip().lower()
                    if len(eid) == 64 and eid in allowed_ids:
                        _add_id(eid)
    if deep_out:
        pid = _primary_id(deep_out)
        if pid and pid in allowed_ids:
            _add_id(pid)
        extras = deep_out.get("extra_articles")
        if isinstance(extras, list):
            for ex in extras:
                if isinstance(ex, dict):
                    eid = str(ex.get("id", "")).strip().lower()
                    if len(eid) == 64 and eid in allowed_ids:
                        _add_id(eid)

    return out_short, deep_out, new_ids


def linkedin_topics_bundle(
    articles: list[dict[str, Any]],
    run_id: str,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None, list[str]]:
    """3 ganchos curtos + 1 tema detalhado; ids para histórico anti-repetição."""
    if not articles:
        return [], None, []
    allowed_ids = {str(a.get("id", "")).strip().lower() for a in articles}
    allowed_ids.discard("")
    n = len(articles)
    n_short = min(3, n)
    aud = _linkedin_audience_text()
    user = (
        "Perfil de audiência:\n"
        f"{aud}\n\n"
        "Escolhe conteúdo APENAS dos artigos abaixo (usa os `id` exatos do JSON). "
        "Cada artigo tem `source` (identificador do feed: openai, databricks, etc.). "
        "Prioriza o que for mais relevante para audiência **dados** no LinkedIn: plataformas de dados, lakehouse, "
        "analytics engineering, MLOps/LLMOps, GenAI em produção, Azure/Databricks/cloud, "
        "governança, pipelines — técnico, sem floreio.\n\n"
        f"Devolve exatamente {n_short} objetos em linkedin_short_topics — primary_article distinto quando possível. "
        "Cada gancho: topic_label (pt-BR, até ~8 palavras, chamativo), hook_line em português do Brasil, "
        "UMA linha até 200 caracteres (sem quebras de linha), mencionando naturalmente a fonte do artigo (campo source), "
        "profile_match_score 0-100.\n"
        "linkedin_deep_topic: UM objeto — a melhor história para um post mais longo; "
        "topic_label e angle_for_post em português do Brasil com 3-5 frases (mais detalhe que os ganchos); "
        "menciona a fonte (feed) quando fizer sentido; "
        "profile_match_score, primary_article, extra_articles [] opcional. "
        "Preferir quarto primary_article distinto se n>=4; com poucos artigos, reutilizar é aceitável.\n\n"
        f"Artigos (JSON):\n{json.dumps(articles[:150], ensure_ascii=False)[:100000]}\n\n"
        "Saída: apenas JSON:\n"
        "{ \"linkedin_short_topics\": [ "
        "{ \"rank\": 1, \"topic_label\": \"...\", \"profile_match_score\": 88, \"hook_line\": \"...\", "
        "\"primary_article\": {\"id\":\"...\",\"title\":\"...\",\"url\":\"...\"}, \"extra_articles\": [] } ], "
        "\"linkedin_deep_topic\": { \"topic_label\": \"...\", \"profile_match_score\": 92, \"angle_for_post\": \"...\", "
        "\"primary_article\": {\"id\":\"...\",\"title\":\"...\",\"url\":\"...\"}, \"extra_articles\": [] } }\n"
        f"run_id: {run_id}"
    )
    try:
        raw = _chat(
            [
                {"role": "system", "content": SYSTEM_JSON_PT},
                {"role": "user", "content": user},
            ],
            max_tokens=1400,
        )
    except Exception:
        logger.exception("Falha ao gerar bundle LinkedIn")
        return [], None, []
    return _parse_linkedin_bundle(raw, allowed_ids, n_short)
