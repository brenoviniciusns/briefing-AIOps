from __future__ import annotations

import logging
from typing import Any

import pyarrow as pa
from deltalake import DeltaTable, write_deltalake

from shared.config import delta_storage_options, delta_table_uri

logger = logging.getLogger(__name__)

_SCHEMA = pa.schema(
    [
        ("id", pa.string()),
        ("source", pa.string()),
        ("title", pa.string()),
        ("url", pa.string()),
        ("published_at", pa.string()),
        ("category", pa.string()),
        ("score", pa.int32()),
        ("summary", pa.string()),
        ("ingested_at", pa.string()),
        ("processing_run_id", pa.string()),
    ]
)


def upsert_articles(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    uri = delta_table_uri()
    opts = delta_storage_options()
    table = pa.Table.from_pylist(rows, schema=_SCHEMA)

    if not DeltaTable.is_deltatable(uri, storage_options=opts):
        logger.info("Criar tabela Delta inicial em %s", uri)
        write_deltalake(uri, table, mode="overwrite", storage_options=opts)
        return

    dt = DeltaTable(uri, storage_options=opts)
    try:
        (
            dt.merge(
                source=table,
                predicate="target.id = source.id",
                source_alias="source",
                target_alias="target",
            )
            .when_matched_update_all()
            .when_not_matched_insert_all()
            .execute()
        )
    except Exception:
        logger.exception("Merge Delta falhou; a tentar append apenas de novos ids.")
        existing = dt.to_pyarrow_table().select(["id"]).to_pylist()
        have = {r["id"] for r in existing}
        fresh = [r for r in rows if r["id"] not in have]
        if fresh:
            write_deltalake(
                uri,
                pa.Table.from_pylist(fresh, schema=_SCHEMA),
                mode="append",
                storage_options=opts,
            )
