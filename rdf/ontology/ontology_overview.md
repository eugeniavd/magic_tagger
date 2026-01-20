
# Knowledge Model

> Validation: JSON-LD checked with JSON-LD Playground; Turtle checked with an RDF/Turtle validator.

This document defines the minimal, analysis-oriented knowledge model for the Unlocking Russian Folklore corpus and the classifier layer. The model is designed to support (a) faceted retrieval and (b) type-assignment decision support (Top-3 + anckor evidence + expert validation)

---

## 1. Core vocabularies and namespaces

### 1.1 Reused ontologies

- `dcterms:` — DCTERMS (descriptive metadata, source, rights, part-of relations).
- `skos:` — Simple Knowledge Organization System (controlled vocabularies (ATU types, genres/categories, optional keywords/motifs)
- `prov:` — PROV-O (W3C Provenance Ontology) for provenance of transformations, classifier runs, generated artifacts.
- `crm:` — CIDOC-CRM (for class-level alignment of events, persons, places, collections)
- `mexcore`, `mexalgo`, `mexperf:` MEX (structured provenance for ML experiments/models/measures)

### 1.2 Project namespace

- `rft:` — Russian Folktales vocabulary for project-specific classes and properties used in the corpus and knowledge graph_ only when no adequate term exists in the reused vocabularies (mainly folklore-specific glue + classifier-specific convenience properties)
- `rft`: <https://github.com/eugeniavd/magic_tagger/rdf/ontology/#>

Data base IRI:

BASE = <https://github.com/eugeniavd/magic_tagger/rdf/>

---

## 2. Entity-level mapping

### 2.1 Main entities and alignments

| Local entity | Description | Working class & alignment |
|--------------|-------------|---------------------------|
| Tale | A single folktale text (one row in the index). | `crm:E33_Linguistic_Object` and `prov:Entity`. |
| Collection | Archival collection / series such as “ERA, Vene”, “RKM, Vene”, “TRÜ, VKK”. | `dcmitype:Collection`, conceptually alignable to `crm:E78_Curated_Holding` |
| Volume | Physical volume within a collection (bound manuscript volume). | `dcterms:BibliographicResource` and `crm:E22_Man-Made_Object` (carrier) |
| Place | Settlement / parish used in recording and origin fields. | `crm:E53_Place`. |
| Type code (ATU, SUS, national types) | Tale type codes and related classifications. | `rft:TaleType` (working class), a subclass of `skos:Concept` within one or more `skos:ConceptScheme` (ATU, SUS, national schemes). |
| Recording event| The act of recording a tale by one or more collectors from a narrator at a given time and place. | `rft:RecordingEvent` (working class), aligned with `prov:Activity` and `crm:E7_Activity`. |

---

## 3. Field-to-property mapping 

This section shows how fields from `corpus_a_index` map to RDF properties. It is intentionally minimal; more detailed modelling (e.g. full CIDOC-CRM event patterns, narrative content) can be added later. In the section, each local index field is mapped to an RDF property (predicate).

- For simple descriptive metadata (format, rights, source, dates) we reuse existing
  properties from DCTERMS (e.g. `dcterms:format`, `dcterms:rights`).
- For project-specific relations between entities (e.g. tale → narrator, tale → genre,
  tale → tale type) we introduce `rft:` properties (e.g. `rft:narrator`, `rft:hasGenre`,
  `rft:hasATUType`), which are defined in the ontology with explicit domains and ranges
  and, where appropriate, declared as subproperties of DCTERMS or PROV relations.

### 3.1 Identification and source

**Domain:** Tale (`rft:Tale`, conceptually aligned with `crm:E33_Linguistic_Object` / `prov:Entity`)

| Local field | Description | RDF property | Target vocabulary |
|-------------|-------------|--------------|-------------------|
| `tale_id`   | Stable identifier within the corpus (used to build a persistent URI for the tale). | `@id` (via URI template), e.g. `https://github.com/eugeniavd/magic_tagger/rdf/data/tale/{tale_id}` | project / JSON-LD |
| `collection` | Archival series (e.g. “ERA, Vene”, “RKM, Vene”, “TRÜ, VKK”). | `dcterms:isPartOf` → `dcmitype:Collection` (alignable to `crm:E78_Curated_Holding`) | DCTERMS / CIDOC-CRM |
| `volume_no` | Volume number within a collection (bound manuscript volume). | `dcterms:isPartOf` → `rft:Volume` (`dcterms:BibliographicResource`, alignable to `crm:E22_Man-Made_Object`); the volume number itself can be recorded as `dcterms:identifier` on the volume resource. | DCTERMS / rft |
| `source_ref` | Full archival shelfmark string (as given in the index). | `dcterms:source` | DCTERMS |

---

### 3.2 Digital carrier and rights

**Domain:** Tale (`rft:Tale`)

| Local field       | Description                                      | RDF property                    | Target vocabulary |
|-------------------|--------------------------------------------------|---------------------------------|-------------------|
| `digital_carrier` | Digital carrier type (e.g. scan, transcript-only). Controlled list of values. | `dcterms:format`                | DCTERMS           |
| `rights_status`   | Access and reuse status (e.g. open, restricted with anonymisation). | `dcterms:accessRights`, `dcterms:rights` | DCTERMS           |

---

### 3.3 Agents: narrator and collectors

**Domain:** Tale (`rft:Tale`)  
**Related classes:** Narrator (`rft:Narrator`, aligned with `crm:E21_Person`), Collector (`rft:Collector`, aligned with `crm:E21_Person`)

| Local field           | Description                                                  | RDF property (on Tale) | Target vocabulary |
|-----------------------|--------------------------------------------------------------|------------------------|-------------------|
| `narrator`            | Narrator’s name and biographical note (composite field).    | `rft:narrator` → `rft:Narrator` | rft              |
| `collector_1`–`collector_5` | Collectors of the tale (up to five per tale).              | `rft:collector` → `rft:Collector` | rft (subproperty of DCTERMS creator/contributor) |

On the **Narrator / Collector** person nodes:

- name is recorded as `rdfs:label` (e.g. `"Paul Ariste"@et`);
- the composite biographical note (age, occupation, origin, religion, etc. as a single string at this stage) is recorded as `rdfs:comment`.

Notes:

- Many manuscripts were recorded by groups of fieldworkers, and a single volume may list up to five collectors; for this reason, we provide up to five separate collector fields in the index, all mapped to repeated uses of `rft:collector` in the graph.
- In later processing, the composite narrator field will be parsed into separate structured attributes (e.g. narrator_name, narrator_age, narrator_occupation, narrator_religion, narrator_origin) for use in the knowledge graph.

**Provenance pattern (optional):**

- Recording event is modelled as `rft:RecordingEvent` (`prov:Activity`, aligned with `crm:E7_Activity`).
  - Tale (`rft:Tale`, `prov:Entity`, `crm:E33_Linguistic_Object`)  
    `prov:wasGeneratedBy` / `crm:P94_has_created` → `rft:RecordingEvent`.
  - Narrator and collectors (`rft:Narrator`, `rft:Collector`, aligned with `crm:E21_Person`)  
    `prov:wasAssociatedWith` / `crm:P14_carried_out_by` → `rft:RecordingEvent`.

This provenance pattern is optional for the pilot and can be implemented incrementally, starting from the simple `rft:narrator` / `rft:collector` links on `rft:Tale`.

---

### 3.4 Institutions and organisations

**Domain:** Narrator (`rft:Narrator`, aligned with `crm:E21_Person`)  

| Local field        | Description                                           | RDF property              | Target vocabulary |
|--------------------|-------------------------------------------------------|---------------------------|-------------------|
| `narrator_school`  | School associated with the narrator (mainly for pupil collections). | `rft:affiliationLiteral` (simple literal on `rft:Narrator`) | rft |

- At this stage, we keep schools as plain literals attached to the narrator (e.g. `"Tartu Ülikooli Praktikakool"` as `rft:affiliationLiteral`).  
- In a later, richer model we may introduce explicit organisation entities (e.g. `rft:Organisation`, aligned with `crm:E74_Group`) and replace or complement the literal with an object property link from `rft:Narrator` to the organisation node.

---

### 3.5 Places and spatial information

**Domain:** Tale (`rft:Tale`), Narrator (`rft:Narrator`), Place (`crm:E53_Place`)

| Local field              | Description                                                        | RDF property / pattern                                  | Target vocabulary |
|--------------------------|--------------------------------------------------------------------|---------------------------------------------------------|-------------------|
| `recording_parish`       | Parish where the tale was recorded.                               | On Tale: `rft:recordingParish` → `crm:E53_Place`; on Place: `rdfs:label` in the original language. | rft / CIDOC-CRM / RDFS |
| `recording_place`        | Settlement of recording.                                | On Tale: `rft:recordingPlace` → `crm:E53_Place`; optionally, in a richer model, via the recording event as `crm:P7_took_place_at` from `rft:RecordingEvent` to `crm:E53_Place`. | rft / CIDOC-CRM |
| `narrator_origin_parish` | Parish of narrator’s origin.                                      | On Narrator: `rft:originParish` → `crm:E53_Place` (minimal model may store only the label as a literal). | rft / CIDOC-CRM |
| `narrator_origin_place`  | Settlement of narrator’s origin.                                  | On Narrator: `rft:originPlace` → `crm:E53_Place`; in the minimal model this can also be kept as a literal and later aligned to a place node. | rft / CIDOC-CRM |

Additional note:

- The place name is stored here in the original archival language; an English version of the parish/place name will be provided in a separate field for use in the knowledge graph and user interface. The English label supports interoperability with other datasets and tools.

---

### 3.6 Temporal information

**Domain:** Tale (`rft:Tale`, aligned with `crm:E33_Linguistic_Object`),  optionally Recording event (`rft:RecordingEvent`, aligned with `prov:Activity` / `crm:E7_Activity`)

| Local field           | Description                                   | RDF property / pattern                                                                 | Target vocabulary      |
|-----------------------|-----------------------------------------------|----------------------------------------------------------------------------------------|------------------------|
| `recorded_date_start` | Start date of recording (as given in the index). | Minimal model: on Tale, `dcterms:created`. Optional richer model: on `rft:RecordingEvent`, `prov:startedAtTime`, later alignable to a `crm:P4_has_time-span` / `crm:E52_Time-Span` pattern. | DCTERMS / PROV / CIDOC-CRM |
| `recorded_date_end`   | End date of recording (if given).            | Optional, when `rft:RecordingEvent` is used: `prov:endedAtTime`, later alignable to a `crm:P4_has_time-span` / `crm:E52_Time-Span` pattern. For single-day recordings, Tale can simply have `dcterms:created`. | PROV / CIDOC-CRM       |

- In the current index, dates are stored in a US-style string format such as `5/24/1930` (`M/D/YYYY`).  For RDF exports, these values will be normalised to ISO literals (e.g. `"1930-05-24"^^xsd:date`).  
- A separate “raw” date field can be retained if needed to preserve the original archival notation.

---

### 3.7 Content and classification (overview)

**Domain:** Tale (`rft:Tale`); classification concepts (`rft:Genre`, `rft:TaleType` as subclasses of `skos:Concept`)

| Local field              | Description                                         | RDF property / pattern                                                                 | Target vocabulary |
|--------------------------|-----------------------------------------------------|----------------------------------------------------------------------------------------|-------------------|
| `content_description`    | Short content note / archival title.               | On Tale: `dcterms:description`.                                                        | DCTERMS           |
| `genre_1`–`genre_3`      | Archival genres.                                   | On Tale: `rft:hasGenre` / `rft:hasSubgenre` / `rft:hasFolkloreCategory` → `rft:Genre` (`skos:Concept`) in a genre concept scheme. | SKOS / rft        |
| `subgenre`               | Subgenre (e.g. `imemuinasjutt`).                   | On Tale: `rft:hasSubgenre` → `rft:Genre` (`skos:Concept`); on the concept: `skos:broader` to the main genre concept. | SKOS / rft        |
| `folklore_category`      | Fine-grained category.                             | On Tale: `rft:hasFolkloreCategory` → `rft:Genre` (`skos:Concept`); further relations in SKOS (e.g. `skos:broader`, `skos:related`). | SKOS / rft        |
| `type_code_1`–`type_code_4` | ATU, SUS, national types, etc. | On Tale: `rft:hasTaleType` → `rft:TaleType` (`skos:Concept`) in one or more `skos:ConceptScheme` (ATU, SUS, national schemes). | SKOS / rft |

Additional note:

- The content description is kept in the original archival language; where needed, an English translation or summary will be provided in separate fields to support interoperability with other datasets and tools.  
- Each tale type is a `rft:TaleType` (`skos:Concept`) linked to a specific classification system via `skos:inScheme` (e.g. `rft:ATU_Scheme`, `rft:SUS_Scheme`, `rft:EE_Scheme`) and carries its code in `skos:notation` (e.g. `"706"`, `"52"`, `"123A"`). The property `rft:hasTaleType` is used uniformly for all systems.

---


## 4. Tale types as SKOS concepts

Canonical statement in the published KG:

`dcterms:` - subject → `skos:Concept`(the type concept)

So:
<tale/X> dcterms:subject <taleType/atu/707> .


### 4.1 Concept schemes

There is no universally accepted official open URI set distributed by the rights holders of ATU (the index is a published reference work; current editions are commercial / controlled). The Folklore Fellows description confirms the ATU system as an infrastructure, but not as an open URI authority.

There are web-published controlled vocabularies (e.g., TemaTres instances) that provide a vocabulary URI, such as the TemaTres “ATU classification” instance. However, availability/terms dereferencing can be inconsistent, so we treat them as linkable references, not the core dependency.

Wikidata supports an identifier property for works to store ATU codes (P2540). This is useful for cross-linking works, but it is not an authoritative SKOS concept scheme for ATU types.

### 4.2.FAIR strategy
1. Mint our own SKOS concept URIs for ATU types in our stable namespace.

2. Store the code as `skos:notation` and label(s) as `skos:prefLabel`.

3. Link outward opportunistically using `skos:exactMatch` when stable targets exist (Wikidata item about the tale type, a stable vocabulary entry, etc.). 

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

## 5. Agents and Recording Context 

This section defines how we model **narrators** and **collectors** as agents in a way that:
- preserves the narrators’ strong influence on content/variants,
- captures collectors’ influence on **text quality / handwriting / HTR**,
- reflects the fact that **recording time is available at the volume level**, not per tale,
- stays **portable across traditions** (other peoples’ folktales) and reuse-first (PROV-O + light CIDOC).

### 1) Core principle

We always mint stable agent URIs for persons and keep roles contextual (a person may be a narrator in one record and a collector in another).  

### 2) Canonical agent entity

Each agent is represented as a person node:

- **Types:** `prov:Agent`, optionally also `crm:E21_Person`
- **Label:** `rdfs:label "Full Name"`
- **Optional note:** `rdfs:comment` for biographical free text (age/occupation/origin as recorded)

**URI template**
- `BASE + "person/{person_id}"` (preferred)
- fallback: `BASE + "person/{slug}"` (deterministic, collision-safe)

### 3) Role linking policy

Because narrators are central for content variation, and collectors affect capture/legibility, we use two layers:

#### 3.1 Tale-level content attribution (narrator, always on Tale)
Narrator is asserted directly on the Tale to support variant and content analysis.

- `Tale dcterms:contributor NarratorAgent .`

Rationale: `dcterms:contributor` is widely understood and allows cross-corpus reuse.  
If multiple narrators exist, repeat the statement.

#### 3.2 Volume-level capture attribution (collectors, on Volume)
Because recording time is known per volume, and collectors affect handwriting/capture conditions, we treat collectors as part of the volume capture context.

- `Volume dcterms:creator CollectorAgent.` 

This expresses: “these agents are responsible for the creation/recording of this volume’s content”.

### 4) Time modeling (volume-level)

Because dates exist at the volume level, we model time there as the canonical record:

- `Volume dcterms:created "YYYY-MM-DD"^^xsd:date`  
  or, if you truly have ranges:
- `Volume dcterms:temporal "YYYY–YYYY"` (literal)  
  and/or an optional `crm:E52_Time-Span` later.

Tales can be dated indirectly via:
- `Tale dcterms:isPartOf Volume .`

This preserves truthfulness to the source and supports time-based analysis at the appropriate granularity.

### 5) Place modeling 

If place is known per tale: attach it to the Tale.
- `Tale dcterms:spatial Place .`

If place is only known at volume level: attach it to the Volume.
- `Volume dcterms:spatial Place .`

### 6) Linking structure (minimal published graph)

- `Tale dcterms:isPartOf Volume .`
- `Tale dcterms:contributor NarratorAgent .`   *(content influence)*
- `Volume dcterms:creator CollectorAgent .`    *(capture / handwriting influence)*
- `Volume dcterms:created …`                   *(time at volume level)*

This is the minimal, portable structure that supports:
- “variants by narrator”
- “top narrators / narrator-based clustering”
- “collector effects on OCR/HTR quality” (via volume association)
- “temporal analysis by volume decade/period”

### 7) Quality signals linked to collectors (handwriting / OCR-HTR)

To operationalize the collector effect on recognition quality:

- attach quality metrics to the **text-bearing artifact** (page / transcription / volume-level text object),
  then aggregate by collector via `Volume dcterms:creator`.

This yields a defensible KM claim:
> collectors influence capture modality/handwriting, which correlates with recognition quality and downstream extraction reliability.

## 6. Classifier / decision-support layer 

Our goal is to make the “knowledge management” auditable and reproducible: every suggestion is tied to a specific input snapshot, model version, and execution timestamp.

### 6.1 Ontologies used

- **PROV-O**: workflow provenance (`prov:used`, `prov:wasGeneratedBy`, `prov:generatedAtTime`, etc.)
- **MEX**: machine-learning experiment/execution/model/performance structure
- **`rft:`** is used only where reuse-first vocabularies do not provide adequate terms:
  - expert governance fields (final decision, decision source, timestamps, uncertainty signals)
  - compact candidate/evidence structures 

### 6.2 Minimal mapping

#### 1) ClassificationEvent 

- **Types:** `prov:Activity`, `crm:E7_Activity`
- **MEX typing:** `mexcore:Execution` 

**Key links:**
- `prov:used` → `InputText`
- `prov:used` (or `rft:usedModel`) → `mexcore:Model`
- `prov:generated` → `ClassificationResult`
- `prov:generatedAtTime` → `xsd:dateTime`

#### 2) Model

- **Types:** `mexcore:Model`, `prov:Entity`

**Recommended fields:**
- model identifier (SHA/tag)
- `rft:trainedAt` (`xsd:dateTime`)
- `rft:task` (string)
- `rft:textCols` / feature description (string/list)

(Optionally, later we may add the MEX Algorithm layer for learning method, parameters, implementation.)

#### 3) ClassificationResult

- **Types:** `prov:Entity`
- **MEX typing (light):** `mexperf:ExecutionPerformance`  

**Key links:**
- `prov:wasGeneratedBy` → `ClassificationEvent`
- `rft:forTale` → `Tale`
- `rft:hasCandidate` → Top-3 candidates (ranked)

#### 4) Candidates + Evidence

We keep a compact structure consistent with the current export:

- `rft:ClassificationCandidate`
  - `rft:predictedTaleType` → type concept URI (`skos:Concept` in ATU/SUS scheme)
  - `rft:confidenceScore` → `xsd:decimal`
  - `rft:rank` → `xsd:integer`
  - `rft:hasEvidence` → `rft:Evidence`

- `rft:Evidence`
  - snippet text(s) / anchor(s)
  - optional offsets or page references (future)

### 6.3 Human-in-the-loop fields 

These fields capture the expert resolution and are treated as first-class governance metadata:

- `rft:primaryATU` — current stored label in the corpus record
- `rft:modelPrimaryATU` — model Top-1
- `rft:finalATU` — final label after HITL (may equal primary or model)
- `rft:finalDecisionSource` — controlled enum (e.g., `expert` | `model` | `rule`)
- `rft:finalSavedAt` — `xsd:dateTime`
- `rft:deltaTop12` — `xsd:decimal` (margin between top-1 and top-2; uncertainty signal)
- `rft:taleStatus` — controlled status (e.g., `model_suggested`, `expert_override`, `expert_confirmed`, `needs_review`)
- optional: `rft:finalExpertNote` — short textual justification

These governance fields are a key Knowledge Management contribution: they encode not only what was assigned, but how and under which confidence and decision regime the assignment became “knowledge”.

---

## 7. Provenance 

For minimal provenance we recommend a reuse-first pattern based on **PROV-O** (with optional light CIDOC-CRM alignment). The key design constraint in this corpus is that recording time is available at the volume level, not reliably per tale. Therefore, provenance is modeled with a two-level context:

- **Tale-level** provenance for *content attribution* (narrator impact on variants/content).
- **Volume-level** provenance for *capture context* (collectors + recording period impacting handwriting/recognition quality).

### 7.1 Core typing 

- **Tale**
  - `a crm:E33_Linguistic_Object`
  - also `a prov:Entity` (provenance interoperability)

- **Volume**
  - `a dcterms:BibliographicResource`
  - optionally also `a prov:Entity` (when needed for pipeline provenance)

- **Agent (Narrator / Collector)**
  - `a prov:Agent`
  - optionally also `a crm:E21_Person`

- **Recording activity**
  - `a prov:Activity`
  - optionally also `a crm:E7_Activity`

### 7.2 Minimal provenance relations

Because dates are volume-level, the approach uses direct links and avoids inventing per-tale recording events.

**Structural containment**
- `Tale dcterms:isPartOf Volume`

**Content attribution (narrator; on Tale)**
- `Tale dcterms:contributor NarratorAgent`
  - (repeatable; supports “variants by narrator” analyses)

**Capture attribution (collectors; on Volume)**
- `Volume dcterms:creator CollectorAgent`
  - (repeatable; supports “collector effects on HTR/OCR quality” via volume association)

**Recording time (volume-level)**
- `Volume dcterms:created "YYYY-MM-DD"^^xsd:date`
  - if only a period is known, use a controlled literal and/or later introduce a time-span node.

**Recording place (where available)**
- If place is known per tale:
  - `Tale dcterms:spatial Place`
- If place is only known per volume:
  - `Volume dcterms:spatial Place`

This policy stays faithful to the source granularity and remains portable across corpora.

### 7.3 Optional CIDOC-CRM alignment 

When an explicit recording activity is present, we may align it to CIDOC-CRM:

- `RecordingActivity crm:P94_has_created Tale`
- `RecordingActivity crm:P14_carried_out_by CollectorAgent`
- (optionally also associate the narrator if your interpretation treats narration as “carrying out” the event)
- `RecordingActivity crm:P7_took_place_at Place` (`crm:E53_Place`)
- time-span as `crm:E52_Time-Span`, linked via `crm:P4_has_time-span`

### 7.4 Human-readable provenance notes 

Additionally, we attach a compact provenance note either:

- on the **Tale**: `dcterms:provenance "..."`, or
- on a **dataset-level** resource describing a release/pipeline

This approach keeps the published knowledge graph simple and reusable, while preserving a clear upgrade path to richer event modeling and stronger causal analyses (e.g., collector–handwriting–recognition quality; narrator–variant content).

---

## 8. URI scheme

### 8.1 General rules

1. **Base IRI**
   - `BASE = https://github.com/eugeniavd/magic_tagger/rdf/`

2. **Stable identifiers**
   - Prefer existing internal IDs (`tale_id`, `volume_id`, etc.) unchanged.
   - Avoid using free-text labels as identifiers.

3. **Run timestamp formatting (path-safe)**
   - Input timestamp example: `2026-01-15T19:27:09Z`
   - Path-safe form: `2026-01-15T19-27-09Z` (replace `:` with `-`)

4. **Slug rules (only when no authority ID exists)**
   - Use deterministic slugging for person/place fallback:
     - lowercase
     - ASCII transliteration where needed
     - spaces → `-` (or `_`, but be consistent)
     - remove punctuation
     - collapse multiple separators
   - If collisions are possible: append a short hash suffix.


### 8.2 Canonical URI templates

#### Corpus entities

- **Tale**  
  `BASE + "tale/{tale_id}"`

- **Collection**  
  `BASE + "collection/{collection_code}"`

- **Volume**  
  `BASE + "volume/{volume_id}"`  

- **Person**  
  Preferred: `BASE + "person/{person_id}"`  
  Fallback:  `BASE + "person/{slug}"`

- **Place**  
  Preferred: `BASE + "place/{place_id}"`  
  Fallback:  `BASE + "place/{slug}"`

- **Tale type concept (ATU)**  
  `BASE + "taleType/atu/{code}"`

- **Tale type concept (other schemes)**  
  `BASE + "taleType/sus/{code}"` (and analogous patterns for other schemes)

#### Classifier layer

- **Classification event (run activity)**  
  `BASE + "classificationEvent/{tale_id}/{run_ts}"`

- **Classification result (run output entity)**  
  `BASE + "classificationResult/{tale_id}/{run_ts}"`

- **Input text snapshot used for the run**  
  `BASE + "inputText/{tale_id}/{run_ts}"`

- **Model artifact**  
  `BASE + "model/{model_sha}"`

---

#### Bibliographic reference nodes

- **Bibliographic reference**  
  `BASE + "biblio/{id}"`  
  Example: `BASE + "biblio/ffc_284-286_2011_uther"`

---

## 9. Datatype commitments 

The knowledge graph explicitly commits key datatypes to ensure machine-actionability, validation, and consistent downstream querying.

### 9.1 Required datatype mappings

- `rft:confidenceScore` → `xsd:decimal`
- `rft:deltaTop12` → `xsd:decimal`
- `rft:rank` → `xsd:integer`
- `prov:generatedAtTime` → `xsd:dateTime`
- `rft:trainedAt` → `xsd:dateTime`
- `rft:finalSavedAt` → `xsd:dateTime`
- `dcterms:created` → `xsd:date`  
- `skos:notation` → plain string  
  *(codes may contain letters and special symbols such as `*`)*

### 9.2 Implementation note

- These commitments should be enforced both in:
  - the JSON-LD `@context` (via `{"@type": "xsd:..."}` where appropriate), and
  - SHACL shapes (via `sh:datatype` constraints).

---

## 10. Dataset-level modeling

The corpus is published as a versioned Dataset that contains many individual tale records.  
We use **DCAT** for dataset/distribution metadata and **DCTERMS/PROV** for provenance and governance notes.

### 10.1 Rationale

- A **Dataset node** represents a specific *release* of the corpus (e.g., `v1`, `v2`), with stable citation metadata (title, license, publisher, issued date).
- **Tales are not modeled as “rows in a table”**. They are first-class resources linked to the dataset via part–whole relations.
- The dataset points to **distributions** (TTL/JSON-LD exports, SHACL shapes, expected outputs), making the release machine-actionable and reproducible.

### 10.2 Canonical pattern

- `dcat:Dataset` — the corpus release
- `dcat:Distribution` — concrete downloadable artifacts for the release (exports + validation assets)
- `dcterms:hasPart` / `dcterms:isPartOf` — link Dataset ↔ Tale resources
- `prov:wasDerivedFrom` + `dcterms:source` — capture source references and derivations
- `dcterms:license`, `dcterms:rights`, `dcterms:accessRights` — rights and access constraints

### 10.3 Dataset ↔ Tale policy

- Each tale record is linked to the dataset:
  - `Tale dcterms:isPartOf Dataset`
  - (optionally also) `Dataset dcterms:hasPart Tale`

This enables cross-release governance and “what changed between versions” practices.

---

подчистить потом 
## 11. Future extension

### 11.1 Tale-type evidence anchors

In addition to storing tale types (`rft:hasTaleType` → `rft:TaleType`), we plan to model type assignment decisions and their textual anchors:

- `rft:TypingDecision` — an entity representing the assignment of one tale type to one tale  
  (who assigned it, when, by which method).
- `rft:TypeAnchor` — an entity representing the textual or structural evidence used to justify  
  a given tale-type assignment (e.g. a key episode, motif, or Proppian function).

Illustrative pattern:

- `rft:TypingDecision`  
  - links to a tale (`rft:forTale` → `rft:Tale`),  
  - links to a tale type (`rft:assignedType` → `rft:TaleType`),  
  - is aligned with `prov:Entity` and connected to the annotation activity via PROV.

- `rft:TypeAnchor`  
  - links to a typing decision (`rft:anchorForDecision`),  
  - points to the relevant tale (`rft:anchorInTale`),  
  - may carry a short quote (`rft:anchorQuote`) and, optionally, character offsets  
    (`rft:anchorOffsetStart` / `rft:anchorOffsetEnd`),  
  - can later be linked to Proppian functions or motif vocabularies.

This layer is not implemented in the minimal index mapping, but it keeps room for explicit type evidence at the level of individual tales.


### 11.2 Propp-based narrative layer

In a later module we plan to integrate content-level analysis of tales based on Propp’s morphology, using or aligning to ProppOnto / ProppOntology:

- **Proppian functions** as an ontology of plot functions (preparation, complication, struggle, etc.).
- **Dramatis personae** (hero, villain, donor, helper, princess, dispatcher, false hero, etc.) and their relations to functions and narrative segments.

For MagicTagger, this would mean:

- adding `rft:ProppFunction` and `rft:DramatisPersona` classes aligned to ProppOntology classes  
  (via `rdfs:subClassOf` and/or `owl:equivalentClass`);
- introducing project-specific classes for **narrative characters** (e.g. `rft:NarrativeCharacter`)  
  aligned with `crm:E21_Person` to represent persons in narrative roles;
- linking functions to:
  - the **tale** (`rft:Tale`, aligned with `crm:E33_Linguistic_Object`) as a whole,
  - optionally, **text segments** (span-level entities, if we decide to model them),
  - **narrative characters** (instances of `rft:NarrativeCharacter`) that realise Proppian roles.

This Propp-based narrative layer is out of scope for the minimal index mapping described in this document, but we anticipate it here so that namespaces, URI patterns and core class choices remain compatible with a future content-level module.


