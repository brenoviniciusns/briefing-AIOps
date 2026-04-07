"""Simula ingestão até PUT RAW: RSS + janela D-1 UTC (só ontem) → check-id → upload blob (alinhado ao workflow n8n)."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, time, timedelta, timezone
from email.utils import parsedate_to_datetime

# Espelho de allowlist_rss.yaml (lista completa para testes locais)
FEEDS = [
    ("https://netflixtechblog.com/feed", "netflix"),
    ("https://www.uber.com/blog/engineering/rss/", "uber"),
    ("https://medium.com/feed/airbnb-engineering", "airbnb"),
    ("https://www.databricks.com/blog/feed", "databricks"),
    ("https://openai.com/blog/rss.xml", "openai"),
    ("https://huggingface.co/blog/feed.xml", "huggingface"),
    ("https://www.deeplearning.ai/the-batch/feed/", "deeplearning-ai"),
    ("https://azure.microsoft.com/en-us/updates/feed/", "azure-updates"),
    ("https://azure.microsoft.com/en-us/blog/feed/", "azure-blog"),
    ("https://devblogs.microsoft.com/semantic-kernel/feed/", "ms-semantic-kernel"),
    ("https://devblogs.microsoft.com/azure-sdk/feed/", "azure-sdk-devblog"),
    ("https://www.microsoft.com/en-us/research/feed/", "ms-research"),
    ("https://pytorch.org/blog/feed.xml", "pytorch"),
    ("https://blog.tensorflow.org/feeds/posts/default?alt=rss", "tensorflow-blog"),
    ("https://blogs.nvidia.com/feed/", "nvidia-blog"),
    ("https://tdan.com/feed", "tdan"),
]

ACCOUNT = "tinsourcingdevstuixu7snh"
RG = "rg-treinamento-insourcing-dev"
FUNC = "tinsourcing-dev-func-uixu7snhv7bsw"
FUNC_HOST = f"https://{FUNC}.azurewebsites.net"


def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def parse_items(xml: str, source: str) -> list[tuple[str, str, str, str]]:
    items: list[tuple[str, str, str, str]] = []
    if "<entry" in xml:
        for m in re.finditer(r"<entry[^>]*>([\s\S]*?)</entry>", xml, re.I):
            block = m.group(1)
            lm = re.search(r'<link[^>]+href="([^"]+)"', block, re.I) or re.search(
                r"<link[^>]*>([^<]+)</link>", block, re.I
            )
            tm = re.search(r"<title[^>]*>([\s\S]*?)</title>", block, re.I)
            pm = re.search(r"<published>([^<]+)</published>", block, re.I) or re.search(
                r"<updated>([^<]+)</updated>", block, re.I
            )
            if not (lm and pm):
                continue
            link = lm.group(1).strip()
            title = (tm.group(1) if tm else link).replace("<![CDATA[", "").replace("]]>", "").strip()
            pub = pm.group(1).strip()
            items.append((link, title, pub, source))
        return items
    for m in re.finditer(r"<item[^>]*>([\s\S]*?)</item>", xml, re.I):
        block = m.group(1)
        lm = re.search(r"<link[^>]*>([^<]*)</link>", block, re.I)
        tm = re.search(r"<title[^>]*>([\s\S]*?)</title>", block, re.I)
        pm = re.search(r"<pubDate>([^<]*)</pubDate>", block, re.I)
        if not (lm and pm):
            continue
        link = lm.group(1).strip()
        title = (tm.group(1) if tm else link).replace("<![CDATA[", "").replace("]]>", "").strip()
        pub = pm.group(1).strip()
        items.append((link, title, pub, source))
    return items


def fetch_hacker_news(
    start: datetime, end: datetime, source: str = "hackernews"
) -> list[tuple[str, str, str, str]]:
    """API oficial HN (Firebase). Retorna (url, title, published_iso, source)."""
    base = "https://hacker-news.firebaseio.com/v0"
    req = urllib.request.Request(
        f"{base}/newstories.json", headers={"User-Agent": "n8n-tech-intelligence/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            ids = json.loads(r.read().decode())
    except Exception:
        return []
    if not isinstance(ids, list):
        return []
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    out: list[tuple[str, str, str, str]] = []
    for hid in ids[:120]:
        try:
            req2 = urllib.request.Request(
                f"{base}/item/{hid}.json", headers={"User-Agent": "n8n-tech-intelligence/1.0"}
            )
            with urllib.request.urlopen(req2, timeout=20) as r2:
                it = json.loads(r2.read().decode())
        except Exception:
            continue
        if not it or it.get("type") != "story" or not it.get("time"):
            continue
        t_ms = int(it["time"]) * 1000
        if not (start_ms <= t_ms <= end_ms):
            continue
        url = it.get("url") or f"https://news.ycombinator.com/item?id={hid}"
        title = (it.get("title") or url).strip()
        pub_iso = datetime.fromtimestamp(int(it["time"]), tz=timezone.utc).isoformat()
        out.append((url, title, pub_iso, source))
    return out


def parse_pub(pub: str) -> datetime | None:
    try:
        return datetime.fromisoformat(pub.replace("Z", "+00:00"))
    except Exception:
        try:
            t = parsedate_to_datetime(pub)
            if t.tzinfo is None:
                t = t.replace(tzinfo=timezone.utc)
            return t.astimezone(timezone.utc)
        except Exception:
            return None


def az(*args: str) -> str:
    line = subprocess.list2cmdline(("az",) + args)
    r = subprocess.run(line, capture_output=True, text=True, check=True, shell=True)
    return r.stdout.strip()


def main() -> int:
    now = datetime.now(timezone.utc)
    yesterday = (now - timedelta(days=1)).date()
    start = datetime.combine(yesterday, time(0, 0, 0), tzinfo=timezone.utc)
    end = datetime.combine(yesterday, time(23, 59, 59, 999000), tzinfo=timezone.utc)
    print("WINDOW_D1_UTC", start.isoformat(), "->", end.isoformat())

    candidates: list[dict] = []
    for url, src in FEEDS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "n8n-tech-intelligence/1.0"})
            xml = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", errors="replace")
            for link, title, pub, source in parse_items(xml, src):
                t = parse_pub(pub)
                if t is None or not (start <= t <= end):
                    continue
                pid = sha256(link)
                pd = t.astimezone(timezone.utc)
                yy, mm, dd = pd.year, f"{pd.month:02d}", f"{pd.day:02d}"
                candidates.append(
                    {
                        "id": pid,
                        "source": source,
                        "title": title,
                        "url": link,
                        "published_at": pd.isoformat(),
                        "published_date": pd.date().isoformat(),
                        "blob_path": f"raw/year={yy}/month={mm}/day={dd}/source={source}/{pid}.json",
                    }
                )
        except Exception as e:
            print("FEED_FAIL", src, e)

    try:
        for link, title, pub, src in fetch_hacker_news(start, end):
            t = parse_pub(pub)
            if t is None or not (start <= t <= end):
                continue
            pid = sha256(link)
            pd = t.astimezone(timezone.utc)
            yy, mm, dd = pd.year, f"{pd.month:02d}", f"{pd.day:02d}"
            candidates.append(
                {
                    "id": pid,
                    "source": src,
                    "title": title,
                    "url": link,
                    "published_at": pd.isoformat(),
                    "published_date": pd.date().isoformat(),
                    "blob_path": f"raw/year={yy}/month={mm}/day={dd}/source={src}/{pid}.json",
                }
            )
    except Exception as e:
        print("HACKERNEWS_FAIL", e)

    if not candidates:
        print("Nenhum item na janela D-1 UTC nos feeds de teste; usar primeiro item HuggingFace para demo de pipeline.")
        url, src = FEEDS[5]
        req = urllib.request.Request(url, headers={"User-Agent": "n8n-tech-intelligence/1.0"})
        xml = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", errors="replace")
        items = parse_items(xml, src)
        if not items:
            print("ERRO: sem itens RSS")
            return 1
        link, title, pub, source = items[0]
        t = parse_pub(pub) or datetime.now(timezone.utc)
        pid = sha256(link)
        pd = t.astimezone(timezone.utc)
        yy, mm, dd = pd.year, f"{pd.month:02d}", f"{pd.day:02d}"
        candidates.append(
            {
                "id": pid,
                "source": source,
                "title": title,
                "url": link,
                "published_at": pd.isoformat(),
                "published_date": pd.date().isoformat(),
                "blob_path": f"raw/year={yy}/month={mm}/day={dd}/source={source}/{pid}.json",
            }
        )

    art = candidates[0]
    print("ARTIGO", json.dumps(art, ensure_ascii=False)[:500])

    func_key = az(
        "functionapp",
        "keys",
        "list",
        "-g",
        RG,
        "-n",
        FUNC,
        "--query",
        "functionKeys.default",
        "-o",
        "tsv",
    )
    check_url = (
        f"{FUNC_HOST}/api/check-id?id={art['id']}&source={art['source']}"
        f"&published_date={art['published_date']}"
    )
    req = urllib.request.Request(
        check_url,
        headers={"x-functions-key": func_key},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        check_body = json.loads(resp.read().decode())
    print("CHECK_ID", check_body)

    body_obj = {
        "id": art["id"],
        "source": art["source"],
        "title": art["title"],
        "url": art["url"],
        "published_at": art["published_at"],
        "summary": "",
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }
    raw_json = json.dumps(body_obj, ensure_ascii=False).encode("utf-8")

    stkey = az(
        "storage",
        "account",
        "keys",
        "list",
        "-g",
        RG,
        "-n",
        ACCOUNT,
        "--query",
        "[0].value",
        "-o",
        "tsv",
    )
    # blob_path no n8n = raw/year=.../... ; contentor = raw → nome do blob = year=.../...
    tmp = json.dumps(body_obj, ensure_ascii=False)
    open_path = art["blob_path"][4:] if art["blob_path"].startswith("raw/") else art["blob_path"]

    # Upload via az storage blob (equiv. ao PUT HTTP do n8n)
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        f.write(tmp)
        tmp_path = f.name

    az(
        "storage",
        "blob",
        "upload",
        "--account-name",
        ACCOUNT,
        "--container-name",
        "raw",
        "--name",
        open_path,
        "--file",
        tmp_path,
        "--auth-mode",
        "key",
        "--account-key",
        stkey,
        "--overwrite",
    )
    print("PUT_RAW_OK", "raw", open_path, "bytes", len(raw_json))
    return 0


if __name__ == "__main__":
    sys.exit(main())
