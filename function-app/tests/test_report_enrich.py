from __future__ import annotations

from shared.report_enrich import enrich_linkedin_sources


def _id(n: int) -> str:
    return f"{n:064x}"


def test_enrich_fills_primary_and_extra_source() -> None:
    rows = [
        {"id": _id(1), "source": "openai"},
        {"id": _id(2), "source": "databricks"},
    ]
    short = [
        {
            "primary_article": {"id": _id(1), "title": "A", "url": "https://a"},
            "extra_articles": [{"id": _id(2), "title": "B", "url": "https://b"}],
        }
    ]
    deep = {"primary_article": {"id": _id(2), "title": "B2", "url": "https://b2"}}
    enrich_linkedin_sources(short, deep, rows)
    assert short[0]["primary_article"]["source"] == "openai"
    assert short[0]["extra_articles"][0]["source"] == "databricks"
    assert deep["primary_article"]["source"] == "databricks"


def test_enrich_skips_when_source_already_set() -> None:
    rows = [{"id": _id(3), "source": "from-rows"}]
    short = [{"primary_article": {"id": _id(3), "source": "keep-me", "url": "u"}}]
    enrich_linkedin_sources(short, None, rows)
    assert short[0]["primary_article"]["source"] == "keep-me"


def test_enrich_empty_short_and_none_deep() -> None:
    enrich_linkedin_sources([], None, [])
