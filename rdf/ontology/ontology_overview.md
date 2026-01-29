
# Knowledge Model

This document defines the minimal, analysis-oriented knowledge model for the Unlocking Russian Folklore corpus and the classifier layer. The model is designed to support (a) faceted retrieval and (b) type-assignment decision support (Top-3 + expert validation)

---

## 1. Core vocabularies and namespaces

### 1.1 Reused ontologies

- `dcterms:` — DCTERMS (descriptive metadata, source, rights, part-of relations).
- `skos:` — Simple Knowledge Organization System (controlled vocabularies (ATU types, genres/categories, optional keywords/motifs)
- `prov:` — PROV-O (W3C Provenance Ontology) for provenance of transformations, classifier runs, generated artifacts.
- `crm:` — CIDOC-CRM (for class-level alignment of events, persons, places, collections)
- `ontoDM:` — OntoDM for typing predictive models (the exported model entity is a predictive model; in our JSON-LD it is currently typed as a probabilistic predictive model).

### 1.2 Project namespace and instance namespace

- `rft:` — *Russian Folktales vocabulary* for project-specific classes and properties used when no adequate term exists in reused vocabularies (folklore-specific glue + classifier/export-specific properties such as confidence bands, decision policy references, dataset snapshot pointers, and input integrity hashes).

**Ontology namespace:**
- `rft:` = `https://eugeniavd.github.io/magic_tagger/rdf/ontology#`

**Data namespace (instances produced by the pipeline and the classifier):**
- `BASE_DATA` = `https://eugeniavd.github.io/magic_tagger/rdf/`

GitHub Pages gives us a stable HTTPS origin owned by the project, with human-browsable, dereferenceable links for static artifacts—without running a separate server. This makes the KG easier to inspect, cite, and reuse.

Why we separate schema vs data:
- Schema (TBox) uses a hash namespace (.../ontology#Term) for compact term IRIs.

- Data (ABox) uses slash IRIs under BASE_DATA for large numbers of instances and predictable paths.
Identity IRIs are minted under BASE_DATA for all instances: ".../tale/{tale_id}"
Metadata exports include resolvable links to the exact artifacts used at inference time. Download URLs (machine-readable file content) are stored separately and must be resolvable links (no synthetic placeholders). 

This keeps the graph stable and inspectable (canonical IRIs) while remaining reproducible (explicit file pointers).
---

## 2. Entity-level mapping

We keep machine-learning provenance lightweight by relying on PROV-O for activities and entities, and we use OntoDM only for typing predictive models. Project-specific rft: terms are limited to (i) folklore-domain glue and (ii) classifier output convenience properties (Top-K candidates, scores, decision policy), which are not covered by the reused ontologies.

### 2.1 Main entities and alignments

| Local entity | Description | Working class & alignment |
|--------------|-------------|---------------------------|
| **Tale** | A single folktale text (one row in the index; stable unit for classification). | `rft:Tale` (project class), aligned to `crm:E33_Linguistic_Object` and `prov:Entity`. |
| **Collection** | Archival collection / series such as “ERA, Vene”, “RKM, Vene”, “TRÜ, VKK”. | `dcmitype:Collection`; conceptually alignable to `crm:E78_Curated_Holding`. |
| **Volume** | Physical volume within a collection (bound manuscript volume / archival unit). | `dcterms:BibliographicResource` (intellectual description) and `crm:E22_Man-Made_Object` (carrier). |
| **Place** | Settlement / parish used in recording and origin fields. | `crm:E53_Place`. |
| **Type code** | Tale type codes and related classifications (controlled vocabularies). | `skos:Concept` in a `skos:ConceptScheme` (ATU, SUS, national schemes). Codes use `skos:notation`. |
| **Recording event** | The act of recording a tale by one or more collectors from a narrator at a given time and place. | `prov:Activity` aligned with `crm:E7_Activity`.  |

**Classifier-specific entities (new, produced by the system)**

| Local entity | Description | Working class & alignment |
|--------------|-------------|---------------------------|
| **Classification run** | One execution of the classifier for a given input (timestamped), with explicit provenance of inputs used (model, input text snapshot, dataset snapshot, policy/labels, bibliographic typing source). | `prov:Activity` *(optionally also `rft:ClassificationRun` as a convenience type).* |
| **Classification result** | The produced prediction bundle for a tale, including Top-3 candidates, policy band, and final decision fields (model vs expert). | `prov:Entity` *(optionally also `rft:ClassificationResult` as a convenience type).* |
| **Candidate** | A single ranked prediction (ATU code + score), linked to the predicted tale type concept. | `rft:ClassificationCandidate` (project class; represented as an entity node in JSON-LD exports). |
| **Input text (stable)** | Stable input artifact identified by the external tale id (not the run id). | `prov:Entity` (e.g., the “InputText” node). |
| **InputTextSnapshot (run-specific)** | A run-specific snapshot carrying integrity information (e.g., `rft:sha256` of the submitted text) and derivation from the stable input text. | `prov:Entity`, linked via `prov:wasDerivedFrom` to the stable input text.|
| **DatasetSnapshot** | The corpus snapshot/version used at inference time (what the classifier had access to). Identified by `source_version` (e.g., `sha256:…`) and may point to a published dataset via `rdfs:seeAlso` (exposed as `datasetUri` in JSON-LD; e.g., a commit permalink or release asset). | `prov:Entity`  |
| **Model** | The trained predictive model artifact used by the run. | `prov:Entity`, additionally typed with OntoDM as **`ontoDM:OntoDM_000073`** (probabilistic predictive model). *(No separate `rft:Model` class required.)* |
| **Human review** | A separate provenance activity only when the final decision is not the model (expert override), optionally attributed to an expert agent. | `prov:Activity`; optional `prov:Agent` via `prov:wasAttributedTo`.|


---

## 3. Field-to-property mapping

This section shows how fields from `corpus_a_index` map to RDF properties. It is intentionally minimal; more detailed modelling (e.g., full CIDOC-CRM event patterns, narrative content) can be added later.

**Principles**
- For descriptive metadata (format, rights, source, dates), reuse DCTERMS (e.g., `dcterms:format`, `dcterms:rights`, `dcterms:created`, `dcterms:source`).
- For controlled vocabularies (ATU/SUS/national types; genres/categories), use SKOS (`skos:Concept`, `skos:ConceptScheme`, `skos:notation`).
- For provenance of transformations and classifier outputs, use PROV-O (`prov:Entity`, `prov:Activity`, `prov:used`, `prov:wasGeneratedBy`, `prov:wasDerivedFrom`).
- Introduce `rft:` properties **only** when there is no adequate reusable predicate, and keep them lightweight and stable.

### 3.1 Identification and source (corpus index)

**Domain:** Tale (`rft:Tale`, aligned with `crm:E33_Linguistic_Object` and `prov:Entity`)

| Local field | Description | RDF property | Target vocabulary |
|-------------|-------------|--------------|-------------------|
| `tale_id` | Stable identifier within the corpus (used to mint the tale IRI). | `@id` (URI template), e.g. `https://github.com/eugeniavd/magic_tagger/rdf/tale/{tale_id}` | project / JSON-LD |
| `collection` | Archival series (e.g., “ERA, Vene”, “RKM, Vene”, “TRÜ, VKK”). | `dcterms:isPartOf` → Collection resource | DCTERMS (+ optional CRM alignment) |
| `volume_no` | Volume number within a collection (bound manuscript volume / archival unit). | `dcterms:isPartOf` → Volume resource; store the volume identifier on the volume as `dcterms:identifier` | DCTERMS |
| `source_ref` | Full archival shelfmark string (as given in the index). | `dcterms:source` (literal or link to a source entity if modelled) | DCTERMS |


### 3.2 Digital carrier and rights

**Domain:** Tale (`rft:Tale`)

| Local field | Description | RDF property | Target vocabulary |
|---|---|---|---|
| `digital_carrier` | Digital carrier / representation type (e.g., scan, transcript-only). Prefer a controlled value set. | `dcterms:format` | DCTERMS |
| `rights_status` | Access and reuse status (e.g., open, restricted; anonymised). | `dcterms:accessRights`, `dcterms:rights` | DCTERMS |


### 3.3 Agents: narrators and collectors

This section models human agents in the archival corpus (narrators, collectors).  
**Note:** classifier-related humans (e.g., a folklore expert who overrides a prediction) are handled separately under **Classifier provenance** (expert review as `prov:Activity` + optional `prov:wasAttributedTo prov:Agent`). We do not mix *archival roles* with *annotation roles*.

---

#### Core entities

- **Tale**: `rft:Tale` (project class; aligned with `crm:E33_Linguistic_Object` and `prov:Entity`)
- **Volume**: `dcterms:BibliographicResource` (and optionally `crm:E22_Man-Made_Object` as carrier in the light profile)
- **Person (Agent)**: `prov:Agent` (optionally `crm:E21_Person`)

---

#### Role principle (no custom narrator/collector classes)

- We mint stable **Person** URIs and keep roles **contextual** (expressed by the predicate + the domain of the statement).
- We do **not** introduce `rft:Narrator` / `rft:Collector` classes (nor “facet tags”). Role is determined by where/how the person is linked.

**URI policy**
- Preferred: `BASE_DATA + "/person/{person_id}"` (stable internal ID).
- Fallback: `BASE_DATA + "/person/{slug}"` (deterministic and collision-safe).

---

#### Canonical role links (two-layer attribution)

We separate two attribution layers because narrators affect content variation, while collectors affect capture conditions (handwriting/legibility/HTR–OCR usability). Also, recording time is available at the volume level.

| Context | Domain | Property | Range | Meaning |
|---|---|---|---|---|
| **Tale-level (content attribution)** | Tale | `dcterms:contributor` | Person | Narrator attribution (variant/content analysis) |
| **Volume-level (capture attribution)** | Volume | `dcterms:creator` | Person | Collector/fieldworker attribution (capture/HTR quality analysis) |
| **Tale → Volume containment** | Tale | `dcterms:isPartOf` | Volume | Tale belongs to a volume (recording context carrier) |

**Notes**
- Collectors are attached to the **Volume**, because capture context (including recording time and handwriting) is volume-scoped in the available metadata.
- Multiple collectors are represented as repeated `dcterms:creator` statements (no `collector_1…collector_5` in RDF).

---

#### Person node

On each **Person** resource:

- **Types:** `prov:Agent` (required); optionally `crm:E21_Person`
- **Display name:** `rdfs:label`
- **Biographical note:** `dcterms:description`

**Naming hygiene**
- Keep `rdfs:label` strictly for the human-facing display name.
- Store raw strings / parsing artifacts outside `rdfs:label` (e.g., `skos:altLabel` or a project literal like `rft:rawName`) if needed.

---

#### Mapping from local index fields

| Local field | Description | RDF mapping | Comment |
|---|---|---|---|
| `narrator` | Narrator name + bio note (composite) | `Tale dcterms:contributor Person`; `Person rdfs:label` + `dcterms:description` | Repeat `dcterms:contributor` if multiple narrators |
| `collector_1`–`collector_5` | Collectors listed for the volume | `Volume dcterms:creator Person` (repeated) | Index stays columnar; RDF becomes repeated assertions |
| `volume_date` (or similar) | Recording/capture date at volume level | `Volume dcterms:created` (`xsd:date` / `xsd:gYear`) | Enables time coverage queries and capture-context filtering |


---

### 3.4 Institutions and organisations

This section covers institutional affiliations recorded in the index (e.g., narrator’s school in pupil collections).  We keep the baseline lightweight and avoid role-specific agent subclasses.

**Domain:** Person (`prov:Agent`, optionally `crm:E21_Person`) referenced as narrator via `dcterms:contributor`

| Local field | Description | RDF property | Target vocabulary |
|---|---|---|---|
| `narrator_school` | School associated with the narrator (mainly for pupil collections). | `dcterms:description` | DCTERMS |

This avoids introducing a custom property and keeps interoperability high.

**Future upgrade**
- We could introduce an **Organisation** node only if you actually need querying over institutions:
  - Organisation: `crm:E74_Group` (and optionally `prov:Agent`)
  - Link: `dcterms:relation` (or `crm:P107_has_current_or_former_member`)
- Then we could keep the literal as the raw label for traceability and add the organisation IRI for structured linking.

---

### 3.5 Places and spatial information

We model places primarily as `crm:E53_Place` nodes with human-readable labels, and we keep links from the corpus entities lightweight. 

**Domains:**  
- Tale: `rft:Tale` (aligned to `crm:E33_Linguistic_Object`, `prov:Entity`)  
- Person: `prov:Agent` (optionally `crm:E21_Person`) referenced as narrator via `dcterms:contributor`  
- Place: `crm:E53_Place`

#### Baseline linking: Tale ↔ Place, Person ↔ Place

| Local field | Description | RDF property / pattern | Target vocabulary |
|---|---|---|---|
| `recording_parish` | Parish where the tale was recorded. | `Tale dcterms:spatial Place` | DCTERMS / CIDOC-CRM |
| `recording_place` | Settlement of recording. | `Tale dcterms:spatial Place` | DCTERMS / CIDOC-CRM |
| `narrator_origin_parish` | Parish of narrator’s origin. | `Person dcterms:spatial Place` | DCTERMS / CIDOC-CRM |
| `narrator_origin_place` | Settlement of narrator’s origin. | `Person dcterms:spatial Place` | DCTERMS / CIDOC-CRM |

**Place node**
- Label(s): `rdfs:label` in the original archival language.
- Optional additional labels: `skos:prefLabel` / `skos:altLabel` to manage multilingual place labels as a controlled vocabulary.

#### Richer model 

To distinct  “recording place” from “origin place” (beyond a generic `dcterms:spatial`), we introduce a recording activity:

- `rft:RecordingEvent a prov:Activity` 
- `Tale prov:wasGeneratedBy rft:RecordingEvent`
- `rft:RecordingEvent crm:P7_took_place_at Place`
- `rft:RecordingEvent prov:wasAssociatedWith CollectorAgent`

This keeps the baseline simple while providing an upgrade path for CRM-style event modelling.

---

### 3.6 Temporal information

**Domain:**  
- **Volume** (preferred for capture context): `dcterms:BibliographicResource` (optionally alignable to `crm:E22_Man-Made_Object`)  
- **Classifier run** (system-produced): `rft:ClassificationRun` aligned with `prov:Activity`

This project distinguishes **two time axes**:

1. **Fieldworktime** (historical capture of the tale) — archival metadata, typically volume-scoped.  
2. **Computation time** (when the classifier was executed) — system provenance (run timestamps).

#### 3.6.1 Recording time 

**Preferred baseline: attach to Volume, not Tale**

Rationale: recording context (including time) is usually consistent within a volume and co-varies with collectors and capture conditions. Tale-level recording dates can be introduced later if truly reliable at row level.

| Local field | Description | RDF property / pattern | Target vocabulary |
|---|---|---|---|
| `recorded_date_start` | Start date of recording (index). | **Baseline:** `Volume dcterms:created` (ISO literal). | DCTERMS / PROV / CIDOC-CRM |
| `recorded_date_end` | End date of recording (if given). | `RecordingEvent prov:endedAtTime` (ISO dateTime), or CIDOC `crm:P4_has_time-span` → `crm:E52_Time-Span`. | PROV / CIDOC-CRM |

**Notes**
- If the source provides only a single day, store it as `"YYYY-MM-DD"^^xsd:date` via `dcterms:created`.
- If the source provides only a year (or year-month), we may use `xsd:gYear` and preserve the raw string separately.

#### 3.6.2 Classifier run time (system provenance)

Classifier outputs already contain run-time timestamps; these are not the historical recording dates.

| Produced meta field | Meaning | RDF mapping in JSON-LD export | Target vocabulary |
|---|---|---|---|
| `created_at` | When the classifier run was executed (inference time). | `ClassificationRun prov:startedAtTime` | PROV-O |
| `trained_at` | When the model artifact was trained (training time). | `Model rft:trainedAt` (typed `xsd:dateTime`) | rft (typed literal) |

This separation prevents accidental mixing of “1930 fieldwork” with “2026 inference”.

---

### 3.7 Content and classification

**Domain:**  
- **Tale (archival text unit):** `rft:Tale` aligned to `crm:E33_Linguistic_Object` / `prov:Entity`  
- **Controlled vocabularies:** `skos:Concept` within one or more `skos:ConceptScheme`

This section separates **archival content description & cataloguing** from **system-produced classifier outputs**.  
Archival fields stay attached to the Tale; classifier outputs are exported as PROV-described artifacts (`ClassificationRun`, `ClassificationResult`, `ClassificationCandidate`) that *refer to* ATU concepts.

---

#### 3.7.1 Archival content description and cataloguing 

| Local field | Description | RDF property / pattern | Target vocabulary |
|---|---|---|---|
| `content_description` | Short content note. | `Tale dcterms:description` | DCTERMS |
| `genre_1`–`genre_3` | Archival genres. | **Preferred:** `Tale dcterms:subject skos:Concept` (genre scheme). | SKOS / DCTERMS / (optional rft) |
| `subgenre` | Subgenre (e.g., `imemuinasjutt`). | `Tale dcterms:subject skos:Concept`; on concept: `skos:broader` to main genre. | SKOS / DCTERMS |
| `folklore_category` | Fine-grained category. | `Tale dcterms:subject skos:Concept`; relations via `skos:broader`, `skos:related`. | SKOS / DCTERMS |
| `type_code_1`–`type_code_4` | ATU, SUS, national type codes (if present in index). | `Tale dcterms:subject skos:Concept` (typed as a type concept; scheme-specific via `skos:inScheme`; code via `skos:notation`). | SKOS / DCTERMS |

**Key modelling choice:**
- We use `dcterms:subject` as the canonical link from Tale → controlled concepts (types, genres, categories).  

**Notes**
- We kept archival descriptions in the source language in `dcterms:description`. English summaries we cpuld store as additional literals with language tags, or as a separate field mapped to `dcterms:description` with `"@language": "en"`.

---

#### 3.7.2 Classifier-produced classification

The classifier does not overwrite archival cataloguing because it was built for external folktales typing. It produces:
- a **run** (`rft:ClassificationRun` / `prov:Activity`)  
- a **result** (`rft:ClassificationResult` / `prov:Entity`)  
- **candidates** (`rft:ClassificationCandidate`) pointing to ATU concepts (`skos:Concept`)

Minimal pattern:
- `ClassificationResult rft:forTale Tale`
- `ClassificationResult prov:wasGeneratedBy ClassificationRun`
- `ClassificationResult rft:hasCandidate Candidate`
- `Candidate rft:predictedTaleType skos:Concept` (ATU) + `rft:confidenceScore` + `rft:rank`
- `ClassificationResult rft:primaryATU / rft:finalATU` → ATU concept (IRI minted as `/taleType/atu/{code}`)

**Important:** classifier decisions (`primaryATU`, `finalATU`, `confidenceBand`, `decisionPolicyId`, `deltaTop12`) live on the **ClassificationResult**, not on the Tale, to preserve scholarly neutrality and provenance.

---

#### 3.7.3 Schemes and concept identifiers 

- Every type/genre/category concept is a `skos:Concept` and must belong to a scheme: `skos:inScheme skos:ConceptScheme`.  
- The code is stored as `skos:notation` (e.g., `"709"`, `"510A"`).  
- In exports, predicted ATU concepts are referenced by IRIs like:  
  `.../rdf/taleType/atu/709`, and may additionally carry `skos:notation "709"`.

This keeps the ontology clean: SKOS carries the semantics of classification systems; rft carries only the classifier artifacts and convenience typed literals.

---


## 4. Tale types as SKOS concepts

Canonical statement in the published KG:

- Tales point to classification concepts via **`dcterms:subject`**.
- Tale types (ATU/SUS/national) are **`skos:Concept`** resources.

This keeps the Tale neutral: catalogue assignments and model suggestions can coexist without overwriting each other. Classifier outputs link to the same concept URIs through rft:predictedTaleType / rft:primaryATU / rft:finalATU on the ClassificationResult

### 4.1 Concept schemes

There is no universally accepted open URI authority for ATU distributed by the rights holders. ATU is a published reference work; current editions are commercial/controlled. Therefore:

- We treat any web-published ATU vocabularies as optional outbound links, not a dependency.

- Wikidata provides an ATU code identifier property (P2540), which is useful for cross-linking, but it is not an authoritative SKOS scheme for ATU concepts.

Project knowledge graph remains self-contained and stable even if external URIs change or disappear.

### 4.2.FAIR strategy
1. Mint our own SKOS concept URIs for ATU types in our stable namespace.
<.../rdf/taleType/atu/707>.

2. Store the code as `skos:notation` and label(s) as `skos:prefLabel`.

3. Link outward opportunistically using SKOS mapping properties when stable targets exist:

- `skos:exactMatch` (strong equivalence),
- `skos:closeMatch` (near equivalence),
- `rdfs:seeAlso` (lightweight pointer),
without making external sources a core dependency.

We define at least three SKOS concept schemes:

- `rft:ATU_Scheme`  
  — Сoncept scheme for Aarne–Thompson–Uther tale types (ATU).

- `rft:SUS_Scheme`  
  — Сoncept scheme for East Slavic SUS tale types.

- `rft:EE_Scheme`  
  — Сoncept scheme for Estonian national tale types.

Each individual genre / subgenre / category is represented as:

- a `skos:Concept`
- `skos:inScheme` 
- `skos:prefLabel`, and optionally `skos:broader` to model subgenre/category hierarchies.

<tale> dcterms:subject <genre/imemuinasjutt> .

Each individual tale type (ATU, SUS, national schemes) is represented as:

- a `skos:Concept`
- `skos:inScheme` one of the type schemes (`rft:ATU_Scheme`, `rft:SUS_Scheme`, `rft:EE_Scheme`, …)
- `skos:notation` carrying the code (e.g., "706", "510A", "1060*"), plus optional labels.

<tale> dcterms:subject <taleType/atu/707> .

---

### 4.3. Classifier alignment (important):

The classifier does not assert dcterms:subject on the Tale.

It produces a rft:ClassificationResult that references the same concept URIs via:

- `rft:primaryATU` (effective decision in the export),
- `rft:modelPrimaryATU` (model-only),
- `rft:finalATU` + `rft:finalDecisionSource` (model vs expert),

Also, it links candidates through rft:predictedTaleType.

---

## 5. Classifier layer

Our goal is to make the “knowledge management” auditable and reproducible: every suggestion is tied to a specific input text snapshot, model artifact, dataset snapshot, policy + label-set, and an execution timestamp. The exported JSON-LD is the canonical provenance record for one run.

### 5.1 Ontologies used

- **PROV-O (`prov:`)** — provenance of runs and artifacts (`prov:Activity`, `prov:Entity`, `prov:used`, `prov:generated`, `prov:wasGeneratedBy`, `prov:wasDerivedFrom`, `prov:startedAtTime`).
- **OntoDM (`ontoDM:`)** — lightweight typing of the model as a predictive model.
- **DCTERMS (`dcterms:`)** — descriptive pointers and bibliographic source (typing reference) used by the model (`dcterms:source`, `dcterms:BibliographicResource`).
- **Project vocabulary `rft:`** — only where reuse-first vocabularies do not provide adequate terms:
  - classifier nodes: run/result/candidate/text snapshot/dataset snapshot/model
  - compact governance fields (confidence band, deltaTop12, tale status, policy id)
  - convenience links (e.g., `rft:forTale`, `rft:hasCandidate`, `rft:usedModel`)


### 5.2 Minimal mapping 

#### 1) ClassificationRun 

- **Types:** `prov:Activity`, `rft:ClassificationRun`

**Key links/fields:**
- `prov:startedAtTime` → run timestamp (`meta.created_at`)
- `rft:forTale` → `rft:Tale`
- `prov:used` → inputs used in this run:
  - `rft:Model` (trained model artifact)
  - `rft:InputTextSnapshot` (run-specific text snapshot)
  - `rft:DatasetSnapshot` (dataset snapshot available at inference)
  - typing source (`dcterms:BibliographicResource`)
  - policy URI and labels URI (IRIs to `models/meta.json` and `models/labels.json`)
- `prov:generated` → `rft:ClassificationResult`
- `rft:usedModel` → model IRI (convenience pointer)
- `rft:sourceVersion` → dataset snapshot identifier string (`meta.source_version`, e.g., `sha256:…`)

#### 2) Model

- **Types:** `prov:Entity`, `rft:Model`, plus OntoDM typing  
  (e.g., `ontoDM:probabilistic_predictive_model` or your chosen `ontoDM:OntoDM_000073` mapping)

**Key fields (exported / in meta):**
- `rft:modelTag` ← `meta.model_version`
- `rft:modelSha` ← `meta.model_sha`
- `rft:trainedAt` ← `meta.trained_at`
- `rft:task` ← `meta.task`
- `rft:textCols` ← `meta.text_cols`
- `dcterms:source` → bibliographic typing source (ATU reference)

**Training corpus pointer (meta):**
- `meta.dataset_uri` — a stable publication pointer for the training dataset (currently a GitHub commit permalink; later may become a release asset/DOI).

#### 3) ClassificationResult 

- **Types:** `prov:Entity`, `rft:ClassificationResult`

**Key links/fields (exported):**
- `prov:wasGeneratedBy` → `rft:ClassificationRun`
- `rft:forTale` → `rft:Tale`
- `rft:hasCandidate` → Top-K `rft:ClassificationCandidate` nodes
- governance fields:
  - `rft:taleStatus` ← `meta.tale_status` (e.g., `accept`, `review`)
  - `rft:deltaTop12` ← `meta.delta_top12`
  - `rft:confidenceBand` ← `meta.confidence_band` (policy band)
  - `rft:decisionPolicyId` ← `meta.decision_policy`
  - `rft:decisionPolicy` ← `meta.decision_policy_uri` (IRI)
  - `rft:labels` ← `meta.labels_uri` (IRI)
  - `rft:primaryATU`, `rft:modelPrimaryATU`, `rft:finalATU`
  - `rft:finalDecisionSource`, `rft:finalExpertNote`, `rft:finalSavedAt`

#### 4) ClassificationCandidate 

- **Types:** `rft:ClassificationCandidate`

**Fields (exported):**
- `rft:rank` → integer
- `rft:predictedTaleType` → URI of the type concept (e.g., `…/taleType/atu/709`)
- `skos:notation` → original code string (e.g., `"709"`, `"510A"`)
- `rft:confidenceScore` → decimal score

#### 5) InputTextSnapshot (integrity of submitted text)

- **Stable text entity:** `rft:InputText` (`prov:Entity`) identified by `meta.tale_id`
- **Run snapshot:** `rft:InputTextSnapshot` (`prov:Entity`)
  - `prov:wasDerivedFrom` → `rft:InputText`
  - `rft:sha256` ← `meta.text_sha256` (hash of submitted text)

#### 6) DatasetSnapshot (what the classifier had access to at inference)

- **Types:** `prov:Entity`, `rft:DatasetSnapshot`
- **Identifier:** `meta.source_version` (e.g., `sha256:ea72…`)
- **Publication pointer:** `datasetUri` (mapped to `rdfs:seeAlso`) ← `meta.dataset_uri`  
  (points to the published training dataset version: commit permalink now; release asset later)

### 5.3 Human-in-the-loop (HITL) handling

We record expert intervention only when the final decision is not the model:

- `rft:finalDecisionSource` is `"model"` by default.
- If expert overrides:
  - `rft:finalDecisionSource = "expert"`
  - `rft:finalATU`, `rft:finalExpertNote`, `rft:finalSavedAt` are filled
  - optionally emit a separate provenance activity:
    - `rft:HumanReview a prov:Activity`
    - `prov:used` → the model result entity
    - optional `prov:wasAttributedTo prov:Agent` (expert)

### 5.4 Governance fields 

- Decision + uncertainty: `tale_status`, `primary_atu`, `model_primary_atu`, `final_atu`, `final_decision_source`, `final_saved_at`, `final_expert_note`, `delta_top12`, `confidence_band`
- Reproducibility pointers: `labels_uri`, `decision_policy_uri`, `decision_policy` (id), `source_version`, `dataset_uri`
- Artifact identities: `run_id`, `model_sha`, plus minted IRIs: `run_uri`, `model_uri`, `input_text_uri`, `result_uri`
- Integrity: `text_sha256`
- Typing reference: `typing_source` (bibliographic resource node)

---

## 6. Dataset-level modeling

The corpus is published as a versioned Dataset that contains many individual tale records.  
We use DCAT for distribution metadata and DCTERMS/PROV for provenance and governance notes.

### 6.1 Rationale

- A **Dataset node** represents a specific release (or publication snapshot) of the corpus, with stable citation metadata (title, license, publisher, issued date).
- **Tales are first-class resources** (not “rows”), and are linked to the dataset via part–whole relations.
- The dataset points to **distributions** (TTL/JSON-LD exports, SHACL shapes, and other release assets), making the release machine-actionable and reproducible.
- We also distinguish:
  - a **published training dataset pointer** (`dataset_uri`, e.g. a commit link) used to document what the model was trained on; and
  - an **inference-time dataset snapshot identifier** (`source_version`, e.g. `sha256:…`) that documents what corpus snapshot was available at prediction time (recorded in the `rft:DatasetSnapshot` node).

### 6.2 Canonical pattern

- `dcat:Dataset` — the corpus release / published snapshot
- `dcat:Distribution` — concrete downloadable artifacts for the release (exports + validation assets)
- `dcterms:hasPart` / `dcterms:isPartOf` — link Dataset ↔ Tale resources
- `prov:wasDerivedFrom` + `dcterms:source` — capture source references and derivations
- `dcterms:license`, `dcterms:rights`, `dcterms:accessRights` — rights and access constraints

### 6.3 Dataset ↔ Tale policy

- Each tale record is linked to the dataset:
  - `Tale dcterms:isPartOf Dataset`
  - (optionally also) `Dataset dcterms:hasPart Tale`

This enables cross-release governance and “what changed between versions” practices.

### 6.4 Consistency with the classifier exports 

- **Dataset-level (DCAT):** the authoritative publication record for a corpus release and its downloadable distributions.
- **Classifier layer:**
  - `meta.dataset_uri` is a *publication pointer* to the training corpus package/version (commit permalink / release asset / DOI).
  - `meta.source_version` is a *checksum-style snapshot ID* recorded in `rft:DatasetSnapshot` to describe the inference-time snapshot.
  - A `rft:DatasetSnapshot` node may include `rdfs:seeAlso` (exported as `datasetUri`) linking to the published dataset artifact that corresponds to that snapshot.

---

## 7. Datatype commitments

The knowledge graph explicitly commits key datatypes to ensure machine-actionability, validation, and consistent downstream querying.

**Classifier layer:**
- `rft:confidenceScore` → `xsd:decimal`
- `rft:deltaTop12` → `xsd:decimal`
- `rft:rank` → `xsd:integer`
- `prov:startedAtTime` → `xsd:dateTime` 
- `rft:trainedAt` → `xsd:dateTime`
- `rft:finalSavedAt` → `xsd:dateTime`
- `rft:modelSha` → `xsd:string`
- `rft:sourceVersion` → `xsd:string`   
- `rft:sha256` → `xsd:string`   
- `rft:task` → `xsd:string`
- `rft:confidenceBand` → `xsd:string`
- `rft:decisionPolicyId` → `xsd:string`
- `rft:taleStatus` → `xsd:string`
- `rft:finalDecisionSource` → `xsd:string`
- `rft:finalExpertNote` → `xsd:string`

**Core corpus layer:**
- `dcterms:created` → `xsd:date` *(or `xsd:gYear` when only a year is known)*

**Controlled vocabularies:**
- `skos:notation` → `xsd:string`  
  *(codes may contain letters and symbols such as `*`, e.g., `510A`, `1060*`)*
