# Tale Type Processing and Quality Control

This section documents the end-to-end workflow we applied to tale type annotations in the corpus, from manual scope cleaning to automated validation and the generation of a lightweight hierarchical resource for downstream analysis.

The overall goal was to ensure that type data are **methodologically consistent** with our research scope (magic tales), **internally coherent** for computational modelling and evaluation, and **transparent and reproducible**, with provenance for all manual harmonization decisions.

---

## 1. Scope Cleaning: Removing Non-Magic Tales

### Rationale
Our project focuses on **tales of magic** (ATU 300–749). Some records in the initial selection were either:
- clearly outside the target genre (e.g., animal tales, realistic tales, religious legends), or
- labelled with codes that are not part of the ATU magic-tale interval
- not labeled.

Including such texts would introduce systematic noise into both evaluation and training, because the model would be asked to learn a label space that contradicts the defined scope.

### Action
We manually removed the following text with were assigned with "non-magic" types:

- `era_vene_1_517_1` — **SUS *296**, animal tales  
- `era_vene_15_465_5` — **954**, realistic tales  
- `era_vene_16_559_12` — **SUS 218B***, not in ATU scope  
- `era_vene_13_30_4` — **ATU 780**, religious tales

These removals are documented explicitly to keep the methodological record transparent and to ensure the dataset can be reconstructed or audited.

---

## 2. Index Enrichment: Tracking Mapping and Label Status

### Rationale
The archive-level metadata sometimes provides tale types in different national type systems (e.g., EE, SUS) or uses local extensions that do not correspond one-to-one to ATU. Since our modelling and evaluation are defined in ATU terms, we needed a controlled way to:
- preserve source evidence (local type labels), and
- record the mapping decisions that produce the final ATU labels used as gold data.

### New Index Columns
We introduced explicit columns to capture mapping provenance and evaluation readiness:

#### `local_type` 
transfered value from `type_code_*` if there is any local scheme (EE, SUS)

#### `local_type_scheme`  
- EE (Estonian tale types)
- SUS (East Slavic Fairy Tales Cataloge)

#### `mapping_status` (enum)
- `not_needed_native_atu` — the `type_code_*` is already in ATU form; we only confirmed/transferred it  
- `mapped_from_local` — the one of the `type_code_*` is in a local scheme (e.g., EE/SUS); we manually assigned ATU codes in `local_type`  
- `missing` — neither a local type nor ATU codes are provided

#### `mapping_relation` (enum)
A controlled descriptor of the relationship between the local type and the chosen ATU target:
- `exact` — full equivalence
- `close` — strong similarity 
- `broad` — mapping only at a higher (less specific) level
- `none` — no mapping possible or not attempted

#### `gold_status` (enum; evaluation/training readiness)
- `ok` — at least one valid ATU code is present in `type_code_*`  
- `missing` — all `type_code_*` fields are empty

These fields make it possible to maintain a single, unified corpus index while still producing reproducible training/evaluation splits via filtering rules.

---

## 3. Manual Harmonization: Mapping Local Types to ATU

### Rationale
For computational classification, the label space must be consistent. We therefore harmonized local type labels to ATU while preserving the local type in a dedicated field. This enables:
- ATU-based modelling and evaluation,
- continued archival fidelity (local types remain accessible for folklorists), and
- future comparative work across typological systems.

### Principle

- `type_code_1 … type_code_4` store the **final ATU types codes**, ordered by appearance in the narrative (supporting multi-type/contamination cases and narrative-structure analysis).
- `local_type` remains the **label outside ATU Classification** (local variants - EE/SUS). In some cases archive provided only local types without assigning ATU type. But we need to use one system for text classification, so we made type mapping (11 cases in the corpus).
- Each manual mapping is annotated via `mapping_status` and `mapping_relation`.

### Documented mapping examples
The following cases illustrate typical harmonization decisions:

- `era_vene_15_433_1`: **EE 650E*** → **ATU 650A**; also aligns with **SUS 650В*** (local model context)  
- `rkm_vene_3_257_117`: **EE 328C*** → **ATU 328**  
- `tru_vkk_5_58_29`,`tru_vkk_48_62_110`, `era_vene_12_501_1`, `era_vene_12_97_19` and `era_vene_13_15_1`: **SUS 480** → **ATU 480D***  
- `era_vene_7_89_1`: **EE 480E*** → **ATU 480**  
- `era_vene_8_223_147`: **SUS 735A**** → **ATU 735A** 
- `era_vene_13_175_18` and `tru_vkk_29_54_68`: **SUS 707B*** → **ATU 707**

These mappings are not treated as silent transformations: they are part of the dataset provenance and are explicitly traceable.

---

## 4. ATU Parser Validation and Exclusion List

### Rationale
After manual harmonization, we conducted a dataset-level quality-control pass to ensure that:
1) all type codes are in an admissible, machine-parseable format, and  
2) each record includes at least one code within the project scope (**ATU 300–749**).

Importantly, our parser supports:
- base types (`300`)
- lettered subtypes (`510A`, `510B`)
- asterisk refinements (`300A*`, `327*`)
and treats the asterisk `*` as a meaningful typological marker, not as noise.

### Result
The automated validation identified **15 texts** with no ATU code present in any of the dedicated type fields (`type_code_1 … type_code_4`). These records were already known as cases where archive folklorists had not assigned a type.

### Policy Decision
We intentionally did not remove these 15 texts from the corpus. Instead, we retain them as:

1) **Unlabeled candidates** for future annotation or semi-supervised training, and  
2) A **held-out set for expert-facing evaluation** of the application.

In the final stage of the project, the application’s predicted type suggestions for these texts will be presented to domain folklorists for assessment. This allows us to evaluate practical plausibility and usefulness beyond the subset with gold ATU labels.

The full parser output and the exclusion list are stored as project artifacts (e.g., `ambiguous_excluded.csv` and an enriched index file with evaluation flags).

---

## 5. Observed ATU Hierarchy: `atu_hierarchy.csv`

### Rationale
Our gold labels include structured variants (`300`, `300A`, `300A*`) that reflect the **typological hierarchy** of ATU numbering. Encoding this structure explicitly has three benefits:

- **Reproducibility:** our interpretation of letters and `*` is documented as data rather than remaining implicit in code.  
- **Evaluation diagnostics:** it becomes possible to distinguish “within-family” confusions (e.g., `300A*` vs `300A`) from cross-family errors (e.g., `300A*` vs `510A`).  
- **UI interpretability:** the application can present suggestions as a breadcrumb path (`300 → 300A → 300A*`), aligning with folklorists’ reasoning about subtypes.

### Construction principles
The table is generated automatically from the **observed label inventory** in `type_code_1 … type_code_4` (not from the entire ATU catalogue). This observed-only approach keeps the workflow fast and guarantees alignment with the label space used in modelling.

Deterministic hierarchy rules:
- Base type `NNN`: `parent=""`, `level=0`
- Lettered subtype `NNN[A-Z]+`: `parent=NNN`, `level=1`
- Asterisk refinement `NNN[A-Z]+*`: `parent=NNN[A-Z]+`, `level=2`
- Edge case `NNN*`: `parent=NNN`, `level=1`

If an observed node implies a parent that is not explicitly present (e.g., `300A*` observed but `300A` absent), the missing parent node is added with `observed_count=0` to ensure the hierarchy is traversable.

### Fields (summary)
- `scheme`: typology identifier (`ATU`)
- `type`: canonical label identifier (e.g., `300A*`)
- `base`: numeric root (`300`)
- `letters`: subtype suffix (`A`, `B`, …)
- `has_star`: presence of `*` as refinement marker
- `parent`: parent node identifier
- `level`: depth in the hierarchy
- `observed_count`: frequency of the label in corpus annotations

---

## 6. Reference Resources Used for Typology and Cross-System Checks

We relied on the following publicly accessible reference materials for interpreting and aligning type systems:

- ATU overview and references:  
  https://edition.fi/kalevalaseura/catalog/view/763/715/2750-1

- SUS type index:  
  https://www.ruthenia.ru/folklore/sus/index.htm

- EE type index (Estonian tale types):  
  https://www.folklore.ee/muinasjutt/tyybid/#_IMEMUINASJUTUD

- Mapping-oriented reference (ATU ↔ SUS guidance):  
  https://libraryguides.missouri.edu/c.php?g=1083510&p=7901911

---

## Outputs and Current Status (Summary)

- Non-magic items were removed to enforce the ATU 300–749 scope.
- The corpus index was extended with explicit mapping and evaluation status fields.
- Local type labels were manually harmonized to ATU while preserving local evidence.
- Automated parsing validated formatting and scope and identified **15 unlabeled texts** (no ATU codes in `type_code_*`).
- These 15 texts are retained for future expert-facing assessment of model suggestions.
- An observed-only ATU hierarchy (`atu_hierarchy.csv`) was generated to support evaluation diagnostics and UI presentation.
