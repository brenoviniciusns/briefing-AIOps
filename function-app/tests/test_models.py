from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from shared.models import CheckIdParams, ProcessBody, RawArticle


def _valid_sha256() -> str:
    return "a" * 64


def test_check_id_params_valid() -> None:
    p = CheckIdParams(id=_valid_sha256(), source="openai", published_date=date(2026, 4, 5))
    assert p.source == "openai"


def test_check_id_params_id_must_be_hex() -> None:
    with pytest.raises(ValidationError):
        CheckIdParams(id="g" * 64, source="x", published_date=date(2026, 1, 1))


def test_check_id_params_id_length() -> None:
    with pytest.raises(ValidationError):
        CheckIdParams(id="ab", source="x", published_date=date(2026, 1, 1))


def test_process_body_defaults() -> None:
    b = ProcessBody.model_validate({"date": "2026-04-05"})
    assert b.archive is False
    assert b.lookback_days == 1


def test_raw_article_accepts_extra_fields() -> None:
    r = RawArticle.model_validate(
        {
            "id": _valid_sha256(),
            "source": "openai",
            "title": "T",
            "url": "https://example.com/p",
            "published_at": "2026-04-05T12:00:00Z",
            "ingested_at": "2026-04-06T07:00:00Z",
            "blob_path": "year=2026/...",
        }
    )
    assert r.title == "T"
