# MagicTagger: Open Infrastructure for Computational Analysis of Russian Folktales

MagicTagger is a locally deployable (Docker) tool for folklorists that turns a corpus of Russian  tales of magic into a reproducible analytical environment. It combines ATU-type suggestions, evidential highlights, map/timeline views and Linked Open Data exports.

> Status: early-stage research prototype. This repository hosts both the corpus and the planned application code.

---

## 1. Goal

Provide a small, self-contained workbench that allows a researcher to:

- explore a curated corpus of Russian magic tales from Estonian Folklore Archive collections,
- obtain Top-3 ATU type suggestions for external texts in Russian,
- inspect evidential highlights and within-type variation,
- export LOD data packages for further analysis.

The emphasis is on reproducibility (versioned corpus, scripted processing) and local control (no server-side storage; runs on the researcher’s machine).

---

## 2. Core Features (planned)

- **Top-3 ATU type suggestions** for Russian input (multi-label, calibrated scores).
- **Maps & timelines** for tales, narrators and collectors (region, decade).
- **Linked Open Data export**: JSON-LD per item; RDF/Turtle batch export.
- **Ephemeral processing** by default: no automatic saving; data is downloaded explicitly by the user.

Details are described in `docs/Magic Tagger — Product Brief v1.3.pdf`.

---

## 3. Licensing

MagicTagger distinguishes between **code**, **derived data** and **archival materials**.

- **Code**:  
  GNU Affero General Public License v3.0 (AGPL-3.0-only).  

- **Derived transcriptions** (produced within this project):  
  Recommended **CC BY 4.0** for public releases, configurable for deployment.

- **Scans and underlying metadata** (Estonian Folklore Archive collections):  
  Not redistributed here. Usage follows the policies and terms of the respective archives.

- **External Corpus B** (if used):  
  Optional, read-only, clearly labelled as “external source” in the interface and exports.

For a more detailed policy see `docs/permissions&licensing.md`.

---

## 4. Repository Structure (top level)

```text
magic_tagger/
├─ README.md                 # this file: project overview
├─ LICENSE                   # AGPL-3.0-only for the code
├─ .gitignore
│
├─ data/
│  ├─ index/
│  │  └─ corpus_a_index.xlsx    # main index of all tales (one row per tale)
│  │
│  ├─ raw/
│  │  ├─ transcriptions_local/   # transcriptions of not digitized texts
│  │   
│  └─ processed/                 # datasets processed for analysis 
│     
├─ docs/
│  ├─ Magic Tagger — Product Brief v1.3.pdf   
│  ├─ permissions&licensing.md 
│  ├─ rdf/                        # ontologies to be used (DC, SKOS, etc.)
│  │  ├─ ontology_overview.md    
│  ├─ metadata/
│  │  ├─ metadata_schema.md      # description of metadata fields
│  │  └─ metadata_examples.csv   # small sample of records
│  └─ archive_notes/
│     ├─ fieldwork_log            # archive work log: dates, tasks
│     └─ sampling_log.md         # how texts were selected and teh corpus overview
│
├─ notebooks                      # exploratory notebooks
│  
│
├─ app/                          # future MagicTagger application
│  ├─ ui/
│  │  ├─ Home.py                 # Streamlit entry point
│  │  └─ __init__.py
│  ├─ api/
│  │  ├─ main.py                 # future API backend
│  │  └─ __init__.py
│  ├─ shared/
│  │  ├─ __init__.py
│  │  └─ config.py               # central config (paths to data, settings)
│  └─ requirements.txt           # dependencies for the app layer
```

---

## 5. How to Cite

If you use MagicTagger or the accompanying corpus, please cite:

*Vdovichenko, E. (2025). MagicTagger: Open Infrastructure for Computational Analysis of Russian Folktales (v1.0). Docker application and research corpus. Code: GNU AGPL-3.0; derived transcriptions and metadata: CC BY 4.0; underlying scans and archival data: subject to Estonian Folklore Archive policies.*