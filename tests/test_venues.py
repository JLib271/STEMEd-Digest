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
        for needed in ("venues.json", "IRB", "CIRTL", "stemed-conferences", "stemed-deadlines", "stemedplus-theme.css"):
            self.assertIn(needed, page)


if __name__ == "__main__":
    unittest.main()
