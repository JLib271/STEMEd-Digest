"""Works deposited in the STEMEd+ Commons Collection and its subcollections, via the
Knowledge Commons Works (InvenioRDM) API. In that API, collections are "communities".

Subcollection works are not always also in the parent collection, so every
subcollection is read separately and duplicates are merged. Subcollections are
discovered on each run, so new ones are picked up without changing the config.
"""
import html
from typing import Dict, List

from . import keywords
from .disciplines import DISCIPLINES, matching_disciplines
from .http import get_json
from .models import Item, utc_stamp


def _records(api: str, slug: str, page_size: int = 100) -> List[dict]:
    hits, page = [], 1
    while True:
        data = get_json(f"{api}/communities/{slug}/records",
                        {"size": page_size, "page": page, "sort": "newest"})
        batch = data["hits"]["hits"]
        hits.extend(batch)
        if not batch or len(hits) >= data["hits"]["total"]:
            return hits
        page += 1


def subcollections(api: str, slug: str) -> List[dict]:
    data = get_json(f"{api}/communities/{slug}/subcommunities", {"size": 100})
    return [{"id": h["id"], "slug": h["slug"], "title": h["metadata"]["title"]} for h in data["hits"]["hits"]]


def _creator(c: dict) -> str:
    name = (c.get("person_or_org") or {}).get("name", "")
    if "," in name:                       # "Anderson, Steven W" -> "Steven W Anderson"
        family, _, given = name.partition(",")
        name = f"{given.strip()} {family.strip()}".strip()
    return " ".join(name.split())


def parse_record(hit: dict, config: dict, subs_by_id: Dict[str, dict]) -> Item:
    md = hit.get("metadata") or {}
    community_ids = ((hit.get("parent") or {}).get("communities") or {}).get("ids") or []
    in_subs = [subs_by_id[c] for c in community_ids if c in subs_by_id]
    tags = list((hit.get("custom_fields") or {}).get("kcr:user_defined_tags") or [])
    subjects = [s.get("subject", "") for s in md.get("subjects") or []]
    disciplines = []
    for sub in in_subs:
        disciplines += config.get("subcollection_disciplines", {}).get(sub["slug"], [])
    text = " ".join([md.get("title", "")] + tags + subjects)
    disciplines += matching_disciplines(text)
    rtype = md.get("resource_type") or {}
    doi = ((hit.get("pids") or {}).get("doi") or {}).get("identifier", "")
    return Item(
        id=f"kcworks:{hit['id']}",
        source="commons",
        title=" ".join(html.unescape(md.get("title") or "").split()),
        authors=[n for n in (_creator(c) for c in md.get("creators") or []) if n],
        venue=config.get("name", "STEMEd+ Commons"),
        url=(hit.get("links") or {}).get("self_html") or (f"https://doi.org/{doi}" if doi else ""),
        added=utc_stamp(hit.get("created", "")),
        published=md.get("publication_date", ""),
        kind=(rtype.get("title") or {}).get("en", ""),
        disciplines=[d for d in DISCIPLINES if d in disciplines],
        collections=[s["title"] for s in in_subs],
        keywords=keywords.match([md.get("title", "")] + tags + subjects),
    )


def fetch_commons(config: dict) -> List[Item]:
    api, parent = config["api"], config["collection"]
    subs = subcollections(api, parent)
    subs_by_id = {s["id"]: s for s in subs}
    seen: Dict[str, dict] = {}
    for slug in [parent] + [s["slug"] for s in subs]:
        for hit in _records(api, slug):
            seen.setdefault(hit["id"], hit)
    return [parse_record(h, config, subs_by_id) for h in seen.values()]
