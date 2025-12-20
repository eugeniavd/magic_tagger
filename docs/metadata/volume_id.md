# VolumeID scheme

## Purpose
This document defines **VolumeID**: a stable identifier for a collection volume used in the project.

VolumeID is required for:
- corpus-wide referencing of volumes across datasets;
- provenance and linking (catalog ↔ scans ↔ transcriptions ↔ extracted tales);
- group-based evaluation (e.g., group k-fold cross-validation), where all tales from the same volume must remain in the same fold.

## Definitions

### Volume
A **Volume** is a single archival unit (physical folder with manuscripts) within a series (e.g., “ERA, Vene”). All texts (tales) extracted from the same volume are considered not independent for evaluation purposes.

All tales extracted from the same archival volume typically share multiple dependencies: the same collector(s), narrator(s), recording session(s), editorial conventions, and often the same physical document context. If we let tales from one volume appear in both train and test, the model can exploit these shared signals and we will get an over-optimistic evaluation (a form of leakage). Using volume_id as a grouping key prevents that: the test fold contains volumes the model has not “seen” during training.

### Text
A **Text** (tale record) is an extracted narrative item with its own TextID.

## Canonical identifiers

### Tale_id (source)
In the corpus index, each tale has a `tale_id` in the following format:

`<collection>_<volume_no>_<item_no>_<page_no>`

Example:
- `era_vene_7_227_1`

Where:
- `<collection>`: series code (e.g., `era_vene`)
- `<volume_no>`: numeric volume number within the series (e.g., `7`)
- `<item_no>`: internal item/page/bundle number in extraction pipeline (e.g., `227`)
- `<pageN_no>`: disambiguation number for multiple variants of the same extracted item (e.g., `1`)

**Important:** only the first three segments identify the volume (collection and volume number).

### Volume_id (derived)
**Volume_id is derived from tale_id** as the two underscore-separated segments:

`VolumeID = <collection>_<volumeNo>`

Example:
- `tale_id:  era_vene_7_227_1`
- `volume_id: era_vene_7`

This rule guarantees that every tale extracted from the same archival volume shares the same volume_id.

## Generation rules

### Rule 1 — Derivation (mandatory)
For each record in `corpus_a_index.csv`, derive volume_id from tale_id:

1) Split `tale_id` by `_`  
2) Take segments 1–3  (collection name consists of 2 segments)
3) Join them back with `_`  
4) Normalize to lowercase

Pseudocode:
- `volume_id_ = "_".join(tale_id.lower().split("_")[0:3])`

### Rule 2 — Required field
`volume_id` is a required (non-null) field in the corpus index. Records without a valid volume_id_ are not eligible for evaluation splits until fixed.

### Rule 3 — Format constraints (validation)
A valid volume_id_ MUST:
- be ASCII lowercase
- contain no spaces
- follow the pattern:

`^[a-z]+_[a-z]+_\d+$`

Examples of valid:
- `era_vene_7`
- `era_vene_12`

Examples of invalid:
- `ERA_Vene_7` (not normalized)
- `era_vene_07a` (non-numeric volume number)
- `era-vene-7` (wrong separator)
- `era_vene` (missing volume number)

### Rule 4 — Stability policy
- volume_id is treated as a stable identifier.  
- Do not reuse volume_id for another volume.
- If an error in assignment is discovered, fix the underlying tale_id/metadata and regenerate volume_id deterministically (do not hand-edit volume_id in a way that breaks the derivation rule).

## Examples

### Example A — single record
- `tale_id`: `era_vene_7_227_1`  
- `volume_id`: `era_vene_7`

### Example B — multiple texts in the same volume
- `era_vene_7_001_1` → `era_vene_7`
- `era_vene_7_227_1` → `era_vene_7`
- `era_vene_7_305_2` → `era_vene_7`

All three belong to the same archival volume and must be grouped together during evaluation.

### Example C — different volumes
- `era_vene_7_227_1`  → `era_vene_7`
- `era_vene_8_010_1`  → `era_vene_8`
- `era_vene_12_099_1` → `era_vene_12`

## Edge cases and handling

### Edge case 1 — unexpected TextID structure
If `tale_id` does not contain at least 3 underscore-separated segments, volume_id cannot be derived.
Action:
- mark the record as invalid for evaluation;
- correct tale_id to match the canonical pattern.

### Edge case 2 — volume number normalization
Volume numbers are stored as integers in tale_id (e.g., `7`, not `007`).  
If a later stage requires zero-padding for file sorting, this should be implemented as a display, not by changing the canonical volume_id.