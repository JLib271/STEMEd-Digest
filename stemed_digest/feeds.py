"""RSS 2.0 feeds: everything, STEMEd+ Commons only, and one per discipline."""
import datetime as dt
import re
from email.utils import format_datetime
from pathlib import Path
from typing import List
from xml.etree import ElementTree as ET

from . import keywords as kw
from . import stemedplus_disciplines as shared
from .disciplines import DISCIPLINES

FIELD_DISCIPLINES = shared.field_labels()  # disciplines that include the field itself
from .models import Item

FEED_SIZE = 200


def slug(text: str) -> str:
    """"History & Philosophy of Science" -> "history-and-philosophy-of-science"."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower().replace("&", " and ")).strip("-")


def _rfc822(stamp: str) -> str:
    try:
        return format_datetime(dt.datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc))
    except ValueError:
        return ""


def describe(item: Item) -> str:
    parts = [", ".join(item.authors[:6]) + (" et al." if len(item.authors) > 6 else "")] if item.authors else []
    venue = item.venue + (f" ({'; '.join(item.collections)})" if item.collections else "")
    parts.append(venue + (f", {item.published}" if item.published else ""))
    if item.kind and item.kind != "Journal article":
        parts.append(item.kind)
    return ". ".join(p for p in parts if p) + "."


def _write(path: Path, title: str, link: str, description: str, items: List[Item], now: dt.datetime) -> None:
    rss = ET.Element("rss", version="2.0")
    ch = ET.SubElement(rss, "channel")
    ET.SubElement(ch, "title").text = title
    ET.SubElement(ch, "link").text = link
    ET.SubElement(ch, "description").text = description
    ET.SubElement(ch, "lastBuildDate").text = format_datetime(now)
    labels = {k["id"]: k["label"] for k in kw.summary()}
    for item in items[:FEED_SIZE]:
        e = ET.SubElement(ch, "item")
        ET.SubElement(e, "title").text = item.title
        ET.SubElement(e, "link").text = item.url
        ET.SubElement(e, "guid", isPermaLink="false").text = item.id
        ET.SubElement(e, "description").text = describe(item)
        if _rfc822(item.added):
            ET.SubElement(e, "pubDate").text = _rfc822(item.added)
        for d in item.disciplines:
            ET.SubElement(e, "category").text = d
        for k in item.keywords:
            if k in labels:
                ET.SubElement(e, "category", domain="https://github.com/JLib271/HuMeta").text = labels[k]
    ET.indent(rss)
    path.write_bytes(b'<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(rss, encoding="utf-8") + b"\n")


def write_all(folder: Path, items: List[Item], site: dict, commons_cfg: dict, now: dt.datetime) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    link = site["repo_url"]
    _write(folder / "all.xml", site["title"], link, site["tagline"], items, now)
    _write(folder / "stemed-commons.xml", f"{site['title']}: {commons_cfg['name']}", commons_cfg["collection_url"],
           f"New works in the {commons_cfg['name']} Collection and its subcollections.",
           [i for i in items if i.source == "commons"], now)
    _write(folder / "preprints.xml", f"{site['title']}: Preprints", link,
           "New STEM+ education preprints from EdArXiv, arXiv Physics Education, and arXiv History and Philosophy of Physics.",
           [i for i in items if i.source == "preprint"], now)
    _write(folder / "dissertations.xml", f"{site['title']}: Dissertations and theses", link,
           "New STEM+ education dissertations and theses from university repositories, via OpenAlex.",
           [i for i in items if i.source == "dissertation"], now)
    for d in DISCIPLINES:
        _write(folder / f"{slug(d)}.xml", f"{site['title']}: {d}", link, f"New work in {d}." if d in FIELD_DISCIPLINES else f"New work in {d} education.",
               [i for i in items if d in i.disciplines], now)
