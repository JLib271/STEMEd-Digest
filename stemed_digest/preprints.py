"""New preprints from EdArXiv (via the OSF API) and arXiv's physics education category.

EdArXiv covers all of education, so only STEM+ preprints are kept (see is_stem). Every
arXiv physics.ed-ph preprint is kept. Abstracts are used only to match keywords; they
are never stored or shown.
"""
import datetime as dt
import html
import re
import time
from typing import Iterable, List, Optional, Tuple
from xml.etree import ElementTree as ET

from . import keywords
from .disciplines import DISCIPLINES, matching_disciplines
from .http import get_json, get_text
from .models import Item, utc_stamp

# Phrases that contain a STEM field name without being about that field.
NOT_STEM = re.compile(
    r"\b(?:prompt|context|social|human) engineer\w*|\bre-?engineer\w*"
    r"|\bscience of (?:learning|reading|teaching)\b"
    r"|\b(?:social|political|learning|cognitive|behaviou?ral|library|information|educational|education"
    r"|implementation|improvement) sciences?\b"
    r"|\b(?:school|classroom|campus|organi[sz]ational|institutional) climate\b",
    re.IGNORECASE,
)
# STEM+ words that are not discipline names, with the discipline each implies (if any).
WORD_DISCIPLINES = (
    ("Mathematics", re.compile(r"\bmaths?\b|\bmathematical\b|\bgeometr(?:y|ic|ical)\b|\balgebra\w*|\bcalculus\b"
                               r"|\bfractions?\b|\bnumeracy\b|\barithmetic\b|\bstatistical\b|\bdata science\b", re.IGNORECASE)),
    ("Engineering", re.compile(r"\bcomputer science\b|\bcomputing\b|\bcomputational thinking\b|\bprogramming\b"
                               r"|\bcoding\b|\brobotics\b", re.IGNORECASE)),
    ("Health Education", re.compile(r"\bbiomedical\b|\bclinical\b|\bpatients?\b", re.IGNORECASE)),
)
STEM_WORDS = re.compile(r"\b(?-i:STEM|STEAM|STEMM)\b|\bsciences?\b|\bscientific\b|\bscientists?\b|\bocean literacy\b",
                        re.IGNORECASE)


def stem_disciplines(text: str) -> Tuple[bool, List[str]]:
    """(is it STEM+?, the disciplines it names). Learning Science alone does not count:
    its terms (educational technology, learning design) cover every subject."""
    text = NOT_STEM.sub(" ", text)
    found = [d for d in matching_disciplines(text) if d != "Learning Science"]
    found += [d for d, pattern in WORD_DISCIPLINES if d not in found and pattern.search(text)]
    return bool(found or STEM_WORDS.search(text)), _ordered(found)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", text or ""))).strip()


def _ordered(found: Iterable[str]) -> List[str]:
    found = set(found)
    return [d for d in DISCIPLINES if d in found]


# ---- EdArXiv -------------------------------------------------------------------------

def is_stem(title: str, tags: List[str], subjects: List[str], stem_subjects: Iterable[str]) -> Tuple[bool, List[str]]:
    """Kept when the title names a STEM+ field or word, or when the author filed it under a
    STEM subject and its keywords name one. Tags alone are not enough: authors often paste
    long keyword strings that mention 'engineering' or 'health' in passing."""
    ok, found = stem_disciplines(title)
    if ok:
        return True, found
    if set(subjects) & set(stem_subjects):
        ok, found = stem_disciplines(" ; ".join(tags))
        if ok:
            return True, found
    return False, []


def _osf_authors(record: dict) -> List[str]:
    people = (record.get("embeds") or {}).get("contributors", {}).get("data") or []
    names = []
    for c in people:
        if not c.get("attributes", {}).get("bibliographic", True):
            continue
        user = ((c.get("embeds") or {}).get("users") or {}).get("data") or {}
        name = (user.get("attributes") or {}).get("full_name") or c.get("attributes", {}).get("unregistered_contributor")
        if name:
            names.append(_clean(name))
    return names


def parse_osf(records: Iterable[dict], config: dict, since: str) -> List[Item]:
    items = []
    for r in records:
        a = r.get("attributes") or {}
        if not a.get("is_latest_version", True) or a.get("date_withdrawn") or not a.get("is_published", True):
            continue
        added = utc_stamp(a.get("date_published") or a.get("date_created") or "")
        if added[:10] < since:
            continue
        title = _clean(a.get("title"))
        tags = [_clean(t) for t in a.get("tags") or []]
        subjects = [s.get("text", "") for path in a.get("subjects") or [] for s in path]
        ok, found = is_stem(title, tags, subjects, config.get("stem_subjects", []))
        if not title or not ok:
            continue
        base = r["id"].split("_")[0]
        links = r.get("links") or {}
        items.append(Item(
            id=f"osf:{base}",
            source="preprint",
            title=title,
            authors=_osf_authors(r),
            venue=config["name"],
            url=f"https://osf.io/preprints/{config['provider']}/{base}",
            added=added,
            published=added[:10],
            kind="Preprint",
            disciplines=_ordered(found or ["Science Education"]),
            keywords=keywords.match([title, " ; ".join(tags), _clean(a.get("description"))]),
            version_of=(a.get("doi") or "").lower().replace("https://doi.org/", ""),
        ))
    return items


def fetch_edarxiv(config: dict, since: str, max_pages: int = 40) -> List[Item]:
    """Preprints that appeared on or after `since` (YYYY-MM-DD). Moderation can take a few
    weeks, so the request reaches back 30 days before `since` by submission date and the
    result is then cut by the date each preprint went public."""
    start = (dt.date.fromisoformat(since) - dt.timedelta(days=30)).isoformat()
    url: Optional[str] = config["api"]
    params: Optional[dict] = {
        "filter[provider]": config["provider"], "filter[date_created][gte]": start,
        "page[size]": 100, "embed": "contributors", "sort": "-date_created",
    }
    records: List[dict] = []
    for _ in range(max_pages):
        data = get_json(url, params)
        records += data.get("data") or []
        url, params = (data.get("links") or {}).get("next"), None
        if not url:
            break
    return parse_osf(records, config, since)


# ---- arXiv ---------------------------------------------------------------------------

ATOM = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def parse_arxiv(feed: str, config: dict, since: str) -> Tuple[List[Item], bool]:
    """Items on or after `since`, and whether the feed reached back past `since`
    (newest first, so older entries mean there is nothing more to fetch)."""
    root = ET.fromstring(feed)
    items, done = [], False
    for e in root.findall("a:entry", ATOM):
        added = utc_stamp(e.findtext("a:published", "", ATOM))
        if added[:10] < since:
            done = True
            continue
        abs_id = e.findtext("a:id", "", ATOM).rsplit("/abs/", 1)[-1]
        base = re.sub(r"v\d+$", "", abs_id)
        title = _clean(e.findtext("a:title", "", ATOM))
        if not base or not title:
            continue
        summary = _clean(e.findtext("a:summary", "", ATOM))
        _, found = stem_disciplines(title)
        items.append(Item(
            id=f"arxiv:{base}",
            source="preprint",
            title=title,
            authors=[_clean(n.text) for n in e.findall("a:author/a:name", ATOM) if n.text],
            venue=config["name"],
            url=f"https://arxiv.org/abs/{base}",
            added=added,
            published=added[:10],
            kind="Preprint",
            disciplines=_ordered(list(config.get("disciplines", [])) + found),
            keywords=keywords.match([title, summary]),
            version_of=(e.findtext("arxiv:doi", "", ATOM) or "").strip().lower(),
        ))
    return items, done


def fetch_arxiv(config: dict, since: str, page: int = 200, max_pages: int = 10, pause: float = 3.0) -> List[Item]:
    """arXiv asks for no more than one request every three seconds."""
    items: List[Item] = []
    for n in range(max_pages):
        if n:
            time.sleep(pause)
        feed = get_text(config["api"], {
            "search_query": f"cat:{config['category']}", "sortBy": "submittedDate", "sortOrder": "descending",
            "start": n * page, "max_results": page,
        }, accept="application/atom+xml")
        got, done = parse_arxiv(feed, config, since)
        items += got
        if done or len(ET.fromstring(feed).findall("a:entry", ATOM)) < page:
            break
    return items
