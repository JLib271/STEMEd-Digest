"""Where to publish: the journal list behind publish.html.

Two sources are combined into one list with two sections:

* config/venues.json: curated venues for teaching innovations, classroom
  materials, and SoTL, with scope, review, access, and fee details.
* config/journals.json: every journal the Digest follows.

If in doubt, a journal is in both sections, and that is the default for
any journal added later. A journal is kept to one section only when:

* its own "sections" field says so (this overrides everything else),
* it is named in "teaching_only" or "research_only" in config/venues.json,
* every one of its disciplines is in "research_only_disciplines", or
* it is a curated practitioner magazine or lesson journal (kind "practice"
  or "materials"), which go in Teaching & SoTL.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .disciplines import DISCIPLINES

ROOT = Path(__file__).resolve().parent.parent
REQUIRED = ("name", "url", "publisher", "disciplines", "kind", "levels", "scope", "review", "access", "fees")
LEVELS = ("K-12", "Undergraduate", "Graduate")
SECTIONS = {"teaching": "Teaching & SoTL", "research": "Research"}


def load(path: Path = ROOT / "config" / "venues.json") -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    check(data)
    return data


def check(data: dict) -> None:
    """Raise ValueError if any venue is incomplete or uses an unknown value."""
    problems, names = [], set()
    for v in data["venues"]:
        name = v.get("name", "?")
        problems += [f"{name}: missing {k}" for k in REQUIRED if not v.get(k) and k != "disciplines"]
        if name in names:
            problems.append(f"{name}: listed twice")
        names.add(name)
        if v.get("kind") not in data["kinds"]:
            problems.append(f"{name}: unknown kind {v.get('kind')!r}")
        if v.get("access") not in data["access"]:
            problems.append(f"{name}: unknown access {v.get('access')!r}")
        problems += [f"{name}: unknown discipline {d!r}" for d in v.get("disciplines", []) if d not in DISCIPLINES]
        problems += [f"{name}: unknown level {x!r}" for x in v.get("levels", []) if x not in LEVELS]
        problems += [f"{name}: unknown section {x!r}" for x in v.get("sections", []) if x not in SECTIONS]
        if not str(v.get("url", "")).startswith("https://"):
            problems.append(f"{name}: url must start with https://")
        if "checked" in v and not re.fullmatch(r"\d{4}-\d{2}", v["checked"]):
            problems.append(f"{name}: checked must be YYYY-MM")
    if problems:
        raise ValueError("config/venues.json: " + "; ".join(problems))


def key(name: str) -> str:
    """Match journal names across the two lists: case, a leading "The",
    a parenthetical abbreviation, "&" for "and", and punctuation do not matter."""
    s = re.sub(r"\(.*?\)", "", name.lower()).replace("&", " and ")
    s = re.sub(r"^\s*the\s+", "", s)
    return re.sub(r"[^a-z0-9]", "", s)


def sections_for(v: dict, data: dict, curated: bool) -> list:
    """Where one journal is listed: both sections unless something says otherwise."""
    if v.get("sections"):
        return list(v["sections"])
    names = {key(n) for n in v.get("digest_names") or [v["name"]]}
    if names & {key(n) for n in data.get("teaching_only", [])}:
        return ["teaching"]
    if names & {key(n) for n in data.get("research_only", [])}:
        return ["research"]
    discs = v.get("disciplines") or []
    if discs and all(d in data.get("research_only_disciplines", []) for d in discs):
        return ["research"]
    if curated and v.get("kind") in ("practice", "materials"):
        return ["teaching"]
    return ["teaching", "research"]


def combine(data: dict, journals: list) -> dict:
    """Return data with every Digest journal added and a sections list on each venue."""
    followed = {key(j["name"]) for j in journals}
    out, covered = [], set()
    for v in data["venues"]:
        names = v.get("digest_names") or [v["name"]]
        covered.update(key(n) for n in names)
        out.append(dict(v, sections=sections_for(v, data, True), digest=any(key(n) in followed for n in names)))
    for j in journals:
        if key(j["name"]) in covered:
            continue
        sections = sections_for(j, data, False)
        kind = "practice" if j.get("classroom") else "journal" if sections == ["research"] else "education"
        out.append({
            "name": j["name"], "url": j["url"], "publisher": j["publisher"],
            "disciplines": j.get("disciplines", []), "kind": kind, "sections": sections, "digest": True,
        })
    return dict(data, venues=out, sections=SECTIONS)


def write(out: Path) -> None:
    journals = json.loads((ROOT / "config" / "journals.json").read_text(encoding="utf-8"))["journals"]
    data = combine(load(), journals)
    (out / "venues.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
