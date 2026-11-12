import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from xml.etree import ElementTree as ET

from stemed_digest import build, commons, crossref, digest, dissertations, preprints
from stemed_digest.models import Item, utc_stamp

FIX = Path(__file__).parent / "fixtures"
CROSSREF = json.loads((FIX / "crossref_works.json").read_text(encoding="utf-8"))["items"]
KC = json.loads((FIX / "kcworks.json").read_text(encoding="utf-8"))
COMMONS_CFG = build.load_config("commons.json")
SERVERS = build.load_config("preprints.json")
DISS_CFG = build.load_config("dissertations.json")
EDARXIV = json.loads((FIX / "edarxiv.json").read_text(encoding="utf-8"))
ARXIV = (FIX / "arxiv.xml").read_text(encoding="utf-8")
OPENALEX = json.loads((FIX / "openalex_dissertations.json").read_text(encoding="utf-8"))
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
        self.assertEqual(params["filter"], "from-created-date:2026-10-23,type:journal-article")
        self.assertEqual(params["cursor"], "*")

    def test_fetch_follows_the_cursor_through_every_page(self):
        def work(n):
            return {"DOI": f"10.1/{n}", "type": "journal-article", "title": [f"Article {n}"],
                    "created": {"date-time": "2026-11-01T00:00:00Z"}, "published": {"date-parts": [[2026]]}}
        pages = [{"message": {"items": [work(1), work(2)], "next-cursor": "c2"}},
                 {"message": {"items": [work(3), work(4)], "next-cursor": "c3"}},
                 {"message": {"items": [work(5)], "next-cursor": "c4"}}]
        with mock.patch.object(crossref, "get_json", side_effect=pages) as get:
            items = crossref.fetch_journal({"name": "X", "issn": "1"}, "2025-11-06", rows=2)
        self.assertEqual(len(items), 5)
        self.assertEqual([c[0][1]["cursor"] for c in get.call_args_list], ["*", "c2", "c3"])

    def test_skips_back_catalog_re_registrations(self):
        old = {"DOI": "10.3928/old", "type": "journal-article", "title": ["Nursing Education in 1968"],
               "created": {"date-parts": [[2026, 3, 1]], "date-time": "2026-03-01T00:00:00Z"},
               "published": {"date-parts": [[1968, 5]]}}
        last_year = dict(old, DOI="10.3928/ok", title=["Published last year, registered this year"],
                         published={"date-parts": [[2025, 12]]})
        items = crossref.parse_works([old, last_year], {"name": "J", "disciplines": []})
        self.assertEqual([i.id for i in items], ["doi:10.3928/ok"])


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


class PreprintTests(unittest.TestCase):
    def test_edarxiv_keeps_latest_stem_preprints_only(self):
        items = preprints.parse_osf(EDARXIV["data"], SERVERS["edarxiv"], "2025-11-06")
        titles = [i.title for i in items]
        self.assertEqual(len(items), 2, titles)
        immunology = next(i for i in items if "immunology" in i.title)
        self.assertEqual(immunology.id, "osf:z98uj")
        self.assertEqual(immunology.url, "https://osf.io/preprints/edarxiv/z98uj")
        self.assertEqual(immunology.authors, ["Ana Ruiz", "Lee Chen"])        # non-bibliographic left out
        self.assertEqual(immunology.disciplines, ["Bioscience"])
        self.assertEqual(immunology.version_of, "10.1128/jmbe.00001-26")
        self.assertEqual((immunology.source, immunology.kind, immunology.venue), ("preprint", "Preprint", "EdArXiv"))
        self.assertIn("construct:self_efficacy", immunology.keywords)          # matched in the abstract
        self.assertTrue(any(t.startswith("Feedback without marks") for t in titles))  # STEM subject + math tags
        self.assertFalse(any("Prompt Engineering" in t for t in titles))       # not engineering education

    def test_stem_check(self):
        self.assertEqual(preprints.stem_disciplines("Teaching chemistry with games"), (True, ["Chemistry"]))
        self.assertFalse(preprints.stem_disciplines("Prompt engineering for teachers")[0])
        self.assertFalse(preprints.stem_disciplines("School climate and attendance")[0])
        self.assertFalse(preprints.stem_disciplines("The science of reading in grade 2")[0])
        self.assertTrue(preprints.stem_disciplines("Fractions in grade 4")[0])
        self.assertTrue(preprints.stem_disciplines("Belonging in STEM majors")[0])
        self.assertFalse(preprints.stem_disciplines("Stem cells of policy")[0])   # STEM only in capitals

    def test_arxiv_parses_and_stops_at_the_window(self):
        items, done = preprints.parse_arxiv(ARXIV, SERVERS["arxiv"], "2026-10-23")
        self.assertTrue(done)
        self.assertEqual([i.id for i in items], ["arxiv:2611.04148", "arxiv:2611.06943"])
        first = items[0]
        self.assertTrue(first.title.startswith("Active Learning with Generative AI in Introductory Physics: A Multi"))
        self.assertNotIn("\n", first.title)
        self.assertEqual(first.url, "https://arxiv.org/abs/2611.04148")
        self.assertEqual(first.disciplines, ["Physics"])
        self.assertIn("construct:conceptual_understanding", first.keywords)
        self.assertEqual(items[1].version_of, "10.1119/5.0349953")

    def test_arxiv_fetch_pages_politely(self):
        with mock.patch.object(preprints, "get_text", return_value=ARXIV) as get, mock.patch.object(preprints.time, "sleep"):
            items = preprints.fetch_arxiv(SERVERS["arxiv"], "2026-10-23", page=3)
        self.assertEqual(get.call_count, 1)
        self.assertEqual(len(items), 2)

    def test_published_preprint_is_listed_once_as_the_article(self):
        article = Item(id="doi:10.1119/5.0349953", source="journal", title="Getting the picture", authors=[],
                       venue="The Physics Teacher", url="u", added="2026-11-03T00:00:00Z")
        pre = preprints.parse_arxiv(ARXIV, SERVERS["arxiv"], "2026-10-23")[0]
        kept = build.drop_preprints_of_listed_articles([article] + pre)
        self.assertEqual([i.id for i in kept], ["doi:10.1119/5.0349953", "arxiv:2611.04148"])


class DissertationTests(unittest.TestCase):
    def test_keeps_recently_indexed_english_stem_theses(self):
        items = dissertations.parse_works(OPENALEX["results"], DISS_CFG, "2025-11-06", NOW)
        titles = [i.title for i in items]
        self.assertFalse(any(t.startswith("PENGARUH") for t in titles))                 # not English
        self.assertFalse(any("number line" in t for t in titles))                       # indexed 2016, re-dated
        self.assertFalse(any("Green consumer" in t for t in titles))                    # topic not followed
        self.assertTrue(any(t.startswith("Can Medical School") for t in titles))        # English, no "the"
        chem = next(i for i in items if "chemistry" in i.title)
        self.assertEqual(chem.venue, "Queen's University Library")
        self.assertEqual(chem.url, "https://hdl.handle.net/1974/36937")                  # no DOI: landing page
        self.assertEqual(chem.disciplines, ["Chemistry", "Science Education"])
        self.assertEqual((chem.source, chem.kind), ("dissertation", "Dissertation or thesis"))
        nurse = next(i for i in items if i.title.startswith("FROM STUDENT"))
        self.assertEqual(nurse.published, "2027")                                       # future date shown as year
        self.assertEqual(nurse.url, "https://doi.org/10.7273/000007880")
        self.assertEqual(nurse.venue, "Washington State University")

    def test_english_check(self):
        self.assertTrue(dissertations.looks_english("Trusting Postgraduate Nursing Trainees to Care"))
        self.assertTrue(dissertations.looks_english("Growing Up Green"))
        self.assertFalse(dissertations.looks_english("Stem eğitimi bağlamında kavramsal entegrasyon modeli"))

    def test_fetch_builds_the_query_and_hides_the_key(self):
        with mock.patch.object(dissertations, "get_json", return_value=OPENALEX) as get, \
                mock.patch.dict("os.environ", {"OPENALEX_API_KEY": "k123"}):
            dissertations.fetch_dissertations(DISS_CFG, "2025-11-06", NOW)
        params = get.call_args[0][1]
        self.assertIn("type:dissertation", params["filter"])
        self.assertIn("language:en", params["filter"])
        self.assertIn("primary_location.source.id:!S4306400562", params["filter"])
        self.assertIn("primary_topic.id:T10072|", params["filter"])
        self.assertEqual(params["api_key"], "k123")


def no_extra_sources(test):
    """Build tests run offline: preprint and dissertation sources return nothing."""
    for name, module in (("fetch_edarxiv", preprints), ("fetch_arxiv", preprints), ("fetch_dissertations", dissertations)):
        patcher = mock.patch.object(module, name, return_value=[])
        patcher.start()
        test.addCleanup(patcher.stop)


class BuildTests(unittest.TestCase):
    def setUp(self):
        no_extra_sources(self)

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
                         "feeds/preprints.xml", "feeds/dissertations.xml",
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
            self.assertIn("### [Chemistry Education Research and Practice](https://pubs.rsc.org/en/journals/journalissues/rp) (4)", journal_part)
            self.assertLess(md.index("Recently added to STEMEd+ Commons"), md.index("New in journals"))

    def test_classroom_digest_lists_only_classroom_journals(self):
        def fetch(journal, since):
            # The same fixture articles, once for a research journal and once for a classroom journal.
            return crossref.parse_works(CROSSREF, journal) if journal["issn"] in ("1756-1108", "0021-9584") else []

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            with mock.patch.object(commons, "get_json", side_effect=fake_kc_get):
                payload = build.run(out, None, NOW, fetch_journals=fetch)
            flags = {j["name"]: j["classroom"] for j in payload["journals"]}
            self.assertTrue(flags["Journal of Chemical Education"])
            self.assertTrue(flags["The Physics Teacher"])
            self.assertTrue(flags["Science Scope"])
            self.assertFalse(flags["Chemistry Education Research and Practice"])
            md = (out / "classroom.md").read_text(encoding="utf-8")
            self.assertIn("For the classroom", md)
            self.assertIn("Journal of Chemical Education", md)
            self.assertNotIn("## [Chemistry Education Research and Practice]", md)
            html_page = (out / "classroom.html").read_text(encoding="utf-8")
            self.assertIn("<h1>STEMEd+ Digest: For the classroom", html_page)
            self.assertIn('class="sp-bar"', html_page)
            rss = ET.parse(out / "feeds" / "classroom.xml").getroot()
            venues = {i.findtext("description") for i in rss.findall("./channel/item")}
            self.assertTrue(venues)
            self.assertTrue(all("Journal of Chemical Education" in v for v in venues))

    def test_preprints_and_dissertations_flow_through_to_digest_and_feeds(self):
        asked = {}

        def arxiv(config, since):
            asked["arxiv"] = since
            return preprints.parse_arxiv(ARXIV, config, since)[0]

        def diss(config, since, now, window):
            asked["diss"] = since
            return dissertations.parse_works(OPENALEX["results"], config, since, now)

        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(commons, "get_json", side_effect=fake_kc_get):
            out = Path(tmp) / "out"
            payload = build.run(out, None, NOW, fetch_journals=self.fetch_journal, fetch_arxiv=arxiv,
                                fetch_dissertations=diss)
            self.assertEqual(asked, {"arxiv": "2025-11-06", "diss": "2025-11-06"})   # first run: whole year
            md = (out / "digest.md").read_text(encoding="utf-8")
            prev = Path(tmp) / "prev.json"
            prev.write_text((out / "items.json").read_text(encoding="utf-8"), encoding="utf-8")
            build.run(Path(tmp) / "out2", str(prev), NOW, fetch_journals=self.fetch_journal, fetch_arxiv=arxiv,
                      fetch_dissertations=diss)
            self.assertEqual(asked, {"arxiv": "2026-10-23", "diss": "2026-10-23"})   # later runs: two weeks
            rss = ET.parse(out / "feeds" / "preprints.xml").getroot()
        self.assertEqual(len(rss.findall("./channel/item")), 2)
        self.assertEqual(payload["preprint_servers"][0]["name"], "EdArXiv")
        _, rest = md.split("## New preprints")
        pre, diss_part = rest.split("## New dissertations and theses")
        self.assertIn("Preprints have not been peer reviewed.", pre)
        self.assertIn("[Active Learning with Generative AI", pre)
        self.assertIn("Can Medical School Communication", diss_part)
        self.assertIn("2 preprints, and 1 dissertation or thesis.", md)

    def test_carries_over_previous_items_and_drops_old_journal_articles(self):
        old = [Item(id="doi:10.1/kept", source="journal", title="Kept", authors=[], venue="J", url="u",
                    added="2026-09-01T00:00:00Z"),
               Item(id="doi:10.1/dropped", source="journal", title="Too old", authors=[], venue="J", url="u",
                    added="2025-06-01T00:00:00Z")]
        with tempfile.TemporaryDirectory() as tmp:
            prev = Path(tmp) / "prev.json"
            prev.write_text(json.dumps({"items": [i.to_dict() for i in old]}), encoding="utf-8")
            ids = {i["id"] for i in self.run_build(Path(tmp) / "out", str(prev))["items"]}
        self.assertIn("doi:10.1/kept", ids)
        self.assertNotIn("doi:10.1/dropped", ids)
        self.assertIn("kcworks:agonly-0001", ids)      # Commons works are never dropped for age

    def test_new_journals_get_the_whole_window_and_listed_ones_a_short_lookback(self):
        asked = {}
        def record(journal, since):
            asked[journal["name"]] = since
            return []
        listed = Item(id="doi:10.1/a", source="journal", title="A", authors=[], venue="Medical Education", url="u",
                      added="2026-10-01T00:00:00Z")
        with tempfile.TemporaryDirectory() as tmp:
            prev = Path(tmp) / "prev.json"
            prev.write_text(json.dumps({"items": [listed.to_dict()]}), encoding="utf-8")
            with mock.patch.object(commons, "get_json", side_effect=fake_kc_get):
                build.run(Path(tmp) / "out", str(prev), NOW, fetch_journals=record)
        self.assertEqual(asked["Medical Education"], "2026-10-23")      # 14-day lookback
        self.assertEqual(asked["Medical Teacher"], "2025-11-06")        # never listed: full 365 days

    def test_failed_source_stops_the_build_unless_allowed(self):
        def broken(journal, since):
            raise RuntimeError("Crossref is down")
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(commons, "get_json", side_effect=fake_kc_get):
            with self.assertRaises(SystemExit):
                build.run(Path(tmp), None, NOW, fetch_journals=broken)
            payload = build.run(Path(tmp), None, NOW, fetch_journals=broken, allow_errors=True)
        journal_names = {j["name"] for j in build.load_config("journals.json")["journals"]}
        self.assertTrue(all(not s["ok"] for s in payload["status"] if s["source"] in journal_names))
        self.assertEqual(len(payload["items"]), 3)

    def test_empty_week_still_invites_deposits(self):
        d = digest.build([], build.load_config("site.json"), COMMONS_CFG, NOW)
        md = digest.to_markdown(d, build.load_config("site.json"), COMMONS_CFG)
        self.assertIn("Nothing new this week.", md)
        self.assertIn("Add it to the [STEMEd+ Commons Collection]", md)


class JournalListTests(unittest.TestCase):
    def test_every_journal_has_a_website(self):
        for j in build.load_config("journals.json")["journals"]:
            self.assertRegex(j.get("url", ""), r"^https://[^\s/]+\.[a-z]{2,}(/|$)", j["name"])

    def test_digest_links_journal_names(self):
        item = crossref.parse_works(CROSSREF, {"name": "J", "issn": "1756-1108", "disciplines": ["Chemistry"]})[0]
        item.added = "2026-11-05T00:00:00Z"
        site = build.load_config("site.json")
        d = digest.build([item], site, COMMONS_CFG, NOW, {"J": "https://example.org/j"})
        self.assertIn("### [J](https://example.org/j)", digest.to_markdown(d, site, COMMONS_CFG))
        self.assertIn('<a href="https://example.org/j"', digest.to_html(d, site, COMMONS_CFG))


class StampTests(unittest.TestCase):
    def test_utc_stamp(self):
        self.assertEqual(utc_stamp("2026-10-31T16:20:46.345325+00:00"), "2026-10-31T16:20:46Z")
        self.assertEqual(utc_stamp("2026-11-06T05:43:32Z"), "2026-11-06T05:43:32Z")
        self.assertEqual(utc_stamp("2026-11-06T01:00:00-05:00"), "2026-11-06T06:00:00Z")


if __name__ == "__main__":
    unittest.main()
