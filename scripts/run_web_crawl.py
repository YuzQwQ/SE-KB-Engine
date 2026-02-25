import argparse
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.webpage_crawler import WebpageCrawler
import httpx
from llm_client import _load_env_file

def _read_url_file(path: str):
    urls = []
    p = Path(path)
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            urls.append(s)
    return urls

def _fetch_urls(api: str, query: str = "", limit: int = 20):
    try:
        headers = {}
        key = os.getenv("SEARCH_API_KEY")
        if key:
            headers["Authorization"] = f"Bearer {key}"
        with httpx.Client(timeout=20.0) as client:
            resp = client.get(api, params={"q": query, "limit": limit}, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                return [str(u) for u in data]
            urls = data.get("urls") or data.get("data") or []
            return [str(u) for u in urls]
    except Exception:
        return []

def _fetch_serp_urls(query: str, limit: int = 20, engine: str = "google"):
    _load_env_file()
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        return []
    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.get(
                "https://serpapi.com/search.json",
                params={"engine": engine, "q": query, "api_key": api_key, "num": max(10, limit)},
            )
            resp.raise_for_status()
            data = resp.json()
            urls = []
            for item in data.get("organic_results", [])[:limit]:
                link = item.get("link")
                if link:
                    urls.append(link)
            return urls
    except Exception:
        return []

def main():
    p = argparse.ArgumentParser()
    p.add_argument("urls", nargs="*", help="要爬取的网页 URL 列表")
    p.add_argument("--data-dir", default="data")
    p.add_argument("--url-file")
    p.add_argument("--url-api")
    p.add_argument("--query", default="")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--serp", action="store_true")
    p.add_argument("--engine", default="google")
    args = p.parse_args()
    wc = WebpageCrawler(data_dir=args.data_dir)
    collected = []
    collected.extend(args.urls or [])
    if args.url_file:
        collected.extend(_read_url_file(args.url_file))
    if args.url_api:
        collected.extend(_fetch_urls(args.url_api, args.query, args.limit))
    if args.serp and args.query:
        collected.extend(_fetch_serp_urls(args.query, args.limit, args.engine))
    seen = set()
    final_urls = []
    for u in collected:
        if u and u not in seen:
            seen.add(u)
            final_urls.append(u)
    for u in final_urls:
        try:
            res = wc.crawl_and_parse(u, save_data=True)
            print({"url": u, "files": res.get("file_paths")})
        except Exception as e:
            print({"url": u, "error": str(e)})

if __name__ == "__main__":
    main()