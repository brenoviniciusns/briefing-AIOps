"""Enriquecimento do relatório (ex.: fonte do feed nos blocos LinkedIn)."""

from __future__ import annotations

from typing import Any


def enrich_linkedin_sources(
    short: list[dict[str, Any]],
    deep: dict[str, Any] | None,
    rows: list[dict[str, Any]],
) -> None:
    """Acrescenta `source` (feed) a primary_article / extra_articles usando o id do artigo."""
    src = {
        str(r["id"]).strip().lower(): str(r.get("source", ""))
        for r in rows
        if r.get("id")
    }

    def patch_block(b: dict[str, Any]) -> None:
        pa = b.get("primary_article")
        if isinstance(pa, dict) and not pa.get("source"):
            pid = str(pa.get("id", "")).strip().lower()
            if pid in src:
                pa["source"] = src[pid]
        extras = b.get("extra_articles")
        if isinstance(extras, list):
            for ex in extras:
                if isinstance(ex, dict) and not ex.get("source"):
                    eid = str(ex.get("id", "")).strip().lower()
                    if eid in src:
                        ex["source"] = src[eid]

    for t in short:
        if isinstance(t, dict):
            patch_block(t)
    if isinstance(deep, dict):
        patch_block(deep)
