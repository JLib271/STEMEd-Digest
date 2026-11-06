"""Discipline rules, copied from STEMEd+ Jobs (https://github.com/JLib271/stemed-jobs,
stemed_jobs/disciplines.py, MIT License) so the two projects use the same ten categories.
Only matching_disciplines() and DISCIPLINES are used here."""
import re
from typing import Iterable, List, Sequence, Set, Tuple


# Field and subfield names, as regex alternations without word boundaries. They
# are shared with relevance.py, which looks for "<name> education" in titles.
EARTH_TERMS = (
    r"earth sciences?|geosciences?|geolog(?:y|ical|ists?)|geophysic(?:s|al)|geochemistry|geobiology"
    r"|geomorpholog(?:y|ical)|hydrolog(?:y|ic|ical)|hydrogeology|atmospheric (?:sciences?|chemistry|physics)"
    r"|meteorolog(?:y|ical)|climate|climatology|oceanograph(?:y|ic|ers?)|ocean sciences?|marine sciences?"
    r"|paleontolog(?:y|ists?)|paleoclimat\w*|seismolog(?:y|ists?)|volcanolog(?:y|ists?)|glaciolog(?:y|ists?)"
    r"|mineralog(?:y|ists?)|petrolog(?:y|ists?)|sedimentolog(?:y|ists?)|tectonics|geochronolog(?:y|ists?)"
    r"|planetary sciences?|soil sciences?|environmental sciences?|environmental education|limnolog(?:y|ists?)"
    r"|earth systems?|natural hazards"
)
CHEMISTRY_TERMS = (
    r"chemistr(?:y|ies)|chemical sciences?|chemical education|biochem(?:istry|ical)?|chemical biology"
    r"|geochemistry|atmospheric chemistry|polymer (?:science|chemistry)|molecular sciences?"
)
BIOSCIENCE_TERMS = (
    r"bio(?:logy|logical|science|sciences|engineering)?|life sciences?|molecular biology|genetics|genomics?"
    r"|ecology|microbiology|anatomy|physiology|biochem(?:istry|ical)?|zoolog(?:y|ical|ists?)"
    r"|botan(?:y|ical|ists?)|entomolog(?:y|ical|ists?)|animal sciences?|plant sciences?|neuroscienc(?:e|es|ists?)"
    r"|immunolog(?:y|ists?)|virolog(?:y|ists?)|bacteriolog(?:y|ists?)|biotechnology|bioinformatics"
    r"|biophysics|pharmacolog(?:y|ists?)|toxicolog(?:y|ists?)|ornitholog(?:y|ists?)|mycolog(?:y|ists?)"
    r"|parasitolog(?:y|ists?)|wildlife (?:sciences?|ecology)|chemical biology"
)
PHYSICS_TERMS = (
    r"physics|physicists?|physical sciences?|quantum|astrophysic(?:s|al)|astronom(?:y|ical|ers?)|cosmology"
    r"|space sciences?|space physics|space weather|heliophysics|planetary sciences?|biophysics"
    r"|condensed matter|optics|photonics"
)
# "Medical" also begins benefits boilerplate ("medical, dental and vision
# coverage"), which must not tag a job as Health Education.
HEALTH_TERMS = (
    r"medical(?!,?\s*(?:and\s+)?(?:dental|vision|insurance|benefits?|coverage|leave|plans?|history))"
    r"|medicine|nurs(?:e|es|ing)|midwifery|pharmacy|pharmacists?|pharmaceutical sciences?|pharmaceutics"
    r"|pharmacotherapy|pharmacology|dentistry|dental (?:school|hygiene|medicine|education)|dentists?"
    r"|orthodontics|public health|global health|community health|population health|environmental health"
    r"|occupational health|health sciences?|health professions?|health ?care (?:education|professions?|sciences?"
    r"|administration)|allied health|health education|health informatics|health policy|health services"
    r"|physical therapy|physiotherapy|occupational therapy|speech[- ]language pathology|audiology"
    r"|respiratory therapy|athletic training|physician assistants?|optometry|radiolog(?:y|ic|ical) (?:sciences?|technology)"
    r"|radiology|medical laboratory|clinical laboratory|diagnostic imaging|sonography|paramedics?|kinesiology"
    r"|exercise (?:science|physiology)|nutrition|dietetics|dietitians?|epidemiolog(?:y|ists?)|biostatistics"
    r"|veterinary|osteopathic|physicians?|clinical (?:sciences?|medicine|education)"
    r"|rehabilitation|gerontology|biomedical sciences?|biomedicine"
)


def _terms(alternation: str) -> str:
    return r"\b(?:" + alternation + r")\b"


# Acronyms such as PER, CER, GER and BER are wrapped in (?-i:...) so they only
# match when written in capitals; otherwise "per year" or "per hour" in a
# description would tag a job as Physics.
DISCIPLINE_RULES: Tuple[Tuple[str, re.Pattern], ...] = (
    ("Agriculture", re.compile(r"\bagricultur(?:e|al|a)?\b|\bagri[- ]?science\b|\bag ed\b", re.IGNORECASE)),
    ("Bioscience", re.compile(_terms(BIOSCIENCE_TERMS) + r"|\b(?-i:BER)\b", re.IGNORECASE)),
    ("Chemistry", re.compile(_terms(CHEMISTRY_TERMS) + r"|\b(?-i:CER)\b", re.IGNORECASE)),
    ("Earth Science", re.compile(_terms(EARTH_TERMS) + r"|\b(?-i:GER)\b", re.IGNORECASE)),
    ("Engineering", re.compile(r"\bengineering\b|\bengineer(?:s|ing)?\b", re.IGNORECASE)),
    ("Health Education", re.compile(_terms(HEALTH_TERMS), re.IGNORECASE)),
    (
        "Learning Science",
        re.compile(
            r"\blearning sciences?\b|\bcognitive sciences?\b|\bcognition\b"
            r"|\beducational psychology\b|\blearning analytics\b"
            r"|\binstructional design(?:ers?)?\b|\b(?:learning|educational|education|course) design(?:ers?)?\b"
            r"|\bcurriculum (?:design|development|developers?)\b|\b(?:educational|education|instructional|learning) technolog\w*"
            r"|\b(?:educational|academic|faculty) developers?\b|\bacademic technologists?\b|\bfaculty development\b|\blearning experience design\w*"
            r"|\bteaching and learning cent(?:er|re)s?\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Mathematics",
        re.compile(
            r"\bmathematics\b|\bmath(?:ematics)? education\b|\bmathematical sciences?\b|\bstatistics\b",
            re.IGNORECASE,
        ),
    ),
    ("Physics", re.compile(_terms(PHYSICS_TERMS) + r"|\b(?-i:PER)\b", re.IGNORECASE)),
    (
        "Science Education",
        re.compile(
            r"\bscience education\b|\bscience teaching\b|\bscience teacher education\b"
            r"|\bscience teachers?\b|\bstem education\b|\bstem teaching\b|\bstem teachers?\b"
            r"|\bdiscipline[- ]based education research\b"
            r"|\bdber\b",
            re.IGNORECASE,
        ),
    ),
)

DISCIPLINES = tuple(name for name, _ in DISCIPLINE_RULES)


def matching_disciplines(text: str) -> List[str]:
    return [name for name, pattern in DISCIPLINE_RULES if pattern.search(text)]
