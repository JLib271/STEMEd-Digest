# STEMEd+ Digest

New work in STEM+ education research and practice, in one place:

* **Journal tables of contents** from 68 teaching and education research journals across
  biology, chemistry, physics, earth and environmental science, mathematics and statistics,
  engineering and computing, agriculture, science education, learning sciences, and medical
  and health professions education. 43 are sponsored by professional societies (NABT,
  AAPT, ASEE, NCTM, AMEE, AACP, and more); all come from established publishers, and
  none from MDPI, Frontiers, or predatory publishers.
* **The [STEMEd+ Commons Collection](https://works.hcommons.org/collections/stemedplus/)**
  and all of its subcollections on Knowledge Commons Works, including papers, chapters,
  lesson plans, instruments, figures, and data

Everything is tagged with the same ten disciplines as
[STEMEd+ Jobs](https://github.com/JLib271/stemed-jobs) and the
[STEM+ Education Research Graduate Programs](https://github.com/JLib271/stem-ed-research-programs) list.

🔎 **Website:** https://jlib271.github.io/STEMEd-Digest/ (once GitHub Pages is turned on)

## What you get

| | |
|---|---|
| **Website** | Search and filter by keyword, discipline, journal or collection, source, and date added. New STEMEd+ Commons works are featured at the top. Click a keyword on any listing to see everything with that keyword; the page address then links straight to that view. |
| **Weekly digest** | [`digest.html`](https://jlib271.github.io/STEMEd-Digest/digest.html) covers the last seven days. It opens with **Recently added to STEMEd+ Commons**, with an invitation to share work there, then lists new journal articles by journal. [`digest.md`](https://jlib271.github.io/STEMEd-Digest/digest.md) is the same digest, ready to paste into a STEMEd+ Commons post, newsletter, or email. |
| **RSS feeds** | One for everything, one for STEMEd+ Commons, and one per discipline, in [`feeds/`](https://jlib271.github.io/STEMEd-Digest/feeds/all.xml). |

The site updates itself every day.

## Where the listings come from

* **Journals:** the [Crossref REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/).
  Articles are picked up when they are **registered with Crossref**, not by issue date. Some
  journals record only a publication year, and online-first articles carry later issue
  dates, so filtering by publication date misses them. Issue furniture (Issue Information,
  Editorial Board, Acknowledgments) and corrections are left out.
* **STEMEd+ Commons:** the public [Knowledge Commons Works API](https://mesh-research.github.io/knowledge-commons-works/reference/api.html).
  The collection and each subcollection are read separately, because subcollection works
  are not always in the main collection too. New subcollections are found automatically.
  Works count as new when they are **deposited**, so older work shared in the Commons
  still gets noticed.

Only titles, authors, dates, and links are listed. Abstracts are not copied; every title
links to the original work.

Journal articles stay listed for 12 months, about one volume year even for quarterly
journals. STEMEd+ Commons works stay listed permanently. A journal added to the list gets its
last 12 months on the next run; after that, each daily run looks back 14 days.

Some publishers re-register old issues with Crossref (in 2026, *Journal of Nursing Education*
re-registered articles back to 1962, and *American Journal of Pharmaceutical Education* back to
1937). Anything published more than a year before it was registered is skipped, so back
issues never show up as new.

## Keywords

Listings are tagged with 61 keywords taken from **HuMeta**, the metadata profile for
STEM+ education research, so the digest describes work in the same terms that datasets and
instruments are described with. Each keyword is one or more HuMeta terms, with HuMeta's
verified ERIC Thesaurus descriptors. They come in three groups:

* **What is studied:** HuMeta constructs, such as self-efficacy, sense of belonging, conceptual
  understanding, and disciplinary identity
* **Research approach:** study designs and data collection methods, such as quasi-experimental,
  qualitative, instrument development or validation, interviews, and systematic reviews
* **Teaching and settings:** teaching approaches, learning environments, education levels, and
  participants, such as active learning, flipped classrooms, CUREs, laboratories, K–12, and
  teacher education

Keywords are matched in titles, in abstracts that publishers share with Crossref (used only for
matching, never stored or shown), and in the keywords of STEMEd+ Commons works. Matching is
automatic, so a listing can miss a keyword that fits it or, less often, get one that doesn't.

The keywords live in [`config/keywords.json`](config/keywords.json): each has its HuMeta terms,
ERIC descriptors, and the phrases that count as a match, built from HuMeta's synonyms. To pick
up changes to HuMeta's labels or ERIC links, run `python scripts/sync_humeta.py <path to HuMeta>`.
It never changes the match phrases, which are edited by hand.

## Suggest a journal

Use the [Suggest a journal](../../issues/new?template=suggest_journal.yml) form. Journals
should publish STEM+ teaching or education research and come from a professional society or
an established publisher; journals from MDPI, Frontiers, or predatory publishers are not added. To add it
yourself, add an entry to [`config/journals.json`](config/journals.json) with the ISSN that
Crossref lists new articles under. Some journals use their online ISSN and others their
print ISSN; Academic Medicine, for example, moved to Oxford University Press in 2026 and
lists new articles under 1938-808X.

## Running it

Standard-library Python 3.10+ only; there is nothing to install.

```bash
python -m unittest discover -s tests -t .     # tests (no network)
python -m stemed_digest --out output            # fetch everything and build the site in output/
```

`.github/workflows/update.yml` runs this every day and publishes to GitHub Pages. It carries
listings over from the published site's `items.json`, so the repository never needs
data commits. Turn it on once in **Settings → Pages → Source: GitHub Actions**.

Optionally, add a repository variable `CONTACT_EMAIL` (**Settings → Secrets and variables →
Actions → Variables**). Crossref uses it to contact the maintainer about problems and serves
identified requests from a faster pool. Without it, requests are anonymous.

## Settings

| File | What it controls |
|---|---|
| `config/journals.json` | The journals, their ISSNs, sponsoring societies, and disciplines. `classify_titles` also tags articles by words in their titles, for journals that cover many fields. |
| `config/commons.json` | The STEMEd+ Commons collection, and disciplines for whole subcollections (Entomology Education → Bioscience, STEM in Agricultural Education → Agriculture). |
| `config/keywords.json` | The HuMeta keywords, their ERIC descriptors, and match phrases. |
| `config/site.json` | Title, how many days to look back each run (14), how long to keep journal articles (365 days), and how many days the digest covers (7). |

## License

Code: MIT. The discipline rules in `stemed_digest/disciplines.py` are copied from
[STEMEd+ Jobs](https://github.com/JLib271/stemed-jobs) (MIT).
