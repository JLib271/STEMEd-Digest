"""Where to publish your teaching work: the venue list behind publish.html."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .disciplines import DISCIPLINES

ROOT = Path(__file__).resolve().parent.parent
REQUIRED = ("name", "url", "publisher", "disciplines", "kind", "levels", "scope", "review", "access", "fees")
LEVELS = ("K-12", "Undergraduate", "Graduate")


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
        if not str(v.get("url", "")).startswith("https://"):
            problems.append(f"{name}: url must start with https://")
        if "checked" in v and not re.fullmatch(r"\d{4}-\d{2}", v["checked"]):
            problems.append(f"{name}: checked must be YYYY-MM")
    if problems:
        raise ValueError("config/venues.json: " + "; ".join(problems))


def write(out: Path) -> None:
    data = load()
    (out / "venues.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
