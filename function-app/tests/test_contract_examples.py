"""Contrato: exemplos em ../../examples/ alinhados a modelos e forma do relatório."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_EXAMPLES = _REPO_ROOT / "examples"


def _load(name: str) -> dict:
    p = _EXAMPLES / name
    if not p.is_file():
        pytest.skip(f"exemplo em falta: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def test_process_post_body_matches_process_body() -> None:
    from shared.models import ProcessBody

    ProcessBody.model_validate(_load("process-post-body.json"))


def test_check_id_post_body_matches_check_id_params() -> None:
    from shared.models import CheckIdParams

    d = _load("check-id-post-body.json")
    CheckIdParams.model_validate(
        {
            "id": d["id"],
            "source": d["source"],
            "published_date": d["published_date"],
        }
    )


def test_report_minimal_has_required_keys() -> None:
    doc = _load("report-response-minimal.json")
    required = {
        "date",
        "lookback_days",
        "window_start",
        "window_end",
        "sections",
        "sources",
        "linkedin_short_topics",
        "linkedin_deep_topic",
        "linkedin_topics",
        "llm_insights",
        "processing_run_id",
    }
    assert required <= set(doc.keys())
    sec = doc["sections"]
    assert isinstance(sec, dict)
    assert {"AI", "Architecture", "Data"} <= set(sec.keys())
    ins = doc["llm_insights"]
    assert isinstance(ins, dict)
    for k in ("key_insights", "trends", "important_changes", "actionable_takeaways"):
        assert k in ins
