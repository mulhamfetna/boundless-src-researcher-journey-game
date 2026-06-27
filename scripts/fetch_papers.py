"""Fetch open-access paper candidates from DOAJ for curating applied questions.

Read-only research aid. Usage:
  python scripts/fetch_papers.py "research gap" 10 > content/papers/foundations.json
"""
import json
import sys
import urllib.parse
import urllib.request


def parse_doaj(body: str) -> list[dict]:
    data = json.loads(body)
    out = []
    for r in data.get("results", []):
        bib = r.get("bibjson", {})
        out.append({
            "title": bib.get("title", ""),
            "journal": (bib.get("journal") or {}).get("title", ""),
            "abstract": bib.get("abstract", ""),
            "authors": [a.get("name", "") for a in bib.get("author", []) if a.get("name")],
            "source_url": f"https://doaj.org/article/{r.get('id', '')}",
        })
    return out


def fetch(query: str, page_size: int = 10) -> list[dict]:
    q = urllib.parse.quote(query)
    url = f"https://doaj.org/api/search/articles/{q}?pageSize={page_size}"
    req = urllib.request.Request(url, headers={"User-Agent": "research-quiz/1.0"})
    body = urllib.request.urlopen(req, timeout=20).read().decode()
    return [c for c in parse_doaj(body) if c["abstract"]]


if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "research methodology"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    print(json.dumps(fetch(query, n), ensure_ascii=False, indent=2))
