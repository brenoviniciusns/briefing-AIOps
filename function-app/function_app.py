from __future__ import annotations

import json
import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

import azure.functions as func

from shared.classification import classify_text, relevance_score
from shared.delta_ops import upsert_articles
from shared.models import CheckIdParams, ProcessBody, RawArticle
from shared.openai_client import daily_executive_brief, linkedin_topics_bundle, summarize_article
from shared.storage import (
    append_featured_article_ids,
    iter_raw_articles_date_range,
    raw_article_exists,
    read_featured_article_ids,
    read_report_json,
    write_report_json,
)
from shared.config import max_articles_per_run
from shared.report_enrich import enrich_linkedin_sources

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


def _json_response(body: dict[str, Any], status: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(body, ensure_ascii=False),
        status_code=status,
        mimetype="application/json",
    )


def _parse_check_params(req: func.HttpRequest) -> CheckIdParams:
    if req.method == "GET":
        pid = req.params.get("published_date") or req.params.get("date")
        if not pid:
            raise ValueError("published_date é obrigatório (YYYY-MM-DD)")
        return CheckIdParams(
            id=req.params.get("id") or "",
            source=req.params.get("source") or "",
            published_date=date.fromisoformat(pid),
        )
    data = req.get_json()
    if not data:
        raise ValueError("JSON body obrigatório")
    return CheckIdParams(
        id=str(data.get("id", "")),
        source=str(data.get("source", "")),
        published_date=date.fromisoformat(str(data.get("published_date"))),
    )


@app.route(route="check-id", methods=["GET", "POST"], auth_level=func.AuthLevel.FUNCTION)
def check_id(req: func.HttpRequest) -> func.HttpResponse:
    try:
        p = _parse_check_params(req)
        exists = raw_article_exists(p.source, p.id, p.published_date)
        return _json_response({"exists": exists, "id": p.id})
    except Exception as e:
        logger.warning("check-id inválido: %s", e)
        return _json_response({"error": str(e)}, status=400)


@app.route(route="process", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def process(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
        if not body:
            return _json_response({"error": "JSON body obrigatório"}, 400)
        pb = ProcessBody.model_validate(body)
        run_id = str(uuid.uuid4())
        target = pb.date
        window_start = target - timedelta(days=pb.lookback_days - 1)

        raw_items: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in iter_raw_articles_date_range(window_start, target):
            aid = str(row.get("id", "")).strip().lower()
            if not aid or aid in seen:
                continue
            seen.add(aid)
            raw_items.append(row)

        raw_items = raw_items[: max_articles_per_run()]
        now = datetime.now(timezone.utc).isoformat()

        delta_rows: list[dict[str, Any]] = []
        sections: dict[str, list[dict[str, Any]]] = {"AI": [], "Architecture": [], "Data": []}

        for row in raw_items:
            try:
                art = RawArticle.model_validate(row)
            except Exception:
                logger.exception("RAW inválido, a ignorar: %s", row)
                continue
            cat = classify_text(art.title, art.summary, art.source)
            score = relevance_score(art.title, art.summary, cat)
            summary = summarize_article(art.title, art.url, art.source, art.summary or art.title)
            delta_rows.append(
                {
                    "id": art.id,
                    "source": art.source,
                    "title": art.title,
                    "url": art.url,
                    "published_at": art.published_at,
                    "category": cat,
                    "score": int(score),
                    "summary": summary,
                    "ingested_at": art.ingested_at or now,
                    "processing_run_id": run_id,
                }
            )
            entry = {
                "id": art.id,
                "title": art.title,
                "url": art.url,
                "source": art.source,
                "score": score,
                "summary": summary,
            }
            sections[cat].append(entry)

        upsert_articles(delta_rows)

        brief_payload = [
            {"title": r["title"], "url": r["url"], "source": r["source"], "category": r["category"]}
            for r in delta_rows
        ]
        llm_insights = daily_executive_brief(brief_payload) if brief_payload else {}

        featured = read_featured_article_ids()
        linkedin_candidates = [
            {
                "id": r["id"],
                "title": r["title"],
                "url": r["url"],
                "source": r["source"],
                "category": r["category"],
                "score": r["score"],
                "summary": (r.get("summary") or "")[:500],
            }
            for r in delta_rows
            if str(r.get("id", "")).strip().lower() not in featured
        ]
        linkedin_short, linkedin_deep, linkedin_new_ids = linkedin_topics_bundle(
            linkedin_candidates, run_id
        )
        enrich_linkedin_sources(linkedin_short, linkedin_deep, delta_rows)
        if linkedin_new_ids:
            append_featured_article_ids(linkedin_new_ids)

        sources_sorted = sorted({r["source"] for r in delta_rows})
        report = {
            "date": target.isoformat(),
            "lookback_days": pb.lookback_days,
            "window_start": window_start.isoformat(),
            "window_end": target.isoformat(),
            "sections": sections,
            "sources": sources_sorted,
            "linkedin_short_topics": linkedin_short,
            "linkedin_deep_topic": linkedin_deep,
            "linkedin_topics": linkedin_short,
            "llm_insights": llm_insights,
            "processing_run_id": run_id,
        }
        path = write_report_json(target, report, archive=pb.archive)
        return _json_response(
            {
                "ok": True,
                "date": target.isoformat(),
                "processed_count": len(delta_rows),
                "report_path": path,
                "processing_run_id": run_id,
            }
        )
    except Exception as e:
        logger.exception("Falha em /process")
        return _json_response({"error": str(e)}, status=500)


@app.route(route="report", methods=["GET"], auth_level=func.AuthLevel.FUNCTION)
def report(req: func.HttpRequest) -> func.HttpResponse:
    try:
        ds = req.params.get("date")
        if not ds:
            return _json_response({"error": "query date=YYYY-MM-DD obrigatório"}, 400)
        d = date.fromisoformat(ds)
        doc = read_report_json(d)
        if doc is None:
            return _json_response({"error": "relatório não encontrado", "date": ds}, 404)
        return _json_response(doc)
    except Exception as e:
        return _json_response({"error": str(e)}, 400)
