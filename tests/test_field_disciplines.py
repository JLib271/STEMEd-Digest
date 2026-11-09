"""History & Philosophy of Science and Science & Health Communication cover the fields themselves."""
import json
import unittest
from pathlib import Path

from stemed_digest import build, feeds
from stemed_digest.disciplines import DISCIPLINES

ROOT = Path(__file__).resolve().parent.parent


class FieldDisciplineTests(unittest.TestCase):
    def test_feed_names_spell_out_ampersands(self):
        self.assertEqual(feeds.slug("History & Philosophy of Science"), "history-and-philosophy-of-science")
        self.assertEqual(feeds.slug("Earth Science"), "earth-science")

    def test_field_disciplines_come_from_the_shared_list(self):
        self.assertEqual(feeds.FIELD_DISCIPLINES, ("History & Philosophy of Science", "Science & Health Communication"))

    def test_every_configured_discipline_exists(self):
        journals = json.loads((ROOT / "config" / "journals.json").read_text())["journals"]
        topics = build.load_config("dissertations.json")["topics"]
        servers = build.load_config("preprints.json")
        used = {d for j in journals for d in j["disciplines"]}
        used |= {d for t in topics.values() for d in t["disciplines"]}
        used |= {d for s in servers.values() if isinstance(s, dict) for d in s.get("disciplines", [])}
        self.assertLessEqual(used, set(DISCIPLINES))
        self.assertIn("History & Philosophy of Science", used)
        self.assertIn("Science & Health Communication", used)

    def test_issns_are_unique(self):
        journals = json.loads((ROOT / "config" / "journals.json").read_text())["journals"]
        issns = [j["issn"] for j in journals]
        self.assertEqual(len(issns), len(set(issns)))


if __name__ == "__main__":
    unittest.main()
