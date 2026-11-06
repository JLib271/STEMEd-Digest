import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from xml.etree import ElementTree as ET

from stemed_digest import build, commons, crossref, digest
from stemed_digest.models import Item, utc_stamp

FIX = Path(__file__).parent / "fixtures"
CROSSREF = json.loads((FIX / "crossref_works.json").read_text(encoding="utf-8"))["items"]
KC = json.loads((FIX / "kcworks.json").read_text(encoding="utf-8"))
COMMONS_CFG = build.load_config("commons.json")
NOW = dt.datetime(2026, 11, 6, 18, 0, tzinfo=dt.timezone.utc)


def fake_kc_get(url, params=None, **_):
    if url.endswith("/subcommunities"):
        return KC["subcommunities"]
    slug = url.rstrip("/").split("/")[-2]
    return KC["records"][slug]


class CrossrefTests(unittest.TestCase):
    def setUp(self):
        self.items = crossref.parse_works(CROSSREF, {"name": "Test Journal", "disciplines": ["Chemistry"]})

    def test_skips_issue_furniture_corrections_and_non_articles(self):
        titles = [i.title for i in self.items]
        for junk in ("Acknowledgment", "Issue Information", "Review of: something"):
            self.assertNotIn(junk, titles)
        self.assertFalse(any(t.startswith("Correction") for t in titles))
        self.assertEqual(len(self.items), 5)

    def test_cleans_titles_and_normalizes_fields(self):
        jce = next(i for i in self.items if "Ammonia" in i.title)
        self.assertEqual(jce.title, "Catalytic Hydrolysis of Ammonia Borane: An Integrated Undergraduate "
                                    "Experiment on Hydrogen Production")
        self.assertEqual(jce.id, "doi:10.1021/acs.jchemed.6c00001")
        self.assertEqual(jce.added, "2026-11-06T14:01:39Z")

    def test_decodes_html_entities_in_titles(self):
        self.assertIn("Book Review: Jinfa Cai & Roza Leikin (Eds.)", [i.title for i in self.items])

    def test_keeps_year_only_publication_dates(self):
        cerp = next(i for i in self.items if "redox" in i.title)
        self.assertEqual(cerp.published, "2026")
        self.assertEqual(cerp.authors, ["CERP Consortium"])

    def test_disciplines_from_journal_and_optionally_titles(self):
        plain = next(i for i in self.items if "Medical students" in i.title)
        self.assertEqual(plain.disciplines, ["Chemistry"])
        general = crossref.parse_works(CROSSREF, {"name": "JRST", "disciplines": ["Science Education"],
                                                  "classify_titles": True})
        med = next(i for i in general if "Medical students" in i.title)
        self.assertEqual(med.disciplines, ["Health Education", "Physics", "Science Education"])

    def test_fetch_asks_crossref_by_registration_date(self):
        with mock.patch.object(crossref, "get_json", return_value={"message": {"items": []}}) as get:
            crossref.fetch_journal({"name": "X", "issn": "1756-1108"}, "2026-10-23")
        url, params = get.call_args[0]
        self.assertEqual(url, "https://api.crossref.org/journals/1756-1108/works")
        self.assertEqual(params["filter"], "from-created-date:2026-10-23")
        self.assertEqual(params["sort"], "created")


class CommonsTests(unittest.TestCase):
    def setUp(self):
        with mock.patch.object(commons, "get_json", side_effect=fake_kc_get):
            self.items = {i.id: i for i in commons.fetch_commons(COMMONS_CFG)}

    def test_reads_subcollections_and_merges_duplicates(self):
        # The lesson plan is in both the parent and a subcollection; the ag-only work is
        # only in the subcollection, like most of STEM in Agricultural Education.
        self.assertEqual(sorted(self.items), ["kcworks:6xc17-xze35", "kcworks:agonly-0001", "kcworks:wnm5z-00x75"])

    def test_record_fields(self):
        gci = self.items["kcworks:wnm5z-00x75"]
        self.assertEqual(gci.authors, ["Julie C Libarkin", "Steven W Anderson"])
        self.assertEqual(gci.added, "2026-10-31T16:20:46Z")
        self.assertEqual(gci.published, "2006")
        self.assertEqual(gci.kind, "Book section")
        self.assertEqual(gci.url, "https://works.hcommons.org/records/wnm5z-00x75")
        self.assertEqual(gci.disciplines, ["Earth Science"])   # from its "geoscience" keyword
        self.assertEqual(gci.collections, [])

    def test_subcollection_label_and_discipline(self):
        lesson = self.items["kcworks:6xc17-xze35"]
        self.assertEqual(lesson.collections, ["STEM in Agricultural Education"])
        self.assertIn("Agriculture", lesson.disciplines)
        self.assertEqual(lesson.kind, "Curriculum")


class BuildTests(unittest.TestCase):
    def fetch_journal(self, journal, since):
        return crossref.parse_works(CROSSREF, journal) if journal["issn"] == "1756-1108" else []

    def run_build(self, out, previous=None):
        with mock.patch.object(commons, "get_json", side_effect=fake_kc_get):
            return build.run(out, previous, NOW, fetch_journals=self.fetch_journal)

    def test_full_build_writes_site_feeds_and_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            payload = self.run_build(out)
            self.assertEqual(len(payload["items"]), 8)
            for name in ("index.html", "items.json", "digest.html", "digest.md", "feeds/all.xml",
                         "feeds/stemed-commons.xml", "feeds/chemistry.xml", "feeds/health-education.xml"):
                self.assertTrue((out / name).exists(), name)
            rss = ET.parse(out / "feeds" / "stemed-commons.xml").getroot()
            self.assertEqual(len(rss.findall("./channel/item")), 3)
            md = (out / "digest.md").read_text(encoding="utf-8")
            commons_part, journal_part = md.split("## New in journals")
            self.assertIn("## Recently added to STEMEd+ Commons", commons_part)
            self.assertIn("Water Cycle Lesson Plan", commons_part)        # deposited Oct 30, within the week
            self.assertNotIn("Soil Science Lab", commons_part)           # deposited 2025
            self.assertIn("Add it to the [STEMEd+ Commons Collection]", commons_part)
            self.assertIn("### Chemistry Education Research and Practice (4)", journal_part)
            self.assertLess(md.index("Recently added to STEMEd+ Commons"), md.index("New in journals"))

    def test_carries_over_previous_items_and_drops_old_journal_articles(self):
        old = [Item(id="doi:10.1/kept", source="journal", title="Kept", authors=[], venue="J", url="u",
                    added="2026-09-01T00:00:00Z"),
               Item(id="doi:10.1/dropped", source="journal", title="Too old", authors=[], venue="J", url="u",
                    added="2025-01-01T00:00:00Z")]
        with tempfile.TemporaryDirectory() as tmp:
            prev = Path(tmp) / "prev.json"
            prev.write_text(json.dumps({"items": [i.to_dict() for i in old]}), encoding="utf-8")
            ids = {i["id"] for i in self.run_build(Path(tmp) / "out", str(prev))["items"]}
        self.assertIn("doi:10.1/kept", ids)
        self.assertNotIn("doi:10.1/dropped", ids)
        self.assertIn("kcworks:agonly-0001", ids)      # Commons works are never dropped for age

    def test_failed_source_stops_the_build_unless_allowed(self):
        def broken(journal, since):
            raise RuntimeError("Crossref is down")
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(commons, "get_json", side_effect=fake_kc_get):
            with self.assertRaises(SystemExit):
                build.run(Path(tmp), None, NOW, fetch_journals=broken)
            payload = build.run(Path(tmp), None, NOW, fetch_journals=broken, allow_errors=True)
        self.assertTrue(all(not s["ok"] for s in payload["status"] if s["source"] != "STEMEd+ Commons"))
        self.assertEqual(len(payload["items"]), 3)

    def test_empty_week_still_invites_deposits(self):
        d = digest.build([], build.load_config("site.json"), COMMONS_CFG, NOW)
        md = digest.to_markdown(d, build.load_config("site.json"), COMMONS_CFG)
        self.assertIn("Nothing new this week.", md)
        self.assertIn("Add it to the [STEMEd+ Commons Collection]", md)


class StampTests(unittest.TestCase):
    def test_utc_stamp(self):
        self.assertEqual(utc_stamp("2026-10-31T16:20:46.345325+00:00"), "2026-10-31T16:20:46Z")
        self.assertEqual(utc_stamp("2026-11-06T05:43:32Z"), "2026-11-06T05:43:32Z")
        self.assertEqual(utc_stamp("2026-11-06T01:00:00-05:00"), "2026-11-06T06:00:00Z")


if __name__ == "__main__":
    unittest.main()
