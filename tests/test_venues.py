import copy
import tempfile
import unittest
from pathlib import Path

from stemed_digest import venues


class VenueTests(unittest.TestCase):
    def test_venue_list_is_complete_and_uses_shared_disciplines(self):
        data = venues.load()
        self.assertGreaterEqual(len(data["venues"]), 25)
        self.assertTrue(any(v.get("first_timer") for v in data["venues"]))
        self.assertTrue(any(v["access"] == "diamond" for v in data["venues"]))

    def test_check_rejects_unknown_values(self):
        data = venues.load()
        bad = copy.deepcopy(data)
        bad["venues"][0]["access"] = "free-ish"
        bad["venues"][1]["disciplines"] = ["Astrology"]
        bad["venues"][2]["checked"] = "Nov 2026"
        with self.assertRaises(ValueError) as e:
            venues.check(bad)
        msg = str(e.exception)
        self.assertIn("unknown access", msg)
        self.assertIn("Astrology", msg)
        self.assertIn("YYYY-MM", msg)

    def test_write_publishes_venues_json(self):
        with tempfile.TemporaryDirectory() as d:
            venues.write(Path(d))
            self.assertIn('"venues"', (Path(d) / "venues.json").read_text())

    def test_page_links_back_and_explains_irb_and_cirtl(self):
        page = (venues.ROOT / "site" / "publish.html").read_text()
        for needed in ("venues.json", "journals.json", 'id="sec"', "IRB", "CIRTL", "stemed-conferences", "stemed-deadlines", "stemedplus-theme.css"):
            self.assertIn(needed, page)

    def test_combine_lists_digest_journals_in_two_sections(self):
        data = venues.load()
        journals = [
            {"name": "CBE-Life Sciences Education", "url": "https://x.org", "publisher": "ASCB", "disciplines": ["Bioscience"]},
            {"name": "Journal of Research in Science Teaching", "url": "https://y.org", "publisher": "Wiley", "disciplines": ["Science Education"]},
            {"name": "Science Scope", "url": "https://z.org", "publisher": "NSTA", "disciplines": ["Science Education"], "classroom": True},
            {"name": "Physics Education", "url": "https://w.org", "publisher": "IOP", "disciplines": ["Physics"], "classroom": True},
        ]
        out = {v["name"]: v for v in venues.combine(data, journals)["venues"]}
        # A curated research venue the Digest follows is in both sections.
        self.assertEqual(out["CBE—Life Sciences Education"]["sections"], ["teaching", "research"])
        self.assertNotIn("CBE-Life Sciences Education", out)
        # A curated SoTL venue the Digest does not follow stays in Teaching & SoTL.
        self.assertEqual(out["Teaching & Learning Inquiry"]["sections"], ["teaching"])
        # A practitioner journal can be put in both by hand.
        self.assertEqual(out["Journal of Chemical Education"]["sections"], ["teaching", "research"])
        # Digest-only journals: research goes to Research, classroom to Teaching & SoTL.
        self.assertEqual(out["Journal of Research in Science Teaching"]["sections"], ["research"])
        self.assertEqual(out["Journal of Research in Science Teaching"]["kind"], "journal")
        self.assertEqual(out["Physics Education"]["sections"], ["teaching"])
        # The combined NSTA entry stands for Science Scope.
        self.assertNotIn("Science Scope", out)

    def test_every_digest_journal_is_on_the_page(self):
        import json
        journals = json.loads((venues.ROOT / "config" / "journals.json").read_text())["journals"]
        data = venues.combine(venues.load(), journals)
        listed = set()
        for v in data["venues"]:
            listed.update(venues.key(n) for n in v.get("digest_names") or [v["name"]])
        self.assertEqual([j["name"] for j in journals if venues.key(j["name"]) not in listed], [])
        self.assertTrue(all(v["sections"] for v in data["venues"]))


if __name__ == "__main__":
    unittest.main()
