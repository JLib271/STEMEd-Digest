"""The STEMEd+ disciplines, read from the list shared across STEMEd+ Commons
(humeta-profile's stemedplus_disciplines.json, stored here as
stemedplus_disciplines.json; see stemedplus_disciplines.py). STEMEd+ Jobs,
Funding, Digest, and Graduate Programs all build from the same list."""
from typing import List

from . import stemedplus_disciplines as shared

# (label, pattern) pairs in the shared order. Acronyms such as PER, CER, GER and
# BER match only in capitals, so "per year" is not Physics.
DISCIPLINE_RULES = shared.rules()

DISCIPLINES = tuple(name for name, _ in DISCIPLINE_RULES)


def matching_disciplines(text: str) -> List[str]:
    return [name for name, pattern in DISCIPLINE_RULES if pattern.search(text)]
