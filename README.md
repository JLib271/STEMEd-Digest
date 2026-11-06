# STEMEd+ Digest

New work in STEM+ education research and practice, in one place:

* **Journal tables of contents** from 18 journals across biology, chemistry, physics,
  earth science, mathematics, engineering, agriculture, science education, learning
  sciences, and medical and health professions education
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
| **Website** | Search and filter by discipline, journal or collection, source, and date added. New STEMEd+ Commons works are featured at the top. |
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

Journal articles stay listed for 180 days. STEMEd+ Commons works stay listed permanently.

## Suggest a journal

Use the [Suggest a journal](../../issues/new?template=suggest_journal.yml) form. To add it
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
| `config/journals.json` | The journals, their ISSNs and disciplines. `classify_titles` also tags articles by words in their titles, for journals that cover many fields. |
| `config/commons.json` | The STEMEd+ Commons collection, and disciplines for whole subcollections (Entomology Education → Bioscience, STEM in Agricultural Education → Agriculture). |
| `config/site.json` | Title, how many days to look back each run, how long to keep journal articles, and how many days the digest covers. |

## License

Code: MIT. The discipline rules in `stemed_digest/disciplines.py` are copied from
[STEMEd+ Jobs](https://github.com/JLib271/stemed-jobs) (MIT).
