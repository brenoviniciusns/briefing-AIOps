from __future__ import annotations

import json
import logging
import os
from datetime import date, timedelta
from typing import Any, Iterator

from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from azure.storage.filedatalake import DataLakeServiceClient

from shared.config import (
    container_raw,
    container_reports,
    get_adls_connection_string,
    storage_account_name,
    use_managed_identity_data_plane,
)

logger = logging.getLogger(__name__)


def _service() -> DataLakeServiceClient:
    name = storage_account_name()
    if use_managed_identity_data_plane() and name:
        account_url = f"https://{name}.dfs.core.windows.net"
        return DataLakeServiceClient(account_url=account_url, credential=DefaultAzureCredential())
    direct = os.environ.get("ADLS_CONNECTION_STRING", "").strip()
    if direct:
        return DataLakeServiceClient.from_connection_string(direct)
    cs = get_adls_connection_string()
    if not cs:
        raise RuntimeError("ADLS_CONNECTION_STRING ou AzureWebJobsStorage não configurado.")
    return DataLakeServiceClient.from_connection_string(cs)


def _blob_service() -> BlobServiceClient:
    """Blob API (HTTPS) para relatórios — evita PathNotFound intermitente do DFS com connection string blob."""
    name = storage_account_name()
    if use_managed_identity_data_plane() and name:
        return BlobServiceClient(
            account_url=f"https://{name}.blob.core.windows.net",
            credential=DefaultAzureCredential(),
        )
    direct = os.environ.get("ADLS_CONNECTION_STRING", "").strip()
    if direct:
        return BlobServiceClient.from_connection_string(direct)
    cs = get_adls_connection_string()
    if not cs:
        raise RuntimeError("ADLS_CONNECTION_STRING ou AzureWebJobsStorage não configurado.")
    return BlobServiceClient.from_connection_string(cs)


def raw_blob_path(source: str, article_id: str, published: date) -> str:
    y = published.year
    m = f"{published.month:02d}"
    d = f"{published.day:02d}"
    return f"raw/year={y}/month={m}/day={d}/source={source}/{article_id}.json"


def raw_prefix_for_date(published: date) -> str:
    y = published.year
    m = f"{published.month:02d}"
    d = f"{published.day:02d}"
    return f"raw/year={y}/month={m}/day={d}/"


def raw_article_exists(source: str, article_id: str, published: date) -> bool:
    path = raw_blob_path(source, article_id, published)
    fs = _service().get_file_system_client(container_raw())
    fc = fs.get_file_client(path)
    try:
        return fc.exists()
    except Exception:
        logger.exception("Erro ao verificar existência de %s", path)
        raise


def iter_raw_articles_for_date(published: date) -> Iterator[dict[str, Any]]:
    prefix = raw_prefix_for_date(published)
    fs = _service().get_file_system_client(container_raw())

    def _path_not_found(exc: BaseException) -> bool:
        if isinstance(exc, ResourceNotFoundError):
            return True
        if isinstance(exc, HttpResponseError):
            code = getattr(getattr(exc, "error", None), "code", None) or getattr(exc, "error_code", None) or ""
            if exc.status_code == 404 or str(code) == "PathNotFound" or "PathNotFound" in str(exc):
                return True
        msg = str(exc).lower()
        return "pathnotfound" in msg.replace(" ", "") or "path does not exist" in msg

    try:
        paths = fs.get_paths(path=prefix, recursive=True)
        for p in paths:
            if not p.name.endswith(".json"):
                continue
            fc = fs.get_file_client(p.name)
            try:
                downloader = fc.download_file()
                data = downloader.readall()
                yield json.loads(data.decode("utf-8"))
            except Exception:
                logger.exception("Falha ao ler RAW %s", p.name)
    except ResourceNotFoundError:
        logger.info("Prefixo RAW inexistente: %s", prefix)
        return
    except HttpResponseError as e:
        if _path_not_found(e):
            logger.info("Prefixo RAW inexistente (HTTP %s): %s", e.status_code, prefix)
            return
        raise
    except Exception as e:
        if _path_not_found(e):
            logger.info("Prefixo RAW inexistente: %s (%s)", prefix, e)
            return
        raise


def write_report_json(report_date: date, body: dict[str, Any], archive: bool) -> str:
    name = f"daily-report-{report_date.isoformat()}.json"
    blob_name = name
    if archive:
        import uuid

        blob_name = f"archive/run_id={uuid.uuid4()}/{name}"
    data = json.dumps(body, ensure_ascii=False, indent=2).encode("utf-8")
    bc = _blob_service().get_blob_client(container_reports(), blob_name)
    bc.upload_blob(data, overwrite=True)
    return blob_name


def read_report_json(report_date: date) -> dict[str, Any] | None:
    blob_name = f"daily-report-{report_date.isoformat()}.json"
    bc = _blob_service().get_blob_client(container_reports(), blob_name)
    if not bc.exists():
        return None
    raw = bc.download_blob().readall()
    return json.loads(raw.decode("utf-8"))


LINKEDIN_FEATURED_IDS_BLOB = "linkedin-featured-article-ids.json"
_MAX_FEATURED_IDS = 8000


def read_featured_article_ids() -> set[str]:
    """Ids de artigos já sugeridos para tópicos LinkedIn (anti-repetição de reportagem)."""
    bc = _blob_service().get_blob_client(container_reports(), LINKEDIN_FEATURED_IDS_BLOB)
    if not bc.exists():
        return set()
    try:
        data = json.loads(bc.download_blob().readall().decode("utf-8"))
    except Exception:
        logger.exception("Falha ao ler %s", LINKEDIN_FEATURED_IDS_BLOB)
        return set()
    ids = data.get("ids") if isinstance(data, dict) else []
    out: set[str] = set()
    for x in ids:
        if isinstance(x, str) and len(x) == 64 and all(c in "0123456789abcdef" for c in x.lower()):
            out.add(x.lower())
    return out


def append_featured_article_ids(new_ids: list[str]) -> None:
    cur = read_featured_article_ids()
    for x in new_ids:
        s = str(x).strip().lower()
        if len(s) == 64 and all(c in "0123456789abcdef" for c in s):
            cur.add(s)
    sorted_ids = sorted(cur)
    if len(sorted_ids) > _MAX_FEATURED_IDS:
        sorted_ids = sorted_ids[-_MAX_FEATURED_IDS:]
    payload = json.dumps({"ids": sorted_ids}, ensure_ascii=False, indent=2).encode("utf-8")
    bc = _blob_service().get_blob_client(container_reports(), LINKEDIN_FEATURED_IDS_BLOB)
    bc.upload_blob(payload, overwrite=True)


def iter_raw_articles_date_range(start: date, end: date) -> Iterator[dict[str, Any]]:
    """Itera todos os artigos RAW entre start e end (inclusive), por dia de partição."""
    if start > end:
        return
    d = start
    while d <= end:
        yield from iter_raw_articles_for_date(d)
        d += timedelta(days=1)
