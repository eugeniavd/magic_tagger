# Corpus sampling 

## 1. Sampling rules 

To ensure timely delivery (especcialy text extraction) while preserving analytical value, we constructed a **Selected Corpus B** using a two-part sampling design that balances comparability (within-type variation) and thematic coverage (breadth across rare types).

1. **Core set (comparability-first).** We included *ll texts whose tale type (`type_code_1`) occurs at least twice in the corpus. This guarantees that each retained type supports **intra-type comparison** (variants), which is essential for evaluating the pipeline and demonstrating type-based exploration in the application.

2. **Coverage set (diversity slice).** From the remaining texts that belong to singleton types we added a random 15% sample (fixed seed) to maintain thematic breadth and reduce bias toward only frequent types.

The resulting selection is stored as a **versioned sampling Corpus B** (exported to Excel) that records all metadate from the first corpus A and additional metadata, its type frequency, and membership in the *core* or *coverage* subset. This design keeps the workflow feasible (HTR, metric computation, and application integration) while preserving a principled basis for later expansion (adding more texts without changing the schema or sampling logic).

----

## 2. Sampling outcomes (Selected Corpus B)

The sampling procedure produced a compact, analysis-ready subset while preserving variant comparability:

- **Selected texts:** 61  
  - **Core set:** 55 texts (all texts from types with `count(type) ≥ 2`)  
  - **Coverage set:** 6 texts (15% random sample from singleton types)
- **Unique selected types:** 25  
  - **Core types:** 19 (types with at least two attestations)  
  - **Coverage types:** 6 (single types sampled for breadth)

#### Documentary diversity within the core set
To reduce dependence on a single recording context and to improve generalizability of pipeline evaluation, we assessed whether the two (or more) texts available for each core type span multiple documentary contexts.

- **Volume diversity:** 16/19 core types (≈84%) include texts from at least two distinct volumes.  
  Three types are volume-constrained (both attestations originate from the same volume): **ATU 301**, **ATU 700**, and **ATU 703\***.

- **Year diversity:** 17/19 core types (≈89%) include texts from at least two distinct years.  
  Two types are year-constrained: **ATU 700** and **ATU 703\***.

Overall, the resulting Corpus B retains strong within-type comparability (via the core set) and maintains thematic breadth (via the coverage set), while achieving high documentary diversity for most core types (across volumes and years).

-----

## 3. Corpus B diagnostics

### 1.Type distribution and within-type comparability
The type-frequency histogram shows a substantial reduction in typological breadth from 57 types (Full Corpus A) to 25 types (Selected Corpus B). At the same time, Corpus B shifts the distribution away from singleton types toward types with ≥2 attestations, consistent with the core-set rule. As a result, the selected corpus prioritizes within-type comparability  over maximal coverage of rare, one-off types.

### 2. Collector coverage and concentration effects
Collector coverage decreases from 41 collectors (Full Corpus A) to 23 collectors (Corpus B), reflecting the expected trade-off when the corpus is reduced. The “texts per collector” plot indicates a moderate concentration: a small number of collectors contribute a disproportionately larger share of texts (the top contributors have ~5–11 texts each), while most collectors contribute 1–2 texts. 

This suggests that, although the corpus remains multi-collector, documentary perspectives are not evenly distributed and analyses sensitive to collector practice should control for this imbalance.

### 3. Documentary breadth across volumes and years
Corpus B retains broad documentary coverage despite the reduction in size. The volume/year coverage plot shows a decline from 24 → 19 volumes and 39 → 29 years, meaning that the selected subset still spans a wide range of compilation contexts. This supports the methodological goal of reducing dependence on a single volume/year-specific layout or recording context, while keeping the evaluation and annotation workload manageable.

### Overall assessment
Overall, **Corpus B** operationalizes a thesis-scope compromise: it preserves **variant structure within types** and maintains substantial **temporal and volume diversity**, while reducing typological and collector breadth. The remaining collector concentration is acceptable for Corpus B, provided that downstream evaluation and interpretation explicitly acknowledge collector effects and, where necessary, stratify analyses by collector or treat it as a confounding factor.


