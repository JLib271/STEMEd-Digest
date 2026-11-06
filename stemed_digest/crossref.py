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


def _year(holder: dict) -> int:
    try:
        return int(holder["date-parts"][0][0])
    except (KeyError, IndexError, TypeError, ValueError):
        return 0


def is_back_catalog(work: dict) -> bool:
    """Publishers sometimes re-register old issues (in 2026, Journal of Nursing Education
    re-registered articles back to 1962). Anything published more than a year before it
    was registered is an old article, not a new one."""
    published = _year(work.get("published") or work.get("issued") or {})
    registered = _year(work.get("created") or {}) or int((work.get("created") or {}).get("date-time", "0")[:4] or 0)
    return bool(published and registered and published < registered - 1)


def parse_works(works: Iterable[dict], journal: dict) -> List[Item]:
    items = []
    for w in works:
        if w.get("type") != "journal-article" or is_back_catalog(w):
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


def fetch_journal(journal: dict, since: str, rows: int = 1000, max_pages: int = 20) -> List[Item]:
    """Articles registered on or after `since` (YYYY-MM-DD), following Crossref's cursor
    through as many pages as needed (a busy journal registers well over 1,000 a year)."""
    works, cursor = [], "*"
    for _ in range(max_pages):
        data = get_json(f"{API}/journals/{journal['issn']}/works", {
            "filter": f"from-created-date:{since},type:journal-article",
            "rows": rows, "select": FIELDS, "cursor": cursor,
        })["message"]
        works.extend(data["items"])
        cursor = data.get("next-cursor")
        if not data["items"] or len(data["items"]) < rows or not cursor:
            break
    return parse_works(works, journal)
