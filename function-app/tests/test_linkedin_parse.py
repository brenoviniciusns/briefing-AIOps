from __future__ import annotations

import json

from shared.openai_client import _parse_linkedin_bundle


def _id(n: int) -> str:
    return f"{n:064x}"


def test_parse_bundle_valid_shorts_and_deep() -> None:
    allowed = {_id(1), _id(2), _id(3), _id(4)}
    raw = json.dumps(
        {
            "linkedin_short_topics": [
                {
                    "topic_label": "A",
                    "hook_line": "h1",
                    "primary_article": {"id": _id(1), "title": "t1", "url": "u1"},
                    "extra_articles": [],
                },
                {
                    "topic_label": "B",
                    "hook_line": "h2",
                    "primary_article": {"id": _id(2), "title": "t2", "url": "u2"},
                },
            ],
            "linkedin_deep_topic": {
                "topic_label": "Deep",
                "angle_for_post": "long",
                "primary_article": {"id": _id(3), "title": "t3", "url": "u3"},
            },
        },
        ensure_ascii=False,
    )
    shorts, deep, new_ids = _parse_linkedin_bundle(raw, allowed, expect_short=2)
    assert len(shorts) == 2
    assert shorts[0]["rank"] == 1
    assert shorts[1]["rank"] == 2
    assert shorts[0]["hook_line"] == "h1"
    assert deep is not None
    assert deep["topic_label"] == "Deep"
    assert _id(1) in new_ids and _id(2) in new_ids and _id(3) in new_ids


def test_parse_bundle_invalid_json_returns_empty() -> None:
    s, d, ids = _parse_linkedin_bundle("not json", {_id(1)}, 1)
    assert s == [] and d is None and ids == []


def test_parse_bundle_rejects_unknown_primary_id() -> None:
    allowed = {_id(1)}
    raw = json.dumps(
        {
            "linkedin_short_topics": [
                {
                    "hook_line": "x",
                    "primary_article": {"id": "g" * 64, "title": "bad", "url": "u"},
                }
            ]
        }
    )
    shorts, _, _ = _parse_linkedin_bundle(raw, allowed, expect_short=3)
    assert shorts == []


def test_parse_bundle_dedupes_duplicate_primary_in_shorts() -> None:
    allowed = {_id(1)}
    raw = json.dumps(
        {
            "linkedin_short_topics": [
                {"hook_line": "a", "primary_article": {"id": _id(1), "title": "t", "url": "u"}},
                {"hook_line": "b", "primary_article": {"id": _id(1), "title": "t", "url": "u"}},
            ]
        }
    )
    shorts, _, _ = _parse_linkedin_bundle(raw, allowed, expect_short=2)
    assert len(shorts) == 1
