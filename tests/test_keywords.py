import json
import re
import unittest

from stemed_digest import crossref, keywords

# Real titles from the journals and STEMEd+ Commons (November 2026) and what they should get.
CASES = [
    ("Selective Cognitive and Affective Benefits of 3D-Printed Bacteriophage T4 Models in High School "
     "Molecular Biology Instruction: A Quasi-Experimental Study", {"study_design:quasi_experimental", "education_level:primary"}),
    ("Trajectories of self‐regulated learning patterns across medical students' transition to clerkships: "
     "A longitudinal Q‐method study", {"construct:self_regulated_learning", "study_design:longitudinal"}),
    ("Flipped classroom learning in K-12 redox chemistry: learning gains, video engagement, and implementation factors",
     {"pedagogy:flipped", "education_level:primary", "construct:engagement"}),
    ("Instructor Development of Technological Pedagogical Content Knowledge (TPACK) Self-Efficacy within a "
     "PoP-CURE Professional Development Community of Practice",
     {"construct:self_efficacy", "pedagogy:research_experience", "participant_role:educators", "construct:community_connectedness"}),
    ("The Geoscience Concept Inventory: Application of Rasch Analysis to Concept Inventory Development in Higher Education",
     {"construct:conceptual_understanding", "study_design:instrument_development"}),
    ("Rethinking the Goals of the Laboratory through Students’ Experiences: Findings from 114 Hours of Fieldnotes "
     "in the Laboratory", {"learning_environment:laboratory", "study_design:ethnographic"}),
    ("Chemistry Teachers' Beliefs about Design in Secondary Chemistry Education",
     {"construct:teaching_beliefs", "participant_role:educators", "education_level:primary"}),
]


class MatchingTests(unittest.TestCase):
    def test_real_titles(self):
        for title, expected in CASES:
            with self.subTest(title=title[:50]):
                self.assertEqual(set(keywords.match([title])), expected)

    def test_spelling_variants(self):
        self.assertIn("construct:self_efficacy", keywords.match(["selfefficacy"]))
        self.assertIn("construct:self_efficacy", keywords.match(["self efficacy"]))
        self.assertIn("education_level:primary", keywords.match(["K–12 classrooms"]))
        self.assertIn("construct:conceptual_understanding", keywords.match(["Students' misconceptions"]))

    def test_whole_words_and_acronym_case(self):
        self.assertEqual(keywords.match(["Undergraduate students cure their fears"]), ["education_level:bachelors"])
        self.assertNotIn("education_level:masters", keywords.match(["undergraduate students"]))
        self.assertNotIn("construct:sense_of_belonging", keywords.match(["belongings"]))

    def test_abstracts_count_but_markup_does_not(self):
        works = [{"DOI": "10.1/x", "type": "journal-article", "title": ["A study of chemistry learning"],
                  "created": {"date-time": "2026-11-01T00:00:00Z"},
                  "abstract": "<jats:p>We used <jats:italic>semi-structured interviews</jats:italic> with "
                              "undergraduate students.</jats:p>"}]
        item = crossref.parse_works(works, {"name": "J", "disciplines": ["Chemistry"]})[0]
        self.assertEqual(item.keywords, ["data_collection_method:interview", "education_level:bachelors"])
        self.assertNotIn("abstract", item.to_dict())


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.doc, _ = keywords.load()

    def test_ids_unique_and_groups_known(self):
        ids = [k["id"] for k in self.doc["keywords"]]
        self.assertEqual(len(ids), len(set(ids)))
        for k in self.doc["keywords"]:
            self.assertIn(k["group"], self.doc["groups"])
            self.assertEqual(k["id"], f"{k['humeta'][0]['vocabulary']}:{k['humeta'][0]['term']}")
            self.assertTrue(k.get("match") or k.get("match_case_sensitive"), k["id"])

    def test_every_pattern_compiles(self):
        for k in self.doc["keywords"]:
            self.assertIsInstance(keywords.compile_keyword(k), re.Pattern)


if __name__ == "__main__":
    unittest.main()
