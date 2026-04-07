#!/usr/bin/env python3
"""Copia workflows canónicos da raiz n8n/ para n8n/workflows/ (espelho versionado)."""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAIRS = [
    (ROOT / "n8n" / "workflow-ingestion.json", ROOT / "n8n" / "workflows" / "ingestion.json"),
    (ROOT / "n8n" / "workflow-delivery.json", ROOT / "n8n" / "workflows" / "delivery.json"),
]


def main() -> int:
    for src, dst in PAIRS:
        if not src.is_file():
            print("SKIP (origem em falta):", src)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print("OK", src.name, "->", dst.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
