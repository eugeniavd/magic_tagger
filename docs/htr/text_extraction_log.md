## 1. Corpus index and handwriting registry

### Purpose

To support a fast but methodologically controlled HTR workflow under strict time constraints, we introduced a **golden_truth** table that acts as a single source of truth for:

1. **Traceability from tale-level IDs to image files/pages** (what exactly was recognized and where it came from).
2. **Stable grouping of pages by handwriting (“hand”)** for model evaluation and error analysis.
3. **Separation of roles**: collectors are not automatically assumed to be scribes; where attribution is not possible, we explicitly record uncertainty.
4. **Reproducibility**: all downstream steps (evaluation sampling, model comparison, text export for NLP, quality checks) reference stable identifiers rather than ad-hoc filenames.

---

### Table creation workflow

#### Step 0 — Scope decisions

We took texts from scanned notebooks from the archive database (https://kivike.kirmus.ee/), pages photographed as **spreads** (two facing pages in one image). For HTR evaluation and processing, a page-level unit is preferable (layout, line extraction, CER/WER computation), therefore each spread is represented as two page records (left/right).

When a page contains heavy marginalia, we allow the unit to be refined to a region (a clean block of lines), but this is used sparingly to maintain speed.

---

#### Step 1 — Define stable identifiers

We use stable IDs to keep file naming and processing consistent:

- **`tale_id`**: canonical identifier for the text unit.
- **`image_filename`**: identifier derived from the spread filename (e.g., `era_vene_07_170-171`).
- **`handwriting_id`**: corpus-wide identifier for a visually consistent hand, always neutral (`H001`, `H002`, …). It is never replaced by a collector name or ID.

This separation ensures that “hand” remains a controlled analytical variable even when collector information is incomplete or ambiguous.

---

#### Step 2 — Add core fields (schema)

The table contains three groups of fields.

##### A) File and pagination fields (traceability)

- `tale_id` — links the page to the tale record.
- `image_filename` — name of the scan.
- `page_side` — `L` / `R` (left or right page within the spread).
- `page_no` — the page number if known (e.g., `170` / `171`).
- `page_id` — the page id formulated as collection id united with volume number and page number (e.g. `era_vene_8_211`).


**Why:** these fields allow us to reconstruct exactly what was processed and to re-run HTR consistently.

##### B) Handwriting fields (HTR evaluation and grouping)

- `handwriting_id` — `H##` identifier assigned at corpus level.
- `handwriting_status` — `assigned | unknown`.
- `handwriting_confidence` — `high | medium | low`. - our confidence to assign the handwriting to one of collectors (if they worked in a group)

**Why:** these fields enable evaluation “by hand” (important for multi-hand corpora) and prevent misleading metrics when pages contain mixed writing.

##### C) Collector metadata and attribution fields (provenance and uncertainty)

- `collector_ids`.
- `collector_count` — quantity of collectors.

**Why:** we avoid the common methodological pitfall of equating “collector” with “scribe”. Where a page is known to be written by the collector (single-collector cases), we record a certain attribution; where multiple collectors exist, we keep attribution explicitly ambiguous.

##### D) Quality and inclusion fields (time-efficient triage)

- `quality_hint` — `good | ok | bad`.
- `major_issues` 
- `include_in_gt` — `yes | no` for evaluation ground truth selection.
- `gt_status` — `planned | in_progress | done`.

**Why:** these fields let us prioritize pages for evaluation and manual correction within a limited time budget.

---

#### Step 3 — Filling rules (fast protocol)

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

### Handling deletions and exclusions

#### Why we delete/exclude items

During corpus preparation we may remove items that do not match the project scope or that introduce avoidable noise into HTR evaluation (e.g., non-target language, illegible images, or exceptional one-off hands that are not representative for model training).

We record these decisions in a **`deleted_texts` log** to preserve transparency and reproducibility.

#### Deleted texts log 

Create a small table `deleted_texts` with:

- `tale_id`
- `reason_category` (controlled): `language_mismatch | non_target_genre | illegible | duplicate | rights | other`
- `reason_detail` (free text, one sentence)
- `decision_date`
- `decision_by`

#### Example: `era_vene_1_309_38`

- **Case:** `era_vene_1_309_38` is written in Estonian, and the associated collector appears only once in the entire corpus.
- **Decision rationale (two layers):**
  1. **Language mismatch:** the project targets Russian-language texts; Estonian content falls outside the objectives.
  2. **Singleton hand risk:** a one-off hand (unique collector, single occurrence) does not support meaningful evaluation “by hand” and adds variance without clear analytical benefit under time constraints.

---

## 2. Transkribus baseline evaluation

### Goal
Before investing time into HTR, we ran a baseline evaluation of Transkribus on our corpus to quantify how well the platform performs from the box across multiple handwriting types. The immediate objective was to 
- estimate expected transcription quality for downstream NLP
- identify which hands are “easy” vs “hard” for the baseline model.

### Data and evaluation design
- **Evaluation sample:** 20 pages total, representing **10 handwriting groups** (H01–H10).
- **Per-handwriting coverage:** 2 pages per handwriting group (≈ one notebook spread / document).
- **Document unit in Transkribus:** each document contains two pages written in the same handwriting (one spread scanned as two pages; both pages treated as belonging to one hand for evaluation).
- **No model training:** the goal was to test baseline quality, so we used Transkribus models without any fine-tuning on our material.

### Step 1 — Upload and document structure
1. Uploaded the evaluation sample pages to a dedicated Transkribus collection (`eval_sample`).
2. Created documents so that each document corresponds to one handwriting and contains two pages (a scanned spread split into two page images).

Evaluation set was stored as a Transkribus collection, with one document per notebook spread. For each document we retained two versions: the raw HTR output (hypothesis) and a manually corrected transcription (ground truth). 

**Rationale:** Keeping the document aligned with one handwriting avoids mixing hands in evaluation and makes per-handwriting analysis interpretable.

### Step 2 — Baseline layout analysis (no training)
We performed layout analysis using Transkribus default layout model ("Universal Lines"):
- Automatic detection of text regions and lines.
- Manual verification of region boundaries.

**Important adjustment (two-page spreads):**
- Since the source images are two-page spreads, in same cases layout recognition occasionally produced line baselines crossing the gutter and mixed left/right page reading order or produce 1 long line for all two pages. We enforced two separate text regions per spread and explicitly set reading order (left region first, right region second). In problematic cases, region and line detection was corrected manually.

### Step 3 — Baseline text recognition (no training)
We ran Handwritten Text Recognition using:
- **Russian Generic Handwriting 2** (Transkribus public model)

This produced an initial hypothesis transcription for each page/line.

### Step 4 — Create ground truth efficiently via correction
To minimize time spent on “from-scratch” transcription, we used the fastest GT strategy:
1. Took the model output as a starting point.
2. **Manually corrected** the transcription to a “good-enough” ground truth for evaluation:
   - corrected letters/words;
   - punctuation and capitalization;
3. Removed/excluded lines that belong to **non-target text** (e.g., marginal notes, unrelated fragments on the spread, or content outside the target tale text).

**Outcome:** a corrected ground truth version per document suitable for computing error rates.

### Step 5 — Compute metrics in Transkribus per document
For each document (2 pages; single handwriting), we used Transkribus’ built-in evaluation to compute:
- **CER (Character Error Rate)**  
  Share of character-level edits (insertions, deletions, substitutions) required to transform the hypothesis into the ground truth.
- **WER (Word Error Rate)**  
  Share of word-level edits required to transform the hypothesis into the ground truth.

We computed metrics **per document**, then transferred the values into our evaluation tables.

### Step 6 — Aggregate results across the full sample (20 pages, 10 hands)
We computed summary statistics across the evaluation set:
- **Mean CER** over all evaluated documents/pages (sample-level baseline)
- **Mean WER** over all evaluated documents/pages
- Additionally, we tracked the **median** as a robust indicator (less sensitive to extreme failures).

These aggregates provide the overall “baseline expectation” of Transkribus performance on our material without training.

### Step 7 — Per-handwriting breakdown and qualitative interpretation
We then grouped the results by `handwriting_id` and calculated:
- per-hand mean/median **CER** and **WER** (based on the two pages in the sample)
- distribution-oriented indicators to support decision-making:
  - share of pages/lines with **CER ≤ 25** (interpretable as “usable / relatively clean”)
  - share of pages/lines with **CER ≥ 50** (interpretable as “very noisy / high risk for NLP”)

This allowed us to identify:
- **hands recognized well** by the generic Russian model (low CER/WER)
- **hands recognized poorly** (high CER/WER, often requiring either fine-tuning or heavier post-correction)

### Findings 
- Baseline recognition quality is handwriting-dependent: some hands achieve substantially better CER/WER than others.
- Two “mid-band” outcomes are common: pages with **CER ~30–35** tend to yield **WER ~0.47–0.56**, meaning that roughly half of the words contain at least one error. This level is often still usable for document-level NLP (e.g., char-ngrams, coarse topic signals), but weak for tasks requiring accurate tokens (e.g., NER) without normalization.
- The per-handwriting breakdown is therefore essential for planning:
  - which portions of the corpus can be processed “as-is” (with light cleaning),
  - which hands require either model adaptation (fine-tuning) or selective manual correction.

---

## 3. Transformer model baseline evaluation

### Normalization rules 
To ensure comparability and to avoid counting purely typographic artifacts as HTR errors, we apply a minimal, explicit normalization:
1. `strip()` leading/trailing whitespace.
2. Convert any internal whitespace runs to a single space: `\s+ → " "`.
3. Preserve all other symbols as-is, including:
   - Cyrillic letters (with diacritics if present),
   - punctuation marks,
   - capitalization,
   - digits.

No spelling modernization, lemmatization, or dictionary correction is applied for metric computation.

### Metrics
We compute:
- **CER (Character Error Rate)**: Levenshtein edit distance at the character level, divided by the number of characters in GT.
- **WER (Word Error Rate)**: Levenshtein edit distance at the token level (tokens defined by whitespace after normalization), divided by the number of GT tokens.

### Aggregation (reporting)
- Report per-spread **CER and WER**.
- Report sample-level aggregates for the evaluation set:
  - **mean CER/WER** across spreads,
  - **median CER/WER** across spreads,
  - per-handwriting summaries (mean/median, plus share of “good” vs. “bad” pages if used in the project dashboard).


## Transformer HTR Baseline Evaluation ("trocr-base-handwritten-ru")

We evaluated a **TrOCR** on the same held-out batch used for the Transkribus baseline and computed the same page-level and handwriting-level metrics (CER/WER) to enable a direct comparison.

### Results summary
TrOCR achieves a **mean CER only moderately worse** than Transkribus, but it is **not competitive at word level**: at the handwriting level, TrOCR remains in a systematic failure regime with **≈70–95% WER** across hands, indicating that the current configuration does not produce usable word sequences without additional adaptation (most plausibly due to spacing/tokenization errors). In contrast, **Transkribus is the stronger baseline overall**, with better mean CER and **overwhelmingly better WER**, and it **wins on more pages** in the per-page delta analysis. TrOCR nevertheless appears **useful as a fallback** for a subset of difficult pages where Transkribus degrades severely, delivering **large CER improvements** in those cases.

### Method selection for the corpus
For corpus-scale HTR we choose the approach that minimizes total downstream cost:

\[
\textbf{Score} = \textbf{CER} + \lambda\cdot\Big(\frac{\text{minutes\_to\_correct}}{100\ \text{lines}}\Big) + \mu\cdot \textbf{failure\_rate} + \nu\cdot \textbf{pipeline\_overhead}.
\]

Under this criterion, **Transkribus is selected as the primary HTR engine**, because its much lower WER implies substantially lower correction time and a lower effective failure rate. **TrOCR is retained as an auxiliary fallback** for pages/hands where Transkribus exhibits high CER, since in those edge cases it can reduce character-level error enough to justify the extra pipeline overhead.