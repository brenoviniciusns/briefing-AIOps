from __future__ import annotations

import re
from typing import Literal

Category = Literal["AI", "Architecture", "Data"]

_AI_KW = re.compile(
    r"\b(llm|gpt|transformer|neural|model training|fine-?tun|rag|embedding|"
    r"openai|hugging\s*face|inference|gpu|mlops|genai|generative)\b",
    re.I,
)
_ARCH_KW = re.compile(
    r"\b(microservice|kubernetes|k8s|service mesh|istio|lambda|serverless|"
    r"scalability|reliability|sre|observability|distributed|load balanc|"
    r"cdn|edge|latency|architecture|platform engineering)\b",
    re.I,
)
_DATA_KW = re.compile(
    r"\b(spark|delta|lakehouse|warehouse|etl|elt|iceberg|hudi|"
    r"data\s*mesh|catalog|unity|pipeline|streaming|kafka|flink|"
    r"sql|warehouse|fabric|synapse|databricks)\b",
    re.I,
)

_SOURCE_BIAS: dict[str, Category] = {
    "openai": "AI",
    "huggingface": "AI",
    "deeplearning-ai": "AI",
    "netflix": "Architecture",
    "uber": "Architecture",
    "airbnb": "Architecture",
    "databricks": "Data",
    "azure-updates": "Architecture",
}


def classify_text(title: str, summary: str, source: str) -> Category:
    text = f"{title}\n{summary}"
    scores = {
        "AI": len(_AI_KW.findall(text)) + (3 if _SOURCE_BIAS.get(source) == "AI" else 0),
        "Architecture": len(_ARCH_KW.findall(text))
        + (2 if _SOURCE_BIAS.get(source) == "Architecture" else 0),
        "Data": len(_DATA_KW.findall(text)) + (3 if _SOURCE_BIAS.get(source) == "Data" else 0),
    }
    best = max(scores, key=lambda k: scores[k])
    if scores[best] == 0:
        return _SOURCE_BIAS.get(source, "Architecture")
    return best  # type: ignore[return-value]


def relevance_score(title: str, summary: str, category: Category) -> int:
    text = f"{title}\n{summary}"
    base = min(100, 30 + min(40, len(text) // 25))
    if category == "AI":
        base = min(100, base + 10)
    if _AI_KW.search(text) or _DATA_KW.search(text) or _ARCH_KW.search(text):
        base = min(100, base + 15)
    return int(base)
