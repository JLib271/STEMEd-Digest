"""The one record type every source produces."""
import datetime as dt
from dataclasses import asdict, dataclass, field
from typing import List


def utc_stamp(value: str) -> str:
    """Any ISO 8601 timestamp -> 'YYYY-MM-DDTHH:MM:SSZ' in UTC, so dates sort as text."""
    if not value:
        return ""
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Item:
    id: str                 # stable key: "doi:<doi>" or "kcworks:<record id>"
    source: str             # "journal" or "commons"
    title: str
    authors: List[str]
    venue: str              # journal name, or "STEMEd+ Commons"
    url: str                # where readers go: the DOI link or the Commons record page
    added: str              # when it appeared (Crossref registration or Commons deposit), ISO 8601 UTC
    published: str = ""     # publication date as given by the source: YYYY, YYYY-MM or YYYY-MM-DD
    kind: str = ""          # e.g. "Journal article", "Curriculum", "Book section"
    disciplines: List[str] = field(default_factory=list)
    collections: List[str] = field(default_factory=list)   # Commons subcollection names
    keywords: List[str] = field(default_factory=list)      # ids from config/keywords.json (HuMeta terms)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Item":
        known = {k: data[k] for k in cls.__dataclass_fields__ if k in data}
        return cls(**known)
