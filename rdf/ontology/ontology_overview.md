
# Knowledge Model

This document defines the minimal, analysis-oriented knowledge model for the Unlocking Russian Folklore corpus and the classifier layer. The model is designed to support (a) faceted retrieval and (b) type-assignment decision support (Top-3 + expert validation)

---

## 1. Core vocabularies and namespaces

### 1.1 Reused ontologies

- `dcterms:` — DCTERMS (descriptive metadata: identifiers, descriptions, rights/access rights, citations, and part–whole containment via `dcterms:isPartOf`, plus `dcterms:subject` links to ATU concepts).
- `skos:` — SKOS (controlled vocabulary for ATU types: `skos:Concept`, `skos:inScheme`, `skos:notation`, `skos:prefLabel`).
- `prov:` — PROV-O (used for attribution as explicit provenance statements: `prov:qualifiedAttribution` / `prov:Attribution` with `prov:agent` and `prov:hadRole`; also used for lightweight derivation links such as `prov:wasDerivedFrom`).
- `locrel:` — Library of Congress MARC Relators (role URIs such as `locrel:nrt` and `locrel:col`, used as values of `prov:hadRole`).
- `crm:` — CIDOC-CRM (class-level alignment for core entities in the corpus: tales as `crm:E33_Linguistic_Object`, persons as `crm:E21_Person`, places as `crm:E53_Place`; event-level modelling is an optional extension).
- `dcmitype:` — DCMI Type Vocabulary (collections as `dcmitype:Collection`).
- `foaf:` — FOAF (web-facing links such as `foaf:page` for landing pages; and optional typing/compatibility for persons via `foaf:Person` where used).
- `dcat:` — DCAT (dataset/distribution packaging in the dataset export).
- `ontoDM:` — OntoDM (only if/where the exported model JSON-LD uses it to type predictive models).

### 1.2 Project namespace and instance namespace

- `rft:` — *Russian Folktales vocabulary* for project-specific classes and properties used where reused vocabularies are insufficient. In the classifier export JSON-LD, `rft:` carries governance and run-specific fields such as `rft:confidenceBand`, `rft:decisionPolicyId`, resolvable policy/labels pointers (`rft:decisionPolicyDownload`, `rft:labelsDownload`), dataset snapshot identifiers (`rft:sourceVersion` plus a `rft:DatasetSnapshot` node with a published pointer via `rdfs:seeAlso`), and input integrity hashes (`rft:sha256` on `rft:InputTextSnapshot`). 


**Schema namespace:**
- `rft:` = `https://eugeniavd.github.io/magic_tagger/rdf/ontology#`

**Data namespace (instances produced by the pipeline and the classifier):**
- `BASE_DATA` = `https://eugeniavd.github.io/magic_tagger/rdf/`

GitHub Pages provides a stable HTTPS origin owned by the project, enabling dereferenceable, human-browsable IRIs for published artefacts without running a separate server, which improves inspection and citation.

Why we separate schema vs data:
- Schema uses a hash namespace (.../ontology#Term) for compact term IRIs.

- Data uses slash IRIs under `BASE_DATA` for large numbers of instances and predictable paths (".../tale/{tale_id}")

Metadata exports include resolvable links to the exact artefacts used at inference time: the run enumerates its inputs (model, text snapshot, dataset snapshot, and external policy/labels resources). 

This keeps the graph stable and inspectable (canonical IRIs) while remaining reproducible (explicit file pointers).

---

## 2. Entity-level mapping

We keep machine-learning provenance lightweight by relying on PROV-O for activities and entities, and we use OntoDM only for typing predictive models. Project-specific rft: terms are limited to (i) folklore-domain glue and (ii) classifier output convenience properties (Top-K candidates, scores, decision policy), which are not covered by the reused ontologies.

### 2.1 Main entities and alignments

| Local entity | Description | Working class & alignment |
|--------------|-------------|---------------------------|
| **Tale** | A single folktale text (one row in the index; stable unit for classification). | `rft:Tale` (project class), aligned to `crm:E33_Linguistic_Object` and `prov:Entity`. |
| **Collection** | Archival collection / series such as “ERA, Vene”, “RKM, Vene”, “TRÜ, VKK”. | `dcmitype:Collection`; conceptually alignable to `crm:E78_Curated_Holding`. |
| **Volume** | Physical volume within a collection (bound manuscript volume / archival unit). | `dcterms:BibliographicResource` (intellectual description), optionally alignable to `crm:E22_Man-Made_Object` (carrier) as an extension. |
| **Place** | Settlement / parish used in recording and origin fields. | `crm:E53_Place`. |
| **Type code** | Tale type codes and related classifications (controlled vocabularies). | `skos:Concept` in a `skos:ConceptScheme` (ATU Index in the current realisation; additional schemes such as SUS or other national folktale type systems are optional extensions). Codes use `skos:notation`. |
| **Recording event** | Optional extension: a recording can be modelled as `prov:Activity` (alignable to `crm:E7_Activity`) if event-level modelling is introduced; the current corpus export encodes attribution without an explicit recording event. |

**Classifier-specific entities (new, produced by the system)**

| Local entity | Description | Working class & alignment |
|--------------|-------------|---------------------------|
| **Classification run** | One execution of the classifier for a given input (timestamped), with explicit provenance of inputs used (model, input text snapshot, dataset snapshot, policy/labels, bibliographic typing source). | `prov:Activity` *(optionally also `rft:ClassificationRun` as a convenience type).* |
| **Classification result** | The produced prediction bundle for a tale, including Top-3 candidates, policy band, and final decision fields (model vs expert). | `prov:Entity` *(optionally also `rft:ClassificationResult` as a convenience type).* |
| **Candidate** | A single ranked prediction (ATU code + score), linked to the predicted tale type concept. | `rft:ClassificationCandidate` (project class; represented as an entity node in JSON-LD exports). |
| **Input text (stable)** | Stable input artifact identified by the external tale id (not the run id). | `prov:Entity` (e.g., the “InputText” node). |
| **InputTextSnapshot (run-specific)** | A run-specific snapshot carrying integrity information (e.g., `rft:sha256` of the submitted text) and derivation from the stable input text. | `prov:Entity`, linked via `prov:wasDerivedFrom` to the stable input text.|
| **DatasetSnapshot** | The corpus snapshot/version used at inference time (what the classifier had access to). Identified by `source_version` (e.g., `sha256:…`) and may point to a published dataset via `rdfs:seeAlso` (exposed as `datasetUrl` in the current JSON-LD export, e.g., a commit permalink or release asset). | `prov:Entity`  |
| **Model** | The trained predictive model artifact used by the run. | `prov:Entity`, additionally typed with OntoDM as **`ontoDM:OntoDM_000073`** (probabilistic predictive model). |
| **Human review** | A separate provenance activity only when the final decision is not the model (expert override), optionally attributed to an expert agent. | `prov:Activity`; optional `prov:Agent` via `prov:wasAttributedTo`.|


---

## 3. Field-to-property mapping

This section shows how fields from `corpus_a_index` map to RDF properties. It is intentionally minimal; more detailed modelling (e.g., full CIDOC-CRM event patterns, narrative content) can be added later.

**Principles**
- For descriptive metadata (format, rights, source, dates), reuse DCTERMS (e.g., `dcterms:format`, `dcterms:rights`, `dcterms:created`, `dcterms:source`).
- For controlled vocabularies (ATU/SUS/national types; genres/categories), use SKOS (`skos:Concept`, `skos:ConceptScheme`, `skos:notation`).
- For provenance and attribution statements, used PROV-O (in the corpus graph: `prov:Entity` and qualified attribution via `prov:qualifiedAttribution` / `prov:Attribution` with `prov:agent` and `prov:hadRole`; run-level provenance such as `prov:used` / `prov:wasGeneratedBy` appears in classifier export).
- Introduce `rft:` properties **only** when there is no adequate reusable predicate, and keep them lightweight and stable.

### 3.1 Identification and source (corpus index)

**Domain:** Tale (`rft:Tale`, aligned with `crm:E33_Linguistic_Object` and `prov:Entity`)

| Local field | Description | RDF property | Target vocabulary |
|-------------|-------------|--------------|-------------------|
| `tale_id` | Stable identifier within the corpus (used to mint the tale IRI). | `@id` (URI template), e.g. `https://eugeniavd.github.io/magic_tagger/rdf/tale/{tale_id}` | project / JSON-LD |
| `collection` | Archival series (e.g., “ERA, Vene”, “RKM, Vene”, “TRÜ, VKK”). | on Volume: `dcterms:isPartOf` → Collection resource (Tale reaches Collection via its Volume) | DCTERMS (+ optional CRM alignment) |
| `volume_no` | Volume number within a collection (bound manuscript volume / archival unit). | on Tale: `dcterms:isPartOf` → Volume resource; on Volume: store volume identifier as `dcterms:identifier` (and optionally `rdfs:label` for “ERA, Vene 2”) | DCTERMS |
| `source_ref` | Full archival shelfmark string for a folktale text (as given in the index). | `dcterms:bibliographicCitation` (literal) | DCTERMS |

---

### 3.2 Access rights

**Domain:** Tale (`rft:Tale`)

| Local field | Description | RDF property | Target vocabulary |
|---|---|---|---|
| `rights_status` | Access and reuse status (e.g., open, restricted; anonymised). | `dcterms:accessRights` | DCTERMS |

---

### 3.3 Agents: narrators and collectors

This section models human agents in the archival corpus (narrators, collectors).  
**Note:** classifier-related humans (e.g., a folklore expert who overrides a prediction) are handled separately under **Classifier provenance** (expert review as `prov:Activity` + optional `prov:wasAttributedTo prov:Agent`). We do not mix *archival roles* with *annotation roles*.

- **Person (Agent)**: `prov:Agent` (alligned with `crm:E21_Person`, `foaf:Person`)
- **Display name:** `rdfs:label`
- **Biographical note:** `rdfs:comment`

#### Role principle 

- We mint stable **Person** URIs and keep roles **contextual** (expressed by qualified attribution statements that link an agent to a specific Tale (for narrators) or Volume (for collectors, because collectors are responsible for producing a whole Volume, not a Tale)).

**URI policy**
- Preferred: `BASE_DATA + "/person/{person_id}"` (stable internal ID).

#### Role links 

We separate two attribution layers because narrators affect content variation, while collectors affect capture conditions (handwriting/legibility/HTR usability). In the current export, recording date is stored at tale level as `dcterms:created (xsd:date)`.

| Context | Domain | Property pattern | Range | Meaning |
|---|---|---|---|---|
| **Tale-level (content attribution)** | Tale | `prov:qualifiedAttribution` → `prov:Attribution` with `prov:agent Person` and `prov:hadRole locrel:nrt` | Person | Narrator attribution (variant/content analysis) |
| **Volume-level (capture process attribution)** | Volume | `prov:qualifiedAttribution` → `prov:Attribution` with `prov:agent Person` and `prov:hadRole locrel:col` | Person | Collector (fieldworker) attribution |
| **Tale → Volume containment** | Tale | `dcterms:isPartOf` | Volume | Tale belongs to a volume (recording context carrier) |

**Notes**
- Multiple collectors are represented as repeated `prov:qualifiedAttribution` statements on the Volume (each with `prov:hadRole` `locrel:col`), rather than column-specific predicates.
- In PROV-O we use both an unqualified shortcut and a qualified attribution node. `prov:wasAttributedTo` provides a direct, query-friendly link from the Tale to the agent (“this Tale is attributed to this person”), while `prov:qualifiedAttribution` points to an explicit `prov:Attribution` resource that carries the *context* of that attribution—most importantly the controlled role URI (e.g., `prov:hadRole locrel:nrt` for a narrator) and any further provenance fields if needed. 

#### Mapping from local index fields

| Local field | Description | RDF mapping | Comment |
|---|---|---|---|
| `narrator_person_id` (+ narrator label/note fields) | Narrator authority id + optional display fields | `Tale prov:qualifiedAttribution  p[ a prov:Attribution ; prov:agent Person ; prov:hadRole locrel:nrt ]`; `Person rdfs:label` + optional `rdfs:comment` | Repeat attribution if multiple narrators occur |
| `collector_person_ids(_str)` | Collectors listed for the volume | `Volume prov:qualifiedAttribution [ a prov:Attribution ; prov:agent Person ; prov:hadRole locrel:col ]` | |
| `recorded_date_start` | Recording date (tale-level in current realisation) | `Tale dcterms:created` (`xsd:date`) |

---

### 3.4 Institutions and organisations

This section covers institutional affiliations.  We keep the baseline lightweight and avoid role-specific agent subclasses.

**Domain:** Person (`prov:Agent`, optionally `crm:E21_Person`) referenced as narrator via tale-level qualified attribution (`prov:qualifiedAttribution` / `prov:Attribution` with `prov:hadRole locrel:nrt`).

**Future upgrade**
- We could introduce an **Organisation** node :
  - Organisation: `crm:E74_Group` (and optionally `prov:Agent`)
  - Link: `dcterms:relation` (or `crm:P107_has_current_or_former_member`)
- Then we could keep the literal as the raw label for traceability and add the organisation IRI for structured linking.

---

### 3.5 Places and spatial information

We model places primarily as `crm:E53_Place` nodes with human-readable labels, and we keep links from the corpus entities lightweight. 

**Domains:**  
- Tale: `rft:Tale` (aligned to `crm:E33_Linguistic_Object`, `prov:Entity`)  
- Person: `prov:Agent` (`crm:E21_Person`). 
- Place: `crm:E53_Place`

#### Baseline linking: Tale ↔ Place

| Local field | Description | RDF property / pattern | Target vocabulary |
|---|---|---|---|
| `recording_place` | Settlement of recording. | `Tale dcterms:spatial Place` | DCTERMS / CIDOC-CRM |

**Place node**
- Label(s): `rdfs:label` as a human-readable string; in the current export it may combine an English normalisation with the original (Russian, Estonian).
- Optional additional labels: `skos:prefLabel` / `skos:altLabel` to manage multilingual place labels as a controlled vocabulary.

#### Richer model 

To distinct  “recording place” from “origin place” (beyond a generic `dcterms:spatial`), in future we could introduce a recording activity:

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

**Baseline**

| Local field | Description | RDF property / pattern | Target vocabulary |
|---|---|---|---|
| `recorded_date_start` | Start date of recording (index). | Tale `dcterms:created` `(xsd:date)`. | DCTERMS / PROV / CIDOC-CRM |


**Notes**
- If the source provides only a single day, store it as `"YYYY-MM-DD"^^xsd:date` via `dcterms:created`.
- If the source provides only a year (or year-month), we may use `xsd:gYear` and preserve the raw string separately.

#### 3.6.2 Classifier run time 

Classifier outputs already contain run-time timestamps; these are not the historical recording dates.

| Produced meta field | Meaning | RDF mapping in JSON-LD export | Target vocabulary |
|---|---|---|---|
| `trained_at` | When the model artifact was trained (training time). | `Model rft:trainedAt` (typed `xsd:dateTime`) | rft (typed literal) |

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
| `type_code_1`–`type_code_4` | ATU, SUS, national type codes (if present in index). | `Tale dcterms:subject skos:Concept` (typed as a type concept; classification name via `skos:inScheme`; folktale type code via `skos:notation`). | SKOS / DCTERMS |

**Notes**
We store the archival content note as `dcterms:description` (typically in the source language, Russian); additional language-tagged summaries can be added as parallel literals.
---

#### 3.7.2 Classifier-produced classification

The classifier does not overwrite archival cataloguing because it was built for external folktales typing. It produces:
- a **run** (`rft:ClassificationRun` / `prov:Activity`)  
- a **result** (`rft:ClassificationResult` / `prov:Entity`)  
- **candidates** (`rft:ClassificationCandidate`) pointing to ATU types.

Minimal pattern:
- `ClassificationResult rft:forTale Tale`
- `ClassificationResult prov:wasGeneratedBy ClassificationRun`
- `ClassificationResult rft:hasCandidate Candidate`
- `Candidate rft:predictedTaleType skos:Concept` (ATU) + `rft:confidenceScore` + `rft:rank`
- `ClassificationResult rft:primaryATU / rft:finalATU` → ATU concept (IRI minted as `/taleType/atu/{code}`)

**Important:** classifier decisions (`primaryATU`, `finalATU`, `confidenceBand`, `decisionPolicyId`, `deltaTop12`) live on the **ClassificationResult**, not on the Tale, to preserve scholarly neutrality and provenance.

---

#### 3.7.3 Schemes and concept identifiers 

- Every ATU type is a `skos:Concept` and must belong to a scheme: `skos:inScheme skos:ConceptScheme`.  
- The type number is stored as `skos:notation` (e.g., `"709"`, `"510A"`).  
- In exports, predicted ATU concepts are referenced by IRIs like:  
  `.../rdf/taleType/atu/709`, and may additionally carry `skos:notation "709"`.
- For type numbers with a star the URI path uses a normalised form while the original code is preserved in `skos:notation` (e.g., 1060* → .../atu/1060-star + `skos:notation` "1060*"). 

This keeps the ontology clean: SKOS carries the semantics of classification systems; rft carries only the classifier artifacts and convenience typed literals.

---

## 4. Tale types as SKOS concepts

### 4.1 Concept schemes

There is no universally accepted open URI authority for ATU distributed by the rights holders. ATU is a published reference work; current editions are controlled. Therefore:

- We treat any web-published ATU vocabularies as optional outbound links, not a dependency.

- Wikidata provides an ATU code identifier property (P2540), which is useful for cross-linking, but it is not an authoritative SKOS scheme for ATU concepts.

Project knowledge graph remains self-contained and stable even if external URIs change or disappear.

### 4.2.FAIR strategy
1. Mint our own SKOS concept URIs for ATU types in our stable namespace.
<.../rdf/taleType/atu/707>.

2. Store the folktale type numbers as `skos:notation` and type titles as `skos:prefLabel`.

3. In the current export, ATU concepts are self-contained (no outbound mapping links are asserted); mapping links are a supported future enhancement:

- `skos:exactMatch` (strong equivalence),
- `skos:closeMatch` (near equivalence),
- `rdfs:seeAlso` (lightweight pointer),

The current export defines one concept scheme: `rft:ATU_Scheme` (ATU). Additional schemes (e.g., SUS or national type systems) are planned but not included in the present TTL exports.

- `rft:SUS_Scheme`  
  — Сoncept scheme for East Slavic SUS tale types.

- `rft:EE_Scheme`  
  — Сoncept scheme for Estonian national tale types.

### 4.3. Classifier alignment

The classifier produces a rft:ClassificationResult that references the same concept URIs via:

- `rft:primaryATU` (effective decision in the export),
- `rft:modelPrimaryATU` (model-only),
- `rft:finalATU` + `rft:finalDecisionSource` (model vs expert),

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
  (e.g., `ontoDM:probabilistic_predictive_model` typed as `ontoDM:OntoDM_000073` mapping)

**Key fields (exported / in meta):**
- `rft:modelTag` ← `meta.model_version`
- `rft:modelSha` ← `meta.model_sha`
- `rft:trainedAt` ← `meta.trained_at`
- `rft:task` ← `meta.task`
- `rft:textCols` ← `meta.text_cols`
- `dcterms:source` → bibliographic typing source (ATU reference)

**Training corpus pointer (meta):**
- `datasetUrl` — a stable publication pointer for the training dataset (currently a GitHub commit permalink; later may become a release asset/DOI).

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
  - `rft:decisionPolicyDownload` ← resolvable URL (raw GitHub)
  - `rft:labelsDownload` ← resolvable URL (raw GitHub)
  - `rft:primaryATU`, `rft:modelPrimaryATU`, `rft:finalATU`
  - `rft:finalDecisionSource`, `rft:finalExpertNote`

#### 4) InputTextSnapshot 

- **Stable text entity:** `rft:InputText` (`prov:Entity`) identified by `meta.tale_id`
- **Run snapshot:** `rft:InputTextSnapshot` (`prov:Entity`)
  - `prov:wasDerivedFrom` → `rft:InputText`
  - `rft:sha256` ← `meta.text_sha256` (hash of submitted text)

#### 5) DatasetSnapshot 

- **Types:** `prov:Entity`, `rft:DatasetSnapshot`
- **Identifier:** `meta.source_version` (e.g., `sha256:ea72…`)
- **Publication pointer:** `datasetUrl` (mapped to `rdfs:seeAlso`) ← `meta.dataset_url`  
  (points to the published training dataset version: commit permalink now; release asset later)

### 5.3 Human-in-the-loop handling

We record expert intervention only when the final decision is not the model:

- `rft:finalDecisionSource` is `"model"` by default.
- If expert overrides:
  - `rft:finalDecisionSource = "expert"`
  - `rft:finalATU`, `rft:finalExpertNote` are filled
  - optionally emit a separate provenance activity:
    - `rft:HumanReview a prov:Activity`
    - `prov:used` → the model result entity
    - optional `prov:wasAttributedTo prov:Agent` (expert)

---

## 6. Dataset-level modeling

The corpus is published as a versioned Dataset that contains many individual tale records.  
We use DCAT for distribution metadata and DCTERMS for citation, rights, and release description; run-level provenance is captured in the classifier JSON-LD exports.

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
- `dcterms:isPartOf` — link Tale ↔ Dataset
- `dcterms:source` — and `dcterms:bibliographicCitation` capture archival source references at Tale/Volume level; derivation links (`prov:wasDerivedFrom`) are used in the classifier export for run inputs (e.g., text snapshots).
- `dcterms:license`, `dcterms:accessRights` — rights and access constraints

This enables cross-release governance and “what changed between versions” practices.

### 6.3 Consistency with the classifier exports 

- **Dataset-level (DCAT):** the authoritative publication record for a corpus release and its downloadable distributions.
- **Classifier layer:**
  - `meta.dataset_uri` is a *publication pointer* to the training corpus package/version (commit permalink / release asset / DOI).
  - `meta.source_version` is a *checksum-style snapshot ID* recorded in `rft:DatasetSnapshot` to describe the inference-time snapshot.
  - A `rft:DatasetSnapshot` node may include `rdfs:seeAlso` (exported as `datasetUrl`) linking to the published dataset artifact that corresponds to that snapshot.

---

## 7. Datatype commitments

The knowledge graph explicitly commits key datatypes to ensure machine-actionability, validation, and consistent downstream querying.

**Classifier layer:**
- `rft:confidenceScore` → `xsd:decimal`
- `rft:deltaTop12` → `xsd:decimal`
- `rft:rank` → `xsd:integer`
- `prov:startedAtTime` → `xsd:dateTime` 
- `rft:trainedAt` → `xsd:dateTime`
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
