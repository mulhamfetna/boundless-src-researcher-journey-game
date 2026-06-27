import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from fetch_papers import parse_doaj

SAMPLE = json.dumps({"results": [{
    "id": "abc123",
    "bibjson": {
        "title": "A Study of X",
        "abstract": "We propose a method and evaluate it.",
        "journal": {"title": "Journal of Open Research"},
        "author": [{"name": "A. Researcher"}],
    }}]})


def test_parse_doaj():
    cands = parse_doaj(SAMPLE)
    assert len(cands) == 1
    c = cands[0]
    assert c["title"] == "A Study of X"
    assert c["journal"] == "Journal of Open Research"
    assert "method" in c["abstract"]
    assert c["source_url"] == "https://doaj.org/article/abc123"
    assert c["authors"] == ["A. Researcher"]
