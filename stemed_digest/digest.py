"""The weekly digest: a short "Recently added to STEMEd+ Commons" section first, to show
off new deposits and invite more, then new journal articles grouped by journal.

Written as digest.html (to read or link) and digest.md (to paste into a STEMEd+ Commons
post, a newsletter, or an email).
"""
import datetime as dt
import html
from collections import OrderedDict
from pathlib import Path
from typing import List, Optional

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


def build(items: List[Item], site: dict, commons_cfg: dict, now: dt.datetime, journal_urls: Optional[dict] = None) -> dict:
    days = site["digest_days"]
    recent = window(items, now, days)
    from_commons = [i for i in recent if i.source == "commons"]
    by_journal: "OrderedDict[str, List[Item]]" = OrderedDict()
    for i in sorted((i for i in recent if i.source == "journal"), key=lambda i: (i.venue.lower(), i.title.lower())):
        by_journal.setdefault(i.venue, []).append(i)
    by_title = lambda i: (i.venue.lower(), i.title.lower())  # noqa: E731
    return {"dates": _dates(now, days), "commons": from_commons, "journals": by_journal, "journal_urls": journal_urls or {},
            "journal_count": sum(len(v) for v in by_journal.values()),
            "preprints": sorted((i for i in recent if i.source == "preprint"), key=by_title),
            "dissertations": sorted((i for i in recent if i.source == "dissertation"), key=lambda i: i.title.lower())}


PREPRINT_NOTE = "Preprints have not been peer reviewed."
DISSERTATION_NOTE = "Doctoral dissertations and master's theses from university repositories, found through OpenAlex."


def _n(count: int, one: str, many: str) -> str:
    return f"{count} {one if count == 1 else many}"


def _lede(d: dict, commons_name: str) -> str:
    return (f"This week: {len(d['commons'])} new in {commons_name}, {_n(d['journal_count'], 'journal article', 'journal articles')}, "
            f"{_n(len(d['preprints']), 'preprint', 'preprints')}, and "
            f"{_n(len(d['dissertations']), 'dissertation or thesis', 'dissertations and theses')}.")


def to_markdown(d: dict, site: dict, commons_cfg: dict) -> str:
    out = [f"# {site['title']}: {d['dates']}", "",
           _lede(d, commons_cfg["name"]), "",
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
        url = d.get("journal_urls", {}).get(venue)
        heading = f"[{_md_escape(venue)}]({url})" if url else venue
        out += [f"### {heading} ({len(its)})", ""] + [f"- [{_md_escape(i.title)}]({i.url}). {describe(i)}" for i in its] + [""]
    for title, note, its in (("New preprints", PREPRINT_NOTE, d["preprints"]),
                             ("New dissertations and theses", DISSERTATION_NOTE, d["dissertations"])):
        out += ["", f"## {title}", "", note, ""]
        out += [f"- [{_md_escape(i.title)}]({i.url}). {describe(i)}" for i in its] or ["Nothing new this week."]
    return "\n".join(out).rstrip() + "\n"


def _li(i: Item) -> str:
    return (f'<li><a href="{html.escape(i.url)}" target="_blank" rel="noopener noreferrer">{html.escape(i.title)}</a>'
            f'<div class="by">{html.escape(describe(i))}</div></li>')


def to_html(d: dict, site: dict, commons_cfg: dict) -> str:
    title = f"{site['title']}: {d['dates']}"
    curl = html.escape(commons_cfg["collection_url"])
    cname = html.escape(commons_cfg["name"])
    commons = "".join(_li(i) for i in d["commons"]) or "<li class=\"none\">Nothing new this week.</li>"
    urls = d.get("journal_urls", {})

    def heading(v: str) -> str:
        if not urls.get(v):
            return html.escape(v)
        return (f'<a href="{html.escape(urls[v])}" target="_blank" rel="noopener noreferrer" '
                f'title="Journal website">{html.escape(v)}</a>')

    def extra(its: List[Item]) -> str:
        return f"<ul>{''.join(_li(i) for i in its)}</ul>" if its else "<p class=\"none\">Nothing new this week.</p>"

    journals = "".join(
        f"<h3>{heading(v)} <span class=\"n\">({len(its)})</span></h3><ul>{''.join(_li(i) for i in its)}</ul>"
        for v, its in d["journals"].items()) or "<p class=\"none\">No new journal articles this week.</p>"
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
 body {{ margin: 0; font: 16px/1.55 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; color: #1d2433; background: #f7f8fa; }}
 main {{ max-width: 780px; margin: 0 auto; padding: 28px 20px 40px; }}
 h1 {{ font-size: 1.5rem; margin: 0 0 6px; }} .lede {{ color: #5b6475; margin: 0 0 22px; }}
 h2 {{ font-size: 1.15rem; margin: 26px 0 8px; }} h3 {{ font-size: 1rem; margin: 18px 0 6px; }} .n {{ color: #5b6475; font-weight: 400; }}
 ul {{ padding-left: 20px; margin: 6px 0; }} li {{ margin: 8px 0; }} a {{ color: #014704; }} .by {{ color: #5b6475; font-size: .9rem; }}
 .commons {{ background: #e9f2e9; border: 1px solid #c6dcc7; border-radius: 8px; padding: 6px 18px 14px; }}
 .invite {{ margin: 10px 0 0; }} .note {{ color: #5b6475; font-size: .9rem; margin: 0 0 6px; }} .none {{ color: #5b6475; list-style: none; }}
 .stemedplus {{ display: inline-block; margin: 0 0 8px; }} .stemedplus img {{ display: block; height: 48px; width: auto; }}
 footer {{ margin-top: 30px; font-size: .9rem; color: #5b6475; }}
</style>
<link rel="stylesheet" href="stemedplus-theme.css"></head><body>
<div class="sp-bar"><div class="sp-in"><a class="sp-logo" href="https://stemedplus.org/"><img src="stemedplus-commons-logo-white.png" alt="STEMEd+ Commons home" width="263" height="91"></a><input type="checkbox" id="sp-menu-toggle" class="sp-toggle"><label for="sp-menu-toggle" class="sp-burger"><span class="sp-burger-icon" aria-hidden="true"></span>Menu</label><nav class="sp-nav" aria-label="STEMEd+ Commons"><ul class="sp-top"><li class="sp-has"><a href="https://stemedplus.org/stemed-features/">Features</a><svg class="sp-chev" width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M1.5 4L6 8L10.5 4" stroke="currentColor" stroke-width="1.5"/></svg><ul class="sp-sub"><li><a href="https://works.hcommons.org/collections/stemedplus/records?q=&amp;l=list&amp;p=1&amp;s=10&amp;sort=newest">STEMEd+ Library</a></li><li><a href="https://stemedplus.org/sites/">STEMEd+ Sites</a></li><li><a href="https://stemedplus.profile.hcommons.org/members/">STEMEd+ Members</a></li><li><a href="https://stemedplus.org/stemed-groups/">STEMEd+ Groups</a></li></ul></li><li class="sp-has sp-here"><a href="https://stemedplus.org/stemed-resources/">Resources</a><svg class="sp-chev" width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M1.5 4L6 8L10.5 4" stroke="currentColor" stroke-width="1.5"/></svg><ul class="sp-sub"><li><a href="https://theseekershub.stemedplus.org/">The Seekers’ Hub: A Job Board</a></li><li><a href="https://stemedplus.org/stemed-collaborators/">Find Collaborators</a></li><li><a href="https://jlib271.github.io/stemed-funding/">Find Funding</a></li><li><a href="https://jlib271.github.io/STEMEd-Digest/" aria-current="page">STEMEd+ Digest</a></li><li><a href="https://jlib271.github.io/stem-ed-research-programs/">STEMEd+ Graduate Programs</a></li><li><a href="https://jlib271.github.io/stemed-conferences/">STEMEd+ Conferences</a></li><li><a href="https://jlib271.github.io/stemed-professional-learning/">STEMEd+ Professional Learning</a></li><li><a href="https://jlib271.github.io/stemed-faculty-development/">STEMEd+ Faculty Development</a></li><li><a href="https://jlib271.github.io/stemed-deadlines/">STEMEd+ Deadlines</a></li></ul></li><li class="sp-has"><a href="https://stemedplus.org/about/">Learn More</a><svg class="sp-chev" width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M1.5 4L6 8L10.5 4" stroke="currentColor" stroke-width="1.5"/></svg><ul class="sp-sub"><li><a href="https://stemedplus.org/about/">About</a></li><li><a href="https://stemedplus.org/learn-more/">Governance</a></li><li><a href="https://stemedplus.org/vision-research/">Vision &amp; Research</a></li><li><a href="https://support.hcommons.org/">Help &amp; Support</a></li></ul></li><li><a href="https://stemedplus.org/collaborate/">Partner with Us</a></li><li><a href="https://stemedplus.org/contact-us/">Contact Us</a></li><li><a href="https://stemedplus.org/join-stemed/">Join STEMEd+</a></li><li><a href="https://stemedplus.org/stemed-commons-frequently-asked-questions/">Get Started &amp; FAQs</a></li></ul></nav><a class="sp-login" href="https://stemedplus.org/wp-login.php">Log in</a></div></div>
<main>
<h1>{html.escape(title)}</h1>
<p class="lede">{html.escape(_lede(d, commons_cfg["name"]))}</p>
<section class="commons"><h2>Recently added to {cname}</h2><ul>{commons}</ul>
<p class="invite">Have a paper, poster, lesson plan, instrument, or dataset to share? <a href="{curl}" target="_blank" rel="noopener noreferrer">Add it to the {cname} Collection</a>.</p></section>
<h2>New in journals</h2>{journals}
<h2>New preprints</h2><p class="note">{PREPRINT_NOTE}</p>{extra(d["preprints"])}
<h2>New dissertations and theses</h2><p class="note">{DISSERTATION_NOTE}</p>{extra(d["dissertations"])}
<footer><a href="./">Browse and search everything</a> · <a href="feeds/all.xml">RSS feed</a> · <a href="digest.md">This digest as Markdown</a></footer>
</main></body></html>
"""


def write(out: Path, items: List[Item], site: dict, commons_cfg: dict, now: dt.datetime,
          journal_urls: Optional[dict] = None) -> None:
    d = build(items, site, commons_cfg, now, journal_urls)
    (out / "digest.md").write_text(to_markdown(d, site, commons_cfg), encoding="utf-8")
    (out / "digest.html").write_text(to_html(d, site, commons_cfg), encoding="utf-8")


# "For the classroom": a monthly digest of journals written for teachers and instructors.

CLASSROOM_NOTE = ("New articles from journals written for teachers and instructors, from pre-K through college: "
                  "classroom activities, labs, teaching practice, and research made for practice.")


def build_classroom(items: List[Item], site: dict, now: dt.datetime, classroom_journals, journal_urls=None) -> dict:
    days = site.get("classroom_days", 30)
    recent = [i for i in window(items, now, days) if i.source == "journal" and i.venue in classroom_journals]
    by_journal: "OrderedDict[str, List[Item]]" = OrderedDict()
    for i in sorted(recent, key=lambda i: (i.venue.lower(), i.title.lower())):
        by_journal.setdefault(i.venue, []).append(i)
    return {"dates": _dates(now, days), "journals": by_journal, "journal_urls": journal_urls or {},
            "count": len(recent), "followed": sorted(classroom_journals, key=str.lower)}


def classroom_markdown(d: dict, site: dict) -> str:
    out = [f"# {site['title']}: For the classroom, {d['dates']}", "", CLASSROOM_NOTE, "",
           f"This month: {_n(d['count'], 'new article', 'new articles')} from {_n(len(d['journals']), 'journal', 'journals')}.", ""]
    if not d["journals"]:
        out.append("No new articles this month.")
    for venue, its in d["journals"].items():
        url = d["journal_urls"].get(venue)
        heading = f"[{_md_escape(venue)}]({url})" if url else venue
        out += [f"## {heading} ({len(its)})", ""] + [f"- [{_md_escape(i.title)}]({i.url}). {describe(i)}" for i in its] + [""]
    out += ["", "Journals followed: " + "; ".join(d["followed"]) + "."]
    return "\n".join(out).rstrip() + "\n"


def classroom_html(d: dict, site: dict) -> str:
    md_title = f"{site['title']}: For the classroom, {d['dates']}"
    urls = d["journal_urls"]

    def heading(v: str) -> str:
        if not urls.get(v):
            return html.escape(v)
        return f'<a href="{html.escape(urls[v])}" target="_blank" rel="noopener noreferrer">{html.escape(v)}</a>'

    body = "".join(f"<h2>{heading(v)} <span class=\"n\">({len(its)})</span></h2><ul>{''.join(_li(i) for i in its)}</ul>"
                   for v, its in d["journals"].items()) or "<p class=\"none\">No new articles this month.</p>"
    page = to_html({"dates": "", "commons": [], "journals": {}, "preprints": [], "dissertations": [], "journal_count": 0},
                   site, {"name": "", "collection_url": ""})
    head, rest = page.split("<main>", 1)
    head = head.replace(f"<title>{html.escape(site['title'] + ': ')}</title>", f"<title>{html.escape(md_title)}</title>")
    lede = (f"This month: {_n(d['count'], 'new article', 'new articles')} from "
            f"{_n(len(d['journals']), 'journal', 'journals')}. {CLASSROOM_NOTE}")
    return (head + "<main>\n" + f"<h1>{html.escape(md_title)}</h1>\n<p class=\"lede\">{html.escape(lede)}</p>\n" + body +
            f"\n<p class=\"note\">Journals followed: {html.escape('; '.join(d['followed']))}.</p>"
            "\n<footer><a href=\"./#source=classroom\">Browse all classroom articles</a> · "
            "<a href=\"feeds/classroom.xml\">RSS feed</a> · <a href=\"classroom.md\">This digest as Markdown</a> · "
            "<a href=\"digest.html\">This week's full digest</a></footer>\n</main></body></html>\n")


def write_classroom(out: Path, items: List[Item], site: dict, now: dt.datetime, classroom_journals,
                    journal_urls: Optional[dict] = None) -> None:
    d = build_classroom(items, site, now, classroom_journals, journal_urls)
    (out / "classroom.md").write_text(classroom_markdown(d, site), encoding="utf-8")
    (out / "classroom.html").write_text(classroom_html(d, site), encoding="utf-8")
