"""Fetch every source, merge with what was published last time, and write the site.

    python -m stemed_digest --out output --previous https://<owner>.github.io/<repo>

Output (all static, served by GitHub Pages):
    index.html        searchable list
    items.json        everything currently listed (also the state for the next run)
    digest.html/.md   the last week: "Recently added to STEMEd+ Commons", journals, preprints, dissertations
    feeds/*.xml       RSS: all, STEMEd+ Commons, preprints, dissertations, and one per discipline
"""
import argparse
import datetime as dt
import json
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional
from urllib.request import Request, urlopen

from . import commons, crossref, digest, dissertations, feeds, keywords, preprints
from .disciplines import DISCIPLINES
from .http import user_agent
from .models import Item

ROOT = Path(__file__).resolve().parent.parent


def load_config(name: str) -> dict:
    return json.loads((ROOT / "config" / name).read_text(encoding="utf-8"))


def load_previous(previous: Optional[str]) -> List[Item]:
    """Items from the last published items.json (a URL or a local path). A missing or
    unreadable file just means a fresh start, e.g. on the very first run."""
    if not previous:
        return []
    try:
        if previous.startswith(("http://", "https://")):
            url = previous.rstrip("/") + "/items.json"
            with urlopen(Request(url, headers={"User-Agent": user_agent()}), timeout=60) as resp:
                data = json.load(resp)
        else:
            data = json.loads(Path(previous).read_text(encoding="utf-8"))
        return [Item.from_dict(d) for d in data.get("items", [])]
    except Exception as exc:  # noqa: BLE001 - any failure means "start fresh"
        print(f"Note: no previous items loaded from {previous} ({exc}).")
        return []


def merge(previous: List[Item], fresh: List[Item], now: dt.datetime, keep_days: int) -> List[Item]:
    """Fresh copies replace old ones. Journal articles older than keep_days are dropped;
    Commons works stay, since the collection is small and every work is worth finding."""
    by_id: Dict[str, Item] = {i.id: i for i in previous}
    by_id.update({i.id: i for i in fresh})
    cutoff = (now - dt.timedelta(days=keep_days)).strftime("%Y-%m-%dT%H:%M:%S")
    kept = [i for i in by_id.values() if i.source == "commons" or i.added >= cutoff]
    return sorted(kept, key=lambda i: (i.added, i.id), reverse=True)


def drop_preprints_of_listed_articles(items: List[Item]) -> List[Item]:
    """A preprint whose published version is already listed from a followed journal is
    shown once, as the journal article."""
    articles = {i.id[4:] for i in items if i.source == "journal"}
    return [i for i in items if not (i.source == "preprint" and i.version_of and i.version_of in articles)]


def run(out: Path, previous: Optional[str], now: dt.datetime, fetch_journals=crossref.fetch_journal,
        fetch_commons=commons.fetch_commons, fetch_edarxiv=None, fetch_arxiv=None, fetch_dissertations=None,
        allow_errors: bool = False) -> dict:
    fetch_edarxiv = fetch_edarxiv or preprints.fetch_edarxiv
    fetch_arxiv = fetch_arxiv or preprints.fetch_arxiv
    fetch_dissertations = fetch_dissertations or dissertations.fetch_dissertations
    site, journals, commons_cfg = load_config("site.json"), load_config("journals.json"), load_config("commons.json")
    servers, diss_cfg = load_config("preprints.json"), load_config("dissertations.json")
    previous_items = load_previous(previous)
    listed = {i.venue for i in previous_items if i.source in ("journal", "preprint")}
    listed |= {i.source for i in previous_items}
    recent = (now - dt.timedelta(days=site["lookback_days"])).strftime("%Y-%m-%d")
    backfill = (now - dt.timedelta(days=site["keep_days"])).strftime("%Y-%m-%d")
    fresh: List[Item] = []
    status = []
    for j in journals["journals"]:
        # A journal with nothing listed yet (first run, or newly added) gets the whole window.
        since = recent if j["name"] in listed else backfill
        try:
            got = fetch_journals(j, since)
            fresh += got
            status.append({"source": j["name"], "ok": True, "new": len(got)})
        except Exception as exc:  # noqa: BLE001
            status.append({"source": j["name"], "ok": False, "error": str(exc)[:200]})
    # Preprint servers and dissertations, also backfilled the first time they run.
    others = [
        (servers["edarxiv"]["name"], lambda since: fetch_edarxiv(servers["edarxiv"], since)),
        (servers["arxiv"]["name"], lambda since: fetch_arxiv(servers["arxiv"], since)),
        (servers["arxiv_hist_ph"]["name"], lambda since: fetch_arxiv(servers["arxiv_hist_ph"], since)),
        (diss_cfg["name"], lambda since: fetch_dissertations(diss_cfg, since, now, site["keep_days"])),
    ]
    for name, fetch in others:
        seen = name in listed or (name == diss_cfg["name"] and "dissertation" in listed)
        try:
            got = fetch(recent if seen else backfill)
            fresh += got
            status.append({"source": name, "ok": True, "new": len(got)})
        except Exception as exc:  # noqa: BLE001
            status.append({"source": name, "ok": False, "error": str(exc)[:200]})
    try:
        got = fetch_commons(commons_cfg)
        fresh += got
        status.append({"source": commons_cfg["name"], "ok": True, "new": len(got)})
    except Exception as exc:  # noqa: BLE001
        status.append({"source": commons_cfg["name"], "ok": False, "error": str(exc)[:200]})

    failed = [s for s in status if not s["ok"]]
    for s in failed:
        print(f"WARNING: {s['source']}: {s['error']}")
    if failed and not allow_errors:
        raise SystemExit(f"{len(failed)} source(s) failed; rerun with --allow-errors to publish anyway.")

    items = drop_preprints_of_listed_articles(merge(previous_items, fresh, now, site["keep_days"]))
    out.mkdir(parents=True, exist_ok=True)
    generated = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "generated": generated,
        "site": {k: site[k] for k in ("title", "tagline", "repo_url", "commons_home")},
        "commons": {"name": commons_cfg["name"], "url": commons_cfg["collection_url"]},
        "disciplines": list(DISCIPLINES),
        "keyword_groups": keywords.load()[0]["groups"],
        "keywords": keywords.summary(),
        "keep_days": site["keep_days"],
        "journals": [{"name": j["name"], "publisher": j.get("publisher", ""), "society": j.get("society", ""),
                      "disciplines": j.get("disciplines", []), "url": j.get("url", "")} for j in journals["journals"]],
        "preprint_servers": [{"name": v["name"], "url": v["url"]} for k, v in servers.items() if not k.startswith("_")],
        "dissertations": {"name": diss_cfg["name"], "url": diss_cfg["url"]},
        "status": status,
        "items": [i.to_dict() for i in items],
    }
    (out / "items.json").write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    shutil.copyfile(ROOT / "site" / "index.html", out / "index.html")
    feeds.write_all(out / "feeds", items, site, commons_cfg, now)
    digest.write(out, items, site, commons_cfg, now, {j["name"]: j["url"] for j in journals["journals"] if j.get("url")})
    counts = ", ".join(f"{sum(i.source == s for i in items)} {s}" for s in ("journal", "commons", "preprint", "dissertation"))
    print(f"Wrote {len(items)} items ({counts}); "
          f"{len(failed)} source(s) failed.")
    return payload


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", default="output")
    p.add_argument("--previous", help="URL of the published site (or path to an items.json) to carry items over from")
    p.add_argument("--allow-errors", action="store_true", help="publish even if some sources fail")
    a = p.parse_args(argv)
    run(Path(a.out), a.previous, dt.datetime.now(dt.timezone.utc), allow_errors=a.allow_errors)
    return 0


if __name__ == "__main__":
    sys.exit(main())
