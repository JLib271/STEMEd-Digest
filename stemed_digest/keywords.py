"""Keywords aligned with HuMeta, the STEM+ education research metadata profile.

config/keywords.json lists each keyword with the HuMeta terms it stands for, their
ERIC descriptors, and the phrases that count as a match. Matching is whole-word and
case-insensitive; a trailing * matches any ending ("misconception*"); acronyms in
match_case_sensitive must match exactly ("CURE" but not "cure").
"""
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Iterable, List, Pattern, Tuple

CONFIG = Path(__file__).resolve().parent.parent / "config" / "keywords.json"


SEP = r"[\s\-‐‑–—]?"          # "self efficacy" ~ "self-efficacy" ~ "selfefficacy"; "K-12" ~ "K–12" ~ "K12"


def _word(w: str) -> str:
    return re.escape(w[:-1]) + r"[\w'-]*" if w.endswith("*") else re.escape(w)


def _phrase(p: str) -> str:
    words = [w for w in re.split(r"[\s\-‐‑–—]+", p.strip()) if w]
    return r"(?<!\w)" + SEP.join(_word(w) for w in words) + r"(?![\w])"


def compile_keyword(entry: dict) -> Pattern:
    parts = []
    if entry.get("match"):
        parts.append(r"(?i:" + "|".join(_phrase(p) for p in entry["match"]) + ")")
    if entry.get("match_case_sensitive"):
        parts.append("|".join(_phrase(p) for p in entry["match_case_sensitive"]))
    return re.compile("|".join(parts) or r"(?!)")


@lru_cache(maxsize=None)
def load() -> Tuple[dict, Tuple[Tuple[str, Pattern], ...]]:
    doc = json.loads(CONFIG.read_text(encoding="utf-8"))
    return doc, tuple((k["id"], compile_keyword(k)) for k in doc["keywords"])


def match(texts: Iterable[str]) -> List[str]:
    text = " ".join(t for t in texts if t)
    text = re.sub(r"<[^>]+>", " ", text)          # abstracts arrive as JATS XML
    text = text.replace("’", "'")
    _, rules = load()
    return [kid for kid, pattern in rules if pattern.search(text)]


def summary() -> List[dict]:
    """What the website and items.json need about each keyword."""
    doc, _ = load()
    return [{"id": k["id"], "label": k["label"], "group": k["group"], "eric": k.get("eric", []),
             "humeta": [f"{h['vocabulary']}:{h['term']}" for h in k["humeta"]]} for k in doc["keywords"]]
