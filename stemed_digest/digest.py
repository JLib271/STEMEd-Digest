"""The weekly digest: a short "Recently added to STEMEd+ Commons" section first, to show
off new deposits and invite more, then new journal articles grouped by journal.

Written as digest.html (to read or link) and digest.md (to paste into a STEMEd+ Commons
post, a newsletter, or an email).
"""
import datetime as dt
import html
from collections import OrderedDict
from pathlib import Path
from typing import List

from .feeds import describe
from .models import Item


def window(items: List[Item], now: dt.datetime, days: int) -> List[Item]:
    start = (now - dt.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return [i for i in items if i.added >= start]


def _md_escape(text: str) -> str:
    return text.replace("[", "\\[").replace("]", "\\]")


def _dates(now: dt.datetime, days: int) -> str:
    start = now - dt.timedelta(days=days)
    return f"{start:%B} {start.day} to {now:%B} {now.day}, {now.year}"


def build(items: List[Item], site: dict, commons_cfg: dict, now: dt.datetime) -> dict:
    days = site["digest_days"]
    recent = window(items, now, days)
    from_commons = [i for i in recent if i.source == "commons"]
    by_journal: "OrderedDict[str, List[Item]]" = OrderedDict()
    for i in sorted((i for i in recent if i.source == "journal"), key=lambda i: (i.venue.lower(), i.title.lower())):
        by_journal.setdefault(i.venue, []).append(i)
    return {"dates": _dates(now, days), "commons": from_commons, "journals": by_journal,
            "journal_count": sum(len(v) for v in by_journal.values())}


def to_markdown(d: dict, site: dict, commons_cfg: dict) -> str:
    out = [f"# {site['title']}: {d['dates']}", "",
           f"{len(d['commons'])} new in {commons_cfg['name']} and {d['journal_count']} new journal articles this week.", "",
           f"## Recently added to {commons_cfg['name']}", ""]
    if d["commons"]:
        out += [f"- [{_md_escape(i.title)}]({i.url}). {describe(i)}" for i in d["commons"]]
    else:
        out.append("Nothing new this week.")
    out += ["", f"Have a paper, poster, lesson plan, instrument, or dataset to share? Add it to the "
                f"[{commons_cfg['name']} Collection]({commons_cfg['collection_url']}).",
            "", "## New in journals", ""]
    if not d["journals"]:
        out.append("No new journal articles this week.")
    for venue, its in d["journals"].items():
        out += [f"### {venue} ({len(its)})", ""] + [f"- [{_md_escape(i.title)}]({i.url}). {describe(i)}" for i in its] + [""]
    return "\n".join(out).rstrip() + "\n"


def _li(i: Item) -> str:
    return (f'<li><a href="{html.escape(i.url)}" target="_blank" rel="noopener noreferrer">{html.escape(i.title)}</a>'
            f'<div class="by">{html.escape(describe(i))}</div></li>')


def to_html(d: dict, site: dict, commons_cfg: dict) -> str:
    title = f"{site['title']}: {d['dates']}"
    curl = html.escape(commons_cfg["collection_url"])
    cname = html.escape(commons_cfg["name"])
    commons = "".join(_li(i) for i in d["commons"]) or "<li class=\"none\">Nothing new this week.</li>"
    journals = "".join(
        f"<h3>{html.escape(v)} <span class=\"n\">({len(its)})</span></h3><ul>{''.join(_li(i) for i in its)}</ul>"
        for v, its in d["journals"].items()) or "<p class=\"none\">No new journal articles this week.</p>"
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
 body {{ margin: 0; font: 16px/1.55 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; color: #1d2433; background: #f7f8fa; }}
 main {{ max-width: 780px; margin: 0 auto; padding: 28px 20px 40px; }}
 h1 {{ font-size: 1.5rem; margin: 0 0 6px; }} .lede {{ color: #5b6475; margin: 0 0 22px; }}
 h2 {{ font-size: 1.15rem; margin: 26px 0 8px; }} h3 {{ font-size: 1rem; margin: 18px 0 6px; }} .n {{ color: #5b6475; font-weight: 400; }}
 ul {{ padding-left: 20px; margin: 6px 0; }} li {{ margin: 8px 0; }} a {{ color: #1f5f8b; }} .by {{ color: #5b6475; font-size: .9rem; }}
 .commons {{ background: #e6f0f7; border: 1px solid #c9dcea; border-radius: 8px; padding: 6px 18px 14px; }}
 .invite {{ margin: 10px 0 0; }} .none {{ color: #5b6475; list-style: none; }}
 footer {{ margin-top: 30px; font-size: .9rem; color: #5b6475; }}
</style></head><body><main>
<h1>{html.escape(title)}</h1>
<p class="lede">{len(d['commons'])} new in {cname} and {d['journal_count']} new journal articles this week.</p>
<section class="commons"><h2>Recently added to {cname}</h2><ul>{commons}</ul>
<p class="invite">Have a paper, poster, lesson plan, instrument, or dataset to share? <a href="{curl}" target="_blank" rel="noopener noreferrer">Add it to the {cname} Collection</a>.</p></section>
<h2>New in journals</h2>{journals}
<footer><a href="./">Browse and search everything</a> · <a href="feeds/all.xml">RSS feed</a> · <a href="digest.md">This digest as Markdown</a></footer>
</main></body></html>
"""


def write(out: Path, items: List[Item], site: dict, commons_cfg: dict, now: dt.datetime) -> None:
    d = build(items, site, commons_cfg, now)
    (out / "digest.md").write_text(to_markdown(d, site, commons_cfg), encoding="utf-8")
    (out / "digest.html").write_text(to_html(d, site, commons_cfg), encoding="utf-8")
