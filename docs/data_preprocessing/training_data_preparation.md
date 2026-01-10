# Training Dataset Preparation for ATU Classification (HTR + Transcriptions)

This document describes how we assembled the training dataset for **automatic ATU type classification** from a mixed source collection: (1) tales with **HTR outputs** from scanned pages and (2) tales available **only as transcriptions**. The goal was to produce a **single, reproducible, LOD-ready table** with stable IDs, ATU labels (including multi-label cases), text content, provenance, and lightweight quality indicators.

---

## 1. Inputs

### 1.1 Corpus Index (tale-level)
We started from the project corpus index spreadsheet (`corpus_b_v1_20251230.xlsx`) containing one row per tale with:
- stable identifier: `tale_id`
- ATU labels encoded across `type_code_*` fields (multi-label possible)
- mapping provenance: `mapping_status`, `mapping_relation`, `gold_status`, `type_count`
- access/provenance fields used for documentation and downstream LOD export (e.g., `rights_status`, `set`, `sampling_version`, `local_type_scheme`, `local_type`, `content_description`)

### 1.2 Recognition Quality Log (page-level)
We used a page-level table reporting HTR quality and usability, including:
- identifiers: `tale_id`, `page_id`, `image_filename`, `page_no`, `page_side`
- usability flags: `htr_usable`, `exclude_reason`, `major_issues`

### 1.3 Text Sources
We integrated text from two sources:
1. **HTR text exports (TXT):** 
2. **TEI/XML transcriptions:** 

---

## 2. Corpus Scope and Selection Rationale

### 2.1 Initial scope
At the start of the workflow, the working corpus consisted of **61 tales**.

### 2.2 Reduced scope for the current training set
For the first end-to-end prototype we reduced the corpus to **50 tales**. The excluded items were removed because of **technical constraints in text extraction**:

- a subset of tales exhibited **complex page layout** (e.g., irregular segmentation, marginalia density, mixed structures) that caused the current HTR pipeline to perform poorly;
- these cases produced **low-quality recognition output** (insufficient for reliable feature extraction and classification at this stage);
- rather than forcing noisy data into the baseline model, we **postponed these tales for a future iteration**, where we plan targeted layout handling and/or improved transcription strategy.

This decision prioritizes a reproducible baseline on usable data, while keeping a clear backlog of difficult cases for later methodological improvements.

---

## 3. Workflow Overview

### 3.1 Load and normalize tables
All input tables were loaded into pandas and column names were normalized (e.g., trimming trailing spaces) to prevent accidental duplication during merges.

### 3.2 Filter the recognition log to “usable” pages
We filtered the page-level recognition log to retain only pages considered usable for downstream modelling. The filtering relied on the project’s existing usability decisions (e.g., `htr_usable` and quality hints), rather than introducing additional heuristic thresholds at this step.

**Outcome:** a filtered page-level dataframe representing pages that are acceptable HTR input.

### 3.3 Select “well-recognized” tales and match with the corpus index
From the filtered pages, we derived the set of **tale_ids that have at least one usable page** and merged this set with the **tale-level corpus index** to attach:
- ATU label lists (multi-label)
- mapping provenance fields (`mapping_status`, `mapping_relation`, `gold_status`, `type_count`)
- rights/provenance fields (`rights_status`, `set`, `sampling_version`, etc.)

This merge produced the initial **HTR-based training subset**, where each tale is represented by:
- stable `tale_id`
- ATU labels
- metadata/provenance

### 3.4 Attach HTR text exports (TXT)

We added:
- `text_raw` — raw HTR/OCR text
- `txt_path` — filesystem path to the corresponding TXT file

### 3.5 Include transcript-only tales (no scans)
Some tales are marked as `digital_carrier = transcript_only` in the index. These items were not expected to appear in the recognition log (no scanned pages). We:
1. filtered these rows from the index
2. selected the same project-wide set of columns (`keep_cols`) to keep the schema consistent
3. appended them to the working dataset so that the final training dataset covers both HTR-based and transcript-only items

### 3.6 Fill missing texts using TEI/XML transcriptions
For rows where `text_raw` was empty or missing, we attempted to recover the text from TEI/XML transcription files.

We implemented a lightweight TEI text extraction procedure:
- prioritizes `<body>` as the container (to avoid header/metadata)
- extracts textual content while discarding markup tags
- preserves structural breaks:
  - `<lb/>` → newline
  - `<pb/>` → blank line

### 3.7 Consolidate and deduplicate
We concatenated the HTR-based subset and transcript-only subset into a single dataset:
- ensuring consistent column schema (`keep_cols`)
- deduplicating by `tale_id`
- checking for missing texts and missing labels as final sanity controls

---

## 4. Data Quality Check (text-level)

To document the quality of the assembled textual input (noisy HTR + transcriptions), we computed lightweight corpus-level quality features per tale:
- `n_tokens` — token count (whitespace-based)
- `cyr_ratio` — share of Cyrillic characters (proxy for script consistency)
- `garbage_ratio` — share of non-allowed characters (proxy for OCR/HTR noise)

We produced summary statistics and diagnostic plots, saved to:
`notebooks/figures/`
including:
- histograms for `n_tokens`, `cyr_ratio`, and `garbage_ratio`
- scatter plot: noise vs length

The corpus is heterogeneous in length (most tales are short-to-medium, with a long tail of very long narratives), while script consistency is stable across items. The garbage ratio is low overall, indicating that the HTR/transcription outputs are structurally suitable for n-gram based baselines without full manual correction. A scatter analysis suggests higher variance of the noise proxy in shorter texts, motivating a conservative needs-review policy for very short and/or noisy items. 

---

## 5. Text Normalization

To reduce the impact of heterogeneous transcription sources (HTR exports and TEI/XML-derived transcriptions) and to make the feature extraction step reproducible, we applied a lightweight, corpus-wide **rule-based normalization** to both the full tale texts (`text_raw → text_norm`) and the short catalog summaries (`content_description → summary_norm`). The normalization is intentionally conservative: it does not attempt spelling correction or linguistic lemmatization, but removes systematic technical artifacts and enforces consistent surface forms, which is particularly important for TF–IDF n-gram models.

### Normalization steps

1. **Unicode canonicalization (NFKC).**  
   All strings are normalized using Unicode NFKC to collapse visually similar codepoints into a consistent representation and to reduce variance introduced by different export pipelines.

2. **Line ending normalization.**  
   Windows and legacy line endings are converted to Unix newlines to ensure consistent downstream processing.

3. **Removal of systematic “noise lines”.**  
   Lines that match typical page markers or standalone line numbers are removed (e.g., `Page 12`, `стр. 12`, bare `01`, `12.`). These tokens are not part of the narrative content and may otherwise become high-frequency artifacts in n-gram features.

4. **Removal of recurrent garbage characters.**  
   A small, explicit blacklist removes symbols observed as systematic OCR/HTR artifacts (e.g., `|`, `¬`, and similar non-linguistic markers). This reduces spurious n-grams and improves model robustness.

5. **De-hyphenation across line breaks.**  
   Hyphenation artifacts are resolved with a single rule applied across the entire corpus: `-\n → ""` (including dash variants). This reconstructs split words (e.g., `сказ-\nка → сказка`) and prevents fragmentation of character n-grams.

6. **Newline collapse.**  
   Remaining newlines (mostly layout-driven rather than content-driven) are converted to spaces, producing a single continuous text per tale suitable for document-level vectorization.

7. **Lowercasing and `ё → е` unification.**  
   Text is lowercased and the Cyrillic letter `ё` is systematically mapped to `е`. This reduces sparsity and avoids treating orthographic variants as distinct tokens.

8. **Dash normalization.**  
   All dash variants are unified to a single long dash (`—`), and dashes between alphanumeric characters are interpreted as intra-word hyphens and mapped to `-`. This provides consistent segmentation while preserving compound forms when relevant.

9. **Whitespace and punctuation spacing.**  
   Multiple spaces are collapsed, spaces before punctuation are removed, and a single space after punctuation is enforced when followed by a non-space character. This improves token boundary stability without heavy linguistic preprocessing.

10. **Bracket character removal (square brackets).**  
   Square brackets are removed while keeping their content (e.g., `[царевна-лягушка] → царевна-лягушка`). This handles catalog/editorial conventions without discarding potentially informative lexical material.

### Rationale for this approach

This normalization strategy targets **systematic, non-linguistic variance** introduced by digitization and transcription workflows (layout, line numbering, encoding differences, hyphenation). For small datasets, TF–IDF models are particularly sensitive to such artifacts because they can inflate feature weights and distort similarity. By applying a uniform, documented set of rules, we improve **reproducibility, comparability across sources**, and **robustness to HTR noise**, while preserving the original lexical signal needed for ATU type prediction.

---

## 6. Notes and Limitations

- The corpus includes **noisy HTR/OCR text**; no full manual correction was performed due to time constraints.
- Multi-label ATU cases are preserved in the label representation to reflect real cataloguing practice.
- TEI/XML extraction is intentionally lightweight (plain-text output) and is used only to fill missing text fields; it does not attempt to preserve full diplomatic markup.
- A subset of tales from the initial pool (61) was temporarily excluded from the current training set (50) due to **complex layout and poor recognition output**; these items are kept for a future iteration with improved layout handling.
- The dataset and the filtering decisions are designed to be **reproducible** and **auditable**, consistent with DH/LOD expectations (stable IDs, provenance, explicit selection criteria).
