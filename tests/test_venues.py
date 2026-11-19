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

    def test_combine_puts_journals_in_both_sections_when_in_doubt(self):
        data = venues.load()
        journals = [
            {"name": "CBE-Life Sciences Education", "url": "https://x.org", "publisher": "ASCB", "disciplines": ["Bioscience"]},
            {"name": "Journal of Research in Science Teaching", "url": "https://y.org", "publisher": "Wiley", "disciplines": ["Science Education"]},
            {"name": "Science Scope", "url": "https://z.org", "publisher": "NSTA", "disciplines": ["Science Education"], "classroom": True},
            {"name": "Physics Education", "url": "https://w.org", "publisher": "IOP", "disciplines": ["Physics"], "classroom": True},
            {"name": "Connected Science Learning", "url": "https://c.org", "publisher": "T&F", "disciplines": ["Science Education"], "classroom": True},
            {"name": "Isis", "url": "https://i.org", "publisher": "Chicago", "disciplines": ["History & Philosophy of Science"]},
            {"name": "A Journal Added Next Year", "url": "https://n.org", "publisher": "New", "disciplines": ["Chemistry"]},
            {"name": "Science & Education", "url": "https://s.org", "publisher": "Springer", "disciplines": ["History & Philosophy of Science", "Science Education"]},
        ]
        out = {v["name"]: v for v in venues.combine(data, journals)["venues"]}
        both, teaching, research = ["teaching", "research"], ["teaching"], ["research"]
        self.assertEqual(out["CBE—Life Sciences Education"]["sections"], both)
        self.assertNotIn("CBE-Life Sciences Education", out)
        self.assertEqual(out["Teaching & Learning Inquiry"]["sections"], both)
        self.assertEqual(out["Journal of Chemical Education"]["sections"], both)
        self.assertEqual(out["PERC Proceedings" if "PERC Proceedings" in out else "Physics Education Research Conference (PERC) Proceedings"]["sections"], both)
        # In doubt, and any new journal: both.
        self.assertEqual(out["Physics Education"]["sections"], both)
        self.assertEqual(out["A Journal Added Next Year"]["sections"], both)
        self.assertEqual(out["A Journal Added Next Year"]["kind"], "education")
        self.assertEqual(out["Science & Education"]["sections"], both)
        # Clearly one kind only.
        self.assertEqual(out["The Physics Teacher"]["sections"], teaching)
        self.assertEqual(out["Connected Science Learning"]["sections"], teaching)
        self.assertEqual(out["Journal of Research in Science Teaching"]["sections"], research)
        self.assertEqual(out["Journal of Research in Science Teaching"]["kind"], "journal")
        self.assertEqual(out["Isis"]["sections"], research)
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
