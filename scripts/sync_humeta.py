#!/usr/bin/env python3
"""Refresh keyword labels and ERIC descriptors from a HuMeta checkout.

    python scripts/sync_humeta.py ../HuMeta

For every keyword in config/keywords.json, this updates the HuMeta term labels and the
verified ERIC descriptors (from standard/humeta/crosswalks/eric.csv), and reports terms
that HuMeta no longer has. It never changes the match phrases, which are edited by hand.
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "keywords.json"


def humeta_terms(humeta: Path):
    labels = {}
    vocab = json.loads((humeta / "standard/humeta/vocabularies.json").read_text(encoding="utf-8"))["vocabularies"]
    for name, v in vocab.items():
        for term in (v.get("terms", v) if isinstance(v, dict) else v):
            if isinstance(term, dict):
                labels[(name, term["id"])] = term["label"]
    constructs = json.loads((humeta / "library/constructs.json").read_text(encoding="utf-8"))
    for c in constructs["constructs"] if isinstance(constructs, dict) else constructs:
        labels[("construct", c["id"])] = c["label"]
    eric = {}
    with open(humeta / "standard/humeta/crosswalks/eric.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["eric_status"] == "verified":
                eric.setdefault((row["vocabulary"], row["term_id"]), [])
                if row["eric_descriptor"] not in eric[(row["vocabulary"], row["term_id"])]:
                    eric[(row["vocabulary"], row["term_id"])].append(row["eric_descriptor"])
    return labels, eric


def main(argv) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    labels, eric = humeta_terms(Path(argv[1]))
    doc = json.loads(CONFIG.read_text(encoding="utf-8"))
    missing, changed = [], 0
    for k in doc["keywords"]:
        descriptors = []
        for h in k["humeta"]:
            key = (h["vocabulary"], h["term"])
            if key not in labels:
                missing.append(f"{k['id']}: {h['vocabulary']}:{h['term']}")
                continue
            if h["label"] != labels[key]:
                h["label"] = labels[key]
                changed += 1
            descriptors += [d for d in eric.get(key, []) if d not in descriptors]
        if descriptors != k.get("eric", []):
            k["eric"] = descriptors
            changed += 1
    CONFIG.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{changed} change(s) written to {CONFIG.relative_to(ROOT)}.")
    for m in missing:
        print(f"  Not in HuMeta any more: {m}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
