"""Injeta n8n/snippets/delivery-email-html.js nos workflows de entrega."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = (ROOT / "n8n/snippets/delivery-email-html.js").read_text(encoding="utf-8")


def main() -> None:
    for rel in ("n8n/workflows/delivery.json", "n8n/workflow-delivery.json"):
        p = ROOT / rel
        wf = json.loads(p.read_text(encoding="utf-8"))
        wf["name"] = "Daily Tech Intel — Entrega (LinkedIn + email / Slack)"
        for node in wf["nodes"]:
            if node.get("name") == "Data relatório D-1 UTC":
                node["name"] = "Data relatório (fim janela UTC)"
            if node.get("name") == "HTML email + texto Slack":
                node.setdefault("parameters", {})["jsCode"] = CODE
        nc: dict = {}
        for k, v in wf["connections"].items():
            nk = "Data relatório (fim janela UTC)" if k == "Data relatório D-1 UTC" else k
            nc[nk] = v
            for branch in v.get("main", []):
                for edge in branch:
                    if edge.get("node") == "Data relatório D-1 UTC":
                        edge["node"] = "Data relatório (fim janela UTC)"
        wf["connections"] = nc
        p.write_text(json.dumps(wf, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("updated", rel)


if __name__ == "__main__":
    main()
