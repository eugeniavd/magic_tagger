# Ontology overview (preliminary, only for the Corpus A metadata)

> **Status:** This is a minimal, preliminary ontology overview for the folktale corpus index.  
> It currently covers only descriptive / bibliographic metadata.  
> In later stages, we will extend it with classes and relations for content analysis of tales  
> (Proppian functions, dramatis personae, motifs, moves, etc.), and align this module with  
> existing works such as ProppOnto / ProppOntology.  
> Our core working model for this pilot relies on DCTERMS, SKOS and PROV-O for simplicity;  
> CIDOC-CRM is used only as a light class-level alignment layer.  
> We also anticipate a richer CIDOC-CRM alignment and possibly an additional  
> web-facing profile (e.g. schema.org) at a later stage, when designing the content layer  
> and public JSON-LD exports.

> We also provide KG_sample.ttl as an RDF/Turtle export of the same minimal graph illustrated in JSON-LD_examples.json (tale  + its core metadata, genre, ATU type, persons, place, and recording event). 
> Validation: JSON-LD checked with JSON-LD Playground; Turtle checked with an RDF/Turtle validator.

This document gives a **minimal ontology mapping** for the folktale corpus:

- mapping of local entities and fields to:
  - Dublin Core Terms (DC/DCTERMS),
  - SKOS,
  - PROV-O and selected DCTERMS provenance-related elements,
  - light class-level alignment to CIDOC-CRM (e.g. recording events as `crm:E7_Activity`,  
    tales as instances of `crm:E33_Linguistic_Object` (a subclass of `crm:E73_Information_Object`),  
    persons as `crm:E21_Person`, places as `crm:E53_Place`, collections as `crm:E78_Curated_Holding`),
- a list of URI templates for core entities.

The goal is to keep a small, pragmatic layer that can later be extended (e.g. to detailed CIDOC-CRM event patterns and Propp-based narrative ontologies).

---

## 1. Core vocabularies and namespaces

We rely on the following namespaces:

- `dc:` / `dcterms:` — Dublin Core (elements and terms); we primarily use DCTERMS
- `skos:` — Simple Knowledge Organization System
- `prov:` — PROV-O (W3C Provenance Ontology)
- `crm:` — CIDOC-CRM (for class-level alignment of events, persons, places, collections)
- `rft:` — Russian Folktales vocabulary for project-specific classes and properties used in the corpus and knowledge graph

Suggested base namespace for project-specific terms:

- `rft`: <https://github.com/eugeniavd/magic_tagger/rdf/ontology/#>

---

## 2. Entity-level mapping

### 2.1 Main entities

| Local entity | Description | Working class & alignment |
|--------------|-------------|---------------------------|
| Tale | A single folktale text (one row in the index). | `rft:Tale` (working class), conceptually aligned with `crm:E33_Linguistic_Object` and `prov:Entity`. |
| Collection | Archival collection / series such as “ERA, Vene”, “RKM, Vene”, “TRÜ, VKK”. | `dcterms:Collection`, conceptually alignable to `crm:E78_Curated_Holding` |
| Volume | Physical volume within a collection (bound manuscript volume). | `dcterms:BibliographicResource` and `crm:E22_Man-Made_Object` (carrier) and/or `crm:E73_Information_Object` (content). |
| Narrator | Person who tells the tale. | `rft:Narrator` (working class), aligned with `crm:E21_Person` and `prov:Agent`. |
| Collector | Person who records the tale in the field. | `rft:Collector` (working class), aligned with `crm:E21_Person` and `prov:Agent`. |
| Place | Settlement / parish used in recording and origin fields. | `crm:E53_Place`. |
| Genre / Subgenre / Folklore category | Controlled vocabularies of genres and categories. | `rft:Genre` (working class), a subclass of `skos:Concept` within a `skos:ConceptScheme`. |
| Type code (ATU, SUS, national types) | Tale type codes and related classifications. | `rft:TaleType` (working class), a subclass of `skos:Concept` within one or more `skos:ConceptScheme` (ATU, SUS, national schemes). |
| Recording event (optional, for provenance) | The act of recording a tale by one or more collectors from a narrator at a given time and place. | `rft:RecordingEvent` (working class), aligned with `prov:Activity` and `crm:E7_Activity`. |

---

## 3. Field-to-property mapping (minimal)

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
| `collection` | Archival series (e.g. “ERA, Vene”, “RKM, Vene”, “TRÜ, VKK”). | `dcterms:isPartOf` → `dcterms:Collection` (alignable to `crm:E78_Curated_Holding`) | DCTERMS / CIDOC-CRM |
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


## 4. Genres and tale types as SKOS concepts

For genres and tale types we use **SKOS concept schemes** with two lightweight project classes:

- `rft:Genre` — subclass of `skos:Concept` for genres, subgenres and folklore categories.
- `rft:TaleType` — subclass of `skos:Concept` for ATU and national tale types.

Each concept is part of one or more `skos:ConceptScheme`:

- a genre scheme for archival genres, subgenres and folklore categories (e.g. `rft:GenreScheme`),
- separate tale type schemes for ATU and national classifications (e.g. `rft:ATU_Scheme`, `rft:SUS_Scheme`, `rft:EE_Scheme`).

Tales link to these concepts via:

- `rft:hasGenre`, `rft:hasSubgenre`, `rft:hasFolkloreCategory` → `rft:Genre`,
- **one generic property** `rft:hasTaleType` → `rft:TaleType` for all classification systems (ATU, SUS, etc.); the specific system is indicated by `skos:inScheme` on the `rft:TaleType` concept and the code by `skos:notation` (e.g. `"706"`, `"52"`, `"123A"`).


### 4.1 Concept schemes

We define at least three SKOS concept schemes:

- `rft:GenreScheme`  
  — SKOS concept scheme collecting genres, subgenres and folklore categories (ERA labels).

- `rft:ATU_Scheme`  
  — SKOS concept scheme for Aarne–Thompson–Uther tale types (ATU).

- `rft:SUS_Scheme`  
  — SKOS concept scheme for East Slavic SUS tale types.

Optionally, further schemes can be added, for example:

- `rft:EE_Scheme`  
  — SKOS concept scheme for Estonian national tale types.

Each individual genre is an instance of `rft:Genre` (a subclass of `skos:Concept`) in `rft:GenreScheme`.  
Each individual tale type is an instance of `rft:TaleType` (a subclass of `skos:Concept`) in one of the tale type schemes (`rft:ATU_Scheme`, `rft:SUS_Scheme`, `rft:EE_Scheme`, etc.), linked via `skos:inScheme` and carrying its code in `skos:notation`.


### 4.2 Core properties

We use the following object properties (all declared in `rft:`):

- `rft:hasGenre`  
  - **Domain:** `rft:Tale`  
  - **Range:** `rft:Genre` (subclass of `skos:Concept`)  
  - **Subproperty of:** `dcterms:type`  
  - Links a tale to one or more genre concepts (`genre_1`–`genre_3`).

- `rft:hasSubgenre`  
  - **Domain:** `rft:Tale`  
  - **Range:** `rft:Genre`  
  - **Subproperty of:** `rft:hasGenre`  
  - Used specifically for the `subgenre` field (e.g. `imemuinasjutt`).

- `rft:hasFolkloreCategory`  
  - **Domain:** `rft:Tale`  
  - **Range:** `rft:Genre`  
  - **Subproperty of:** `dcterms:type`  
  - Used for more fine-grained folklore categories.

- `rft:hasTaleType`  
  - **Domain:** `rft:Tale`  
  - **Range:** `rft:TaleType` (subclass of `skos:Concept`)  
  - **Subproperty of:** `dcterms:subject`  
  - General link from a tale to any tale type concept (ATU, SUS, national, etc.).  
    The specific classification system is indicated on the `rft:TaleType` concept via `skos:inScheme`
    (e.g. `rft:ATU_Scheme`, `rft:SUS_Scheme`, `rft:EE_Scheme`) and the code via `skos:notation`
    (e.g. `"706"`, `"52"`, `"123A"`).

Example SKOS concepts (informally):

- `rft:genre_muinasjutt` — `rft:Genre` / `skos:Concept` in `rft:GenreScheme`, `skos:prefLabel "muinasjutt"@et`.
- `rft:genre_imemuinasjutt` — narrower `rft:Genre` / `skos:Concept` with `skos:broader rft:genre_muinasjutt`.
- `rft:ATU_706` — `rft:TaleType` / `skos:Concept` in `rft:ATU_Scheme`, `skos:notation "706"`.
- `rft:SUS_1060_star` — `rft:TaleType` / `skos:Concept` in `rft:SUS_Scheme`, `skos:notation "1060*"`.

These concepts can be generated automatically from CSV vocabularies of genres and tale types.

---


## 5. Provenance (minimal pattern)

For minimal provenance we recommend the following pattern:

- Tale as `rft:Tale` (working class), aligned with `prov:Entity` and `crm:E33_Linguistic_Object`.
- Recording act as `rft:RecordingEvent` (working class), aligned with `prov:Activity` and `crm:E7_Activity`.
- Narrator and collectors as `rft:Narrator` / `rft:Collector`, aligned with `prov:Agent` and `crm:E21_Person`.

Key PROV relations:

- `rft:Tale prov:wasGeneratedBy rft:RecordingEvent`
- `rft:RecordingEvent prov:wasAssociatedWith rft:Collector`
- `rft:RecordingEvent prov:wasAssociatedWith rft:Narrator`

Optional CIDOC-CRM alignment (for a richer heritage-oriented model):

- `rft:RecordingEvent crm:P94_has_created rft:Tale`
- `rft:RecordingEvent crm:P14_carried_out_by rft:Collector` / `rft:Narrator`
- `rft:RecordingEvent crm:P7_took_place_at crm:E53_Place`
- time-span for the recording modelled as `crm:E52_Time-Span`, linked from `rft:RecordingEvent` via `crm:P4_has_time-span`.

Additionally, `dcterms:provenance` can be used on `rft:Tale` (or on a dataset-level resource) to store a human-readable note summarising how the tale entered the corpus (e.g. collection, volume, editor, processing steps).

This basic pattern can be implemented gradually: the pilot may start with simple links (`rft:narrator`, `rft:collector`, recording dates as literals on `rft:Tale`) and later refine them into explicit `rft:RecordingEvent` nodes with PROV and, where needed, CIDOC-CRM time-span entities.

---

## 6. URI templates

Ontology namespace (classes and properties):  
`rft: <https://github.com/eugeniavd/magic_tagger/rdf/ontology/#>`

For individual resources we use the base  
`https://github.com/eugeniavd/magic_tagger/rdf/`  
with the following URI patterns:

Tale:      <https://github.com/eugeniavd/magic_tagger/rdf/tale/{tale_id}>  
Collection:<https://github.com/eugeniavd/magic_tagger/rdf/collection/{collection_code}>  
Volume:    <https://github.com/eugeniavd/magic_tagger/rdf/volume/{collection_code}_{volume_no}>  
Person:    <https://github.com/eugeniavd/magic_tagger/rdf/person/{slug}>  
Place:     <https://github.com/eugeniavd/magic_tagger/rdf/place/{local_id}>  
Genre:     <https://github.com/eugeniavd/magic_tagger/rdf/genre/{id}>  
Tale type: <https://github.com/eugeniavd/magic_tagger/rdf/taleType/{scheme}/{code}>


---

## 7. Future extension

### 7.1 Tale-type evidence anchors

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


### 7.2 Propp-based narrative layer

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


