## Corpus index and handwriting registry

### Purpose

To support a fast but methodologically controlled HTR workflow under strict time constraints, we introduced a **golden_truth** table that acts as a single source of truth for:

1. **Traceability from tale-level IDs to image files/pages** (what exactly was recognized and where it came from).
2. **Stable grouping of pages by handwriting (“hand”)** for model evaluation and error analysis.
3. **Separation of roles**: collectors are not automatically assumed to be scribes; where attribution is not possible, we explicitly record uncertainty.
4. **Reproducibility**: all downstream steps (evaluation sampling, model comparison, text export for NLP, quality checks) reference stable identifiers rather than ad-hoc filenames.

---

## Table creation workflow

### Step 0 — Scope decisions

We took texts from scanned notebooks from the archive database (https://kivike.kirmus.ee/), pages photographed as **spreads** (two facing pages in one image). For HTR evaluation and processing, a page-level unit is preferable (layout, line extraction, CER/WER computation), therefore each spread is represented as two page records (left/right).

When a page contains heavy marginalia, we allow the unit to be refined to a region (a clean block of lines), but this is used sparingly to maintain speed.

---

### Step 1 — Define stable identifiers

We use stable IDs to keep file naming and processing consistent:

- **`tale_id`**: canonical identifier for the text unit.
- **`image_filename`**: identifier derived from the spread filename (e.g., `era_vene_07_170-171`).
- **`handwriting_id`**: corpus-wide identifier for a visually consistent hand, always neutral (`H001`, `H002`, …). It is never replaced by a collector name or ID.

This separation ensures that “hand” remains a controlled analytical variable even when collector information is incomplete or ambiguous.

---

### Step 2 — Add core fields (schema)

The table contains three groups of fields.

#### A) File and pagination fields (traceability)

- `tale_id` — links the page to the tale record.
- `image_filename` — name of the scan.
- `page_side` — `L` / `R` (left or right page within the spread).
- `page_no` — the page number if known (e.g., `170` / `171`).

**Why:** these fields allow us to reconstruct exactly what was processed and to re-run HTR consistently.

#### B) Handwriting fields (HTR evaluation and grouping)

- `handwriting_id` — `H##` identifier assigned at corpus level.
- `handwriting_status` — `assigned | unknown`.
- `handwriting_confidence` — `high | medium | low`. - our confidence to assign the handwriting to one of collectors (if they worked in a group)

**Why:** these fields enable evaluation “by hand” (important for multi-hand corpora) and prevent misleading metrics when pages contain mixed writing.

#### C) Collector metadata and attribution fields (provenance and uncertainty)

- `collector_ids`.
- `collector_count` — quantity of collectors.

**Why:** we avoid the common methodological pitfall of equating “collector” with “scribe”. Where a page is known to be written by the collector (single-collector cases), we record a certain attribution; where multiple collectors exist, we keep attribution explicitly ambiguous.

#### D) Quality and inclusion fields (time-efficient triage)

- `quality_hint` — `good | ok | bad`.
- `major_issues` 
- `include_in_gt` — `yes | no` for evaluation ground truth selection.
- `gt_status` — `planned | in_progress | done`.

**Why:** these fields let us prioritize pages for evaluation and manual correction within a limited time budget.

---

### Step 3 — Filling rules (fast protocol)

To minimize overhead, we follow a strict protocol:

1. **Create two rows per spread** (`page_side=L` and `page_side=R`).
2. Assign `handwriting_id`:
   - If the hand matches an existing `H###`, reuse it.
   - Otherwise, create a new `H###` and record representative examples in a separate `handwriting_registry` sheet (optional but recommended for consistency).
3. Record collectors:
   - Always fill `collector_ids` and `collector_count`.
4. Set quality triage and GT inclusion:
   - Prefer `good/ok` pages for evaluation.
   - Avoid `bad` pages in GT unless used as a separate “stress test” subset.

---

## Handling deletions and exclusions

### Why we delete/exclude items

During corpus preparation we may remove items that do not match the project scope or that introduce avoidable noise into HTR evaluation (e.g., non-target language, illegible images, or exceptional one-off hands that are not representative for model training).

We record these decisions in a **`deleted_texts` log** to preserve transparency and reproducibility.

### Deleted texts log 

Create a small table `deleted_texts` with:

- `tale_id`
- `reason_category` (controlled): `language_mismatch | non_target_genre | illegible | duplicate | rights | other`
- `reason_detail` (free text, one sentence)
- `decision_date`
- `decision_by`

### Example: `era_vene_1_309_38`

- **Case:** `era_vene_1_309_38` is written in Estonian, and the associated collector appears only once in the entire corpus.
- **Decision rationale (two layers):**
  1. **Language mismatch:** the project targets Russian-language texts; Estonian content falls outside the objectives.
  2. **Singleton hand risk:** a one-off hand (unique collector, single occurrence) does not support meaningful evaluation “by hand” and adds variance without clear analytical benefit under time constraints.