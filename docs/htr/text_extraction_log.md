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


## 4. HTR/OCR Quality Assessment and Data Readiness Protocol

This section documents how we assessed HTR quality in Transkribus, identified systematic failure modes, and defined a pragmatic data-readiness policy for downstream NLP (ATU classification, statistics, and evidence snippets).

---

### 1. Reference evaluation subset (Ground Truth) and quantitative metrics

#### 1.1 Purpose
Because training a dedicated HTR model was out of scope for the current time window, we first evaluated the baseline Transkribus recognition output on a small reference subset to:

- quantify the recognition quality (CER/WER),
- detect systematic error patterns,
- decide whether the corpus is ready for downstream NLP tasks without additional HTR training.

#### 1.2 Ground Truth creation and evaluation setup
We selected **14 pages** as a validation/reference subset and produced **Ground Truth (GT)** transcriptions for them. The pages were chosen to represent both typical and challenging cases, including pages flagged by Transkribus layout recognition as **hard**.

For each GT page, we computed:
- **CER (Character Error Rate)**
- **WER (Word Error Rate)**

**Overall (N=14):**
- CER: **mean 18.70**, median 10.69
- WER: **mean 0.366**, median 0.316

**By layout stratum:**
- `layout_recognition = good` (N=9):
  - CER: **mean 7.70**, median 8.43
  - WER: **mean 0.221**, median 0.279
- `layout_recognition = hard` (N=5):
  - CER: **mean 38.67**, median 20.89
  - WER: **mean 0.720**, median 0.859

These metrics provide an objective estimate of text recognition quality on the reference subset.

#### 1.3 Observed metrics (reference subset)
On the evaluated pages, recognition quality varied substantially. Pages with `layout_recognition = good` tended to have usable CER/WER, whereas pages with `layout_recognition = hard` showed markedly worse performance and, in several cases, a failure regime.

**Key observation:** the strongest degradation in CER/WER aligned with **hard layout cases**.

#### 1.4 Interpretation: layout-driven failure mode
The reference evaluation showed that when a page has a **complex layout** (e.g., challenging spreads, ambiguous separation, visually dense writing), the baseline HTR model may fail even after manual corrections of:
- text regions,
- line segmentation (baselines),
- removal of non-relevant areas.

In other words, for a subset of hard pages, the limiting factor is not only segmentation but the mismatch between the page/handwriting characteristics and the generic model capacity.

---

### 2. Decision and scope: how we handle hard pages

#### 2.1 Immediate implication
Based on the reference evaluation, pages with **hard layout** are currently **not reliable** for downstream NLP tasks (ATU classification, evidence extraction, frequency statistics) when processed with the baseline model.

Such pages would require one of the following interventions:
- **manual text correction**, or
- **HTR model training / fine-tuning** and re-recognition.

#### 2.2 Project decision
Given the project time constraints, we **defer** manual correction and/or model training for these pages to later stages.

For the current iteration, we mark pages with hard layout as **not yet suitable for analysis** and exclude them from downstream experiments by default.

This is recorded via a page-level readiness flag (conceptually: `htr_usable = FALSE` and/or `exclude_reason = low_text_quality`).

---

### 3. Corpus-wide visual audit (510 pages) and readiness labeling

#### 3.1 Motivation
A GT-based evaluation provides precise metrics but is necessarily limited in size. To ensure robust downstream processing under time constraints, we performed a **corpus-wide visual audit**.

#### 3.2 Procedure
We visually inspected **all 510 pages** in Transkribus and assigned a readiness label based on whether the recognized text is usable for computational analysis.

For each page we recorded a binary usability assessment of `htr_usable`:
- **True**: text is sufficiently readable and structurally coherent for downstream NLP,
- **False**: text is visually too noisy or structurally unreliable for downstream NLP.

This labeling complements the GT evaluation by capturing practical usability across the entire corpus.

- Total pages audited: **510**
- Pages flagged as *not usable for downstream NLP at the current stage* (`htr_usable = FALSE`): **137** (**26.9%**)
- Pages considered usable (`htr_usable = TRUE`): **372** (**73.1%**)

Most excluded pages belong to the **hard-layout** stratum and were marked with `exclude_reason = low_text_quality`. These pages are retained in the corpus but excluded from ATU classification, evidence extraction (anchors), and text-derived corpus statistics until a future HTR improvement step (manual correction and/or model training) is completed.


#### 3.3 Operational policy
For the current pipeline iteration, we proceed with downstream tasks **only on pages marked as "True"**.

Pages marked as not usable are retained in the corpus but excluded from:
- ATU classifier training and evaluation,
- evidence snippet extraction (anchors),
- corpus statistics that rely on textual content.

They remain eligible for future processing once an improved HTR strategy is implemented.


---

