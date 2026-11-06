"""New dissertations and theses from OpenAlex, limited to STEM+ education topics.

OpenAlex cannot be asked for "indexed since" without a paid plan, so each run asks for
everything published in the time window and keeps the works OpenAlex first indexed
within it. That also drops old theses a repository has re-dated. Abstracts are used only
to match keywords; they are never stored or shown.
"""
import datetime as dt
import os
import re
from typing import Iterable, List, Optional

from . import keywords
from .disciplines import DISCIPLINES
from .http import get_json
from .models import Item, utc_stamp
from .preprints import _clean, stem_disciplines

# Some repositories label non-English theses as English. A title of five or more words
# with none of these common English words is skipped.
ENGLISH = set(
    "the of in and to for a an on with among through from by at as into about how what why when where who which"
    " does do is are be can could during regarding after before between within across toward towards using via"
    " their its our we i not or than this that these under over beyond without versus".split()
)
SELECT = "id,doi,display_name,publication_date,created_date,authorships,primary_location,primary_topic,abstract_inverted_index"


def looks_english(title: str) -> bool:
    words = re.findall(r"[^\W\d_]+", title.lower())
    return len(words) < 5 or bool(ENGLISH & set(words))


def _abstract(inverted: Optional[dict]) -> str:
    if not inverted:
        return ""
    slots = {}
    for word, places in inverted.items():
        for p in places:
            slots[p] = word
    return " ".join(slots[k] for k in sorted(slots))


def _institution(work: dict) -> str:
    """The university: the author's listed institution, else the repository's name, with
    the university taken from the brackets ("Research Portal (Queen's University Belfast)")."""
    for a in work.get("authorships") or []:
        for inst in a.get("institutions") or []:
            if inst.get("display_name"):
                return inst["display_name"]
    source = ((work.get("primary_location") or {}).get("source") or {}).get("display_name") or ""
    inner = re.search(r"\(([^()]*(?:Universit|College|Institut|School)[^()]*)\)\s*$", source)
    return (inner.group(1) if inner else source).strip() or "Dissertation or thesis"


def parse_works(works: Iterable[dict], config: dict, since: str, now: dt.datetime) -> List[Item]:
    topics = config["topics"]
    items = []
    for w in works:
        topic = ((w.get("primary_topic") or {}).get("id") or "").rsplit("/", 1)[-1]
        if topic not in topics:
            continue
        added = utc_stamp(w.get("created_date") or "")
        title = _clean(w.get("display_name"))
        if not title or added[:10] < since or not looks_english(title):
            continue
        published = w.get("publication_date") or ""
        if published > now.strftime("%Y-%m-%d"):          # some repositories give a future date
            published = published[:4]
        found = set(topics[topic]["disciplines"])
        found |= set(stem_disciplines(title)[1])
        location = w.get("primary_location") or {}
        doi = (w.get("doi") or "").lower().replace("https://doi.org/", "")
        work_id = w["id"].rsplit("/", 1)[-1]
        items.append(Item(
            id=f"openalex:{work_id}",
            source="dissertation",
            title=title,
            authors=[_clean((a.get("author") or {}).get("display_name")) for a in w.get("authorships") or []
                     if (a.get("author") or {}).get("display_name")],
            venue=_institution(w),
            url=(f"https://doi.org/{doi}" if doi else location.get("landing_page_url") or f"https://openalex.org/{work_id}"),
            added=added,
            published=published,
            kind="Dissertation or thesis",
            disciplines=[d for d in DISCIPLINES if d in found],
            keywords=keywords.match([title, _abstract(w.get("abstract_inverted_index"))]),
        ))
    return items


def fetch_dissertations(config: dict, since: str, now: dt.datetime, window_days: int = 365,
                        per_page: int = 200, max_pages: int = 30) -> List[Item]:
    published_from = (now - dt.timedelta(days=window_days)).strftime("%Y-%m-%d")
    filters = [
        "type:dissertation",
        f"from_publication_date:{published_from}",
        "language:" + "|".join(config.get("languages", ["en"])),
        "primary_topic.id:" + "|".join(config["topics"]),
    ] + [f"primary_location.source.id:!{s}" for s in config.get("exclude_sources", {})]
    params = {"filter": ",".join(filters), "select": SELECT, "per_page": per_page, "cursor": "*"}
    key = os.environ.get("OPENALEX_API_KEY", "").strip()
    if key:
        params["api_key"] = key
    works: List[dict] = []
    for _ in range(max_pages):
        data = get_json(config["api"], params)
        works += data.get("results") or []
        cursor = (data.get("meta") or {}).get("next_cursor")
        if not cursor or not data.get("results"):
            break
        params["cursor"] = cursor
    return parse_works(works, config, since, now)
