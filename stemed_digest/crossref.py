"""New articles from journals, via the Crossref REST API.

Articles are selected by the date they were registered with Crossref ("created"), not
by publication date: some journals record only a year (e.g. "2026"), and online-first
articles carry a later issue date, so a publication-date filter silently misses them.
"""
import html
import re
from typing import Iterable, List

from . import keywords
from .disciplines import DISCIPLINES, matching_disciplines
from .http import get_json
from .models import Item, utc_stamp

API = "https://api.crossref.org"
FIELDS = "DOI,URL,title,author,container-title,created,published,issued,type,abstract"
# Abstracts are used only to match keywords. They are never stored or shown.

# Issue furniture and notices that are not research or practice articles.
SKIP_TITLE = re.compile(
    r"^\s*(?:issue information|editorial board|front matter|back matter|table of contents|contents|masthead"
    r"|cover image|acknowledge?ments?|index|thank(?:s| you) to (?:our )?reviewers.*|reviewers?(?: \d{4})?"
    r"|(?:correction|corrigendum|erratum)\b.*)\s*$",
    re.IGNORECASE,
)


def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text or "")          # Crossref titles may carry JATS/HTML tags
    return " ".join(html.unescape(text).split())        # ...and entities such as "&amp;"


def _date(parts_holder: dict) -> str:
    try:
        parts = parts_holder["date-parts"][0]
    except (KeyError, IndexError, TypeError):
        return ""
    return "-".join(f"{p:02d}" if i else str(p) for i, p in enumerate(parts) if p)


def _authors(work: dict) -> List[str]:
    names = []
    for a in work.get("author") or []:
        name = " ".join(x for x in (a.get("given"), a.get("family")) if x) or a.get("name", "")
        if name:
            names.append(_clean(name))
    return names


def parse_works(works: Iterable[dict], journal: dict) -> List[Item]:
    items = []
    for w in works:
        if w.get("type") != "journal-article":
            continue
        title = _clean((w.get("title") or [""])[0])
        if not title or SKIP_TITLE.match(title):
            continue
        disciplines = [d for d in journal.get("disciplines", []) if d in DISCIPLINES]
        if journal.get("classify_titles"):
            disciplines += [d for d in matching_disciplines(title) if d not in disciplines]
        doi = w["DOI"].lower()
        items.append(Item(
            id=f"doi:{doi}",
            source="journal",
            title=title,
            authors=_authors(w),
            venue=journal["name"],
            url=w.get("URL") or f"https://doi.org/{doi}",
            added=utc_stamp((w.get("created") or {}).get("date-time", "")),
            published=_date(w.get("published") or w.get("issued") or {}),
            kind="Journal article",
            disciplines=[d for d in DISCIPLINES if d in disciplines],
            keywords=keywords.match([title, html.unescape(w.get("abstract") or "")]),
        ))
    return items


def fetch_journal(journal: dict, since: str, rows: int = 1000) -> List[Item]:
    """Articles registered on or after `since` (YYYY-MM-DD)."""
    data = get_json(f"{API}/journals/{journal['issn']}/works", {
        "filter": f"from-created-date:{since}",
        "sort": "created", "order": "desc", "rows": rows, "select": FIELDS,
    })
    return parse_works(data["message"]["items"], journal)
