from __future__ import annotations

from shared.classification import Category, classify_text, relevance_score


def test_classify_openai_source_bias_ai() -> None:
    cat = classify_text("Weekly update", "Nothing specific", "openai")
    assert cat == "AI"


def test_classify_keyword_data() -> None:
    # Fonte com viés AI para forçar competição por palavras-chave de dados no texto.
    cat = classify_text(
        "Delta Lake and Spark tuning",
        "Unity Catalog metadata pipelines",
        "openai",
    )
    assert cat == "Data"


def test_classify_keyword_architecture() -> None:
    cat = classify_text("Kubernetes at scale", "Service mesh rollout", "uber")
    assert cat == "Architecture"


def test_relevance_score_in_range() -> None:
    s = relevance_score("t", "u", "AI")
    assert 0 <= s <= 100


def test_relevance_score_category_ai_boost() -> None:
    t = "Same text body for both"
    s_ai = relevance_score(t, "", "AI")
    s_data = relevance_score(t, "", "Data")
    assert s_ai >= s_data
