
# Knowledge Model

This document defines the minimal, analysis-oriented knowledge model for the Unlocking Russian Folklore corpus and the classifier layer. The model is designed to support (a) faceted retrieval and (b) type-assignment decision support (Top-3 + expert validation)

## 1. Core vocabularies and namespaces

### 1.1 Reused ontologies

- `dcterms:` — DCTERMS (descriptive metadata: identifiers, descriptions, rights/access rights, citations, and part–whole containment via `dcterms:isPartOf`, plus `dcterms:subject` links to ATU concepts).
- `skos:` — SKOS (controlled vocabulary for ATU types: `skos:Concept`, `skos:inScheme`, `skos:notation`, `skos:prefLabel`).
- `prov:` — PROV-O (used for attribution as explicit provenance statements: `prov:qualifiedAttribution` / `prov:Attribution` with `prov:agent` and `prov:hadRole`; also used for lightweight derivation links such as `prov:wasDerivedFrom`).
- `locrel:` — Library of Congress MARC Relators (role URIs such as `locrel:nrt` and `locrel:col`, used as values of `prov:hadRole`).
- `crm:` — CIDOC-CRM (class-level alignment for core entities in the corpus: tales as `crm:E33_Linguistic_Object`, places as `crm:E53_Place`; event-level modelling is an optional extension).
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
| **TaleRecording** | A single archival folktale text record; the recorded textual item used for retrieval and corpus navigation. | `rft:TaleRecording`, aligned to `crm:E33_Linguistic_Object`. |
| **TaleContent** | The abstract tale content separated from the archival text record; this is the node that carries typological assignment. | `rft:TaleContent`, aligned to `crm:E28_Conceptual_Object`. |
| **Collection** | Archival collection / series such as “ERA, Vene”, “RKM, Vene”, “TRÜ, VKK”. | `dcmitype:Collection`; conceptually alignable to `crm:E78_Curated_Holding`. |
| **Volume** | Physical / archival volume within a collection; the immediate container for tale recordings. | `dcterms:BibliographicResource`; optionally alignable to `crm:E22_Man-Made_Object` as a future extension. |
| **Place** | Settlement / parish used in recording-location metadata. | `crm:E53_Place`. |
| **ATU concept / Type code** | Tale type concepts and their controlled identifiers; ATU codes are stored as notations on concept nodes and linked from tale content. | `rft:TaleType`, aligned to `skos:Concept`, within `rft:ATU_Scheme` (`skos:ConceptScheme`); codes stored via `skos:notation`. |
| **Person / Agent** | Human actors represented as stable authority nodes; narrators and collectors are not modeled as subclasses but as role-bearing attributions. | `prov:Agent`, also typed as `foaf:Person`; optional person-specific metadata may include `schema:birthDate` and `rft:ageAtRecording`. |
| **Attribution** | Reified role statement linking a person to a tale recording with an explicit role URI. | `prov:Attribution`; uses `prov:agent` and `prov:hadRole` with LoC relators such as `locrel:nrt` and `locrel:col`. |
| **Recording event** | Not part of the baseline export; can be introduced later if explicit event-level modeling is needed. | Optional extension as `prov:Activity`, alignable to `crm:E7_Activity`. |

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
- For provenance and attribution statements, used PROV-O (in the corpus graph: qualified attribution via `prov:qualifiedAttribution` / `prov:Attribution` with `prov:agent` and `prov:hadRole`; run-level provenance such as `prov:used` / `prov:wasGeneratedBy` appears in classifier export).
- Introduce `rft:` properties **only** when there is no adequate reusable predicate, and keep them lightweight and stable.

### 3.1 Identification and source (corpus index)

**Domain:** TaleRecording (`rft:TaleRecording`, aligned with `crm:E33_Linguistic_Object`)

> Note: 
> `rft:TaleRecording` is linked to `rft:TaleContent` via `prov:wasDerivedFrom`, and ATU concepts are linked from `rft:TaleContent` via `dcterms:subject`.

| Local field | Description | RDF property | Target vocabulary |
|-------------|-------------|--------------|-------------------|
| `tale_id` | Stable identifier within the corpus (used to mint the TaleRecording IRI). | `@id` (URI template), e.g. `https://eugeniavd.github.io/magic_tagger/rdf/TaleRecording/{tale_id}`; also `dcterms:identifier` on the recording node | project / JSON-LD + DCTERMS |
| `collection` | Archival series (e.g., “ERA, Vene”, “RKM, Vene”, “TRÜ, VKK”). | not attached directly to TaleRecording; represented through `TaleRecording dcterms:isPartOf Volume` and `Volume dcterms:isPartOf Collection` | DCTERMS (+ optional CRM alignment) |
| `volume_no` | Volume number within a collection (bound manuscript volume / archival unit). | represented through `TaleRecording dcterms:isPartOf → Volume`; on the Volume node store the stable volume key in `dcterms:identifier` and optionally a human-readable `rdfs:label` such as “ERA, Vene 2” | DCTERMS / RDFS |
| `source_ref` | Full archival shelfmark string for a folktale text (as given in the index). | `dcterms:bibliographicCitation` (literal) on `rft:TaleRecording` | DCTERMS |


### 3.2 Access rights

**Domain:** TaleRecording (`rft:TaleRecording`)

| Local field | Description | RDF property | Target vocabulary |
|---|---|---|---|
| `rights_status` | Access and reuse status of the archival text record (e.g., open; partly anonymised). In the current profile, values are mapped to controlled rights individuals rather than kept as free strings. | `dcterms:accessRights` → `rft:rights_open` / `rft:rights_partly_anonymised` | DCTERMS + project ontology |


### 3.3 Agents: narrators and collectors

This section models human agents in the archival corpus (narrators, collectors).  
**Note:** classifier-related humans (e.g., a folklore expert who overrides a prediction) are handled separately under **Classifier provenance** (expert review as `prov:Activity` + optional `prov:wasAttributedTo prov:Agent`). Archival roles are therefore kept separate from annotation roles.

- **Person (Agent):** `prov:Agent`, also typed as `foaf:Person`
- **Display name:** `rdfs:label`
- **Biographical note:** `rdfs:comment`
- **Optional person metadata:** `schema:birthDate`, `rft:ageAtRecording`

#### Role principle 

- We mint stable **Person** URIs and keep roles **contextual**, expressed through qualified attribution statements.
- In the current model, both narrators and collectors are linked to a specific **TaleRecording**, not modeled as subclasses of Person and not attached through dedicated local predicates.
- The distinction between archival text and abstract content is maintained elsewhere in the model: `rft:TaleRecording` is linked to `rft:TaleContent` via `prov:wasDerivedFrom`.

**URI policy**
- Preferred: `BASE_DATA + "/person/{person_id}"` (stable internal ID).

#### Role links 

Roles are represented through explicit `prov:Attribution` nodes so that the agent and the role value remain queryable and extensible. In the current export, recording date is stored at the **TaleRecording** level as `dcterms:created`, and may be serialized as `xsd:date`, `xsd:gYearMonth`, or `xsd:gYear` depending on source precision.

| Context | Domain | Property pattern | Range | Meaning |
|---|---|---|---|---|
| **Recording-level narrator attribution** | `rft:TaleRecording` | `prov:qualifiedAttribution` → `prov:Attribution` with `prov:agent Person` and `prov:hadRole locrel:nrt` | Person | Narrator attribution |
| **Recording-level collector attribution** | `rft:TaleRecording` | `prov:qualifiedAttribution` → `prov:Attribution` with `prov:agent Person` and `prov:hadRole locrel:col` | Person | Collector attribution |
| **Volume-level creator link** | Volume | `dcterms:creator` | Person | Volume-level creator / collector reference |
| **Recording → Volume containment** | `rft:TaleRecording` | `dcterms:isPartOf` | Volume | Recording belongs to a volume (archival container) |

**Notes**
- Multiple narrators or collectors are represented as repeated `prov:qualifiedAttribution` statements on the same `rft:TaleRecording`, each with its own `prov:Attribution` node.
- In PROV-O we use both an unqualified shortcut and a qualified attribution node. `prov:wasAttributedTo` provides a direct, query-friendly link from the `rft:TaleRecording` to the agent, while `prov:qualifiedAttribution` points to an explicit `prov:Attribution` resource that carries the contextual role URI (e.g., `locrel:nrt` or `locrel:col`).
- At the volume level, collectors may additionally be recorded through `dcterms:creator` for simpler bibliographic access patterns.

#### Mapping from local index fields

| Local field | Description | RDF mapping | Comment |
|---|---|---|---|
| `narrator_person_id` (+ narrator label/note fields) | Narrator authority id + optional display fields | `TaleRecording prov:qualifiedAttribution [ a prov:Attribution ; prov:agent Person ; prov:hadRole locrel:nrt ]`; `Person rdfs:label` + optional `rdfs:comment` | Repeat attribution if multiple narrators occur |
| `collector_person_ids(_str)` | Collectors associated with the archival recording / volume context | `TaleRecording prov:qualifiedAttribution [ a prov:Attribution ; prov:agent Person ; prov:hadRole locrel:col ]`; optionally also `Volume dcterms:creator Person` | Repeat attribution if multiple collectors occur |
| `recorded_date_start` | Recording date | `TaleRecording dcterms:created` | Datatype may be `xsd:date`, `xsd:gYearMonth`, or `xsd:gYear` depending on source precision |


### 3.4 Institutions and organisations

This section covers institutional affiliations.  
The baseline profile remains lightweight and does not introduce role-specific agent subclasses.

**Domain:** Person (`prov:Agent`, also typed as `foaf:Person`) referenced through recording-level qualified attribution on `rft:TaleRecording` (`prov:qualifiedAttribution` → `prov:Attribution` with `prov:agent` and `prov:hadRole`, e.g. `locrel:nrt` for narrators or `locrel:col` for collectors).

**Future upgrade**
- We could introduce an **Organisation** node :
  - Organisation: `crm:E74_Group` (and optionally `prov:Agent`)
  - Link: `dcterms:relation` (or `crm:P107_has_current_or_former_member`)
- Then we could keep the literal as the raw label for traceability and add the organisation IRI for structured linking.


### 3.5 Places and spatial information

We model places primarily as `crm:E53_Place` nodes with human-readable labels and keep the linking pattern lightweight at the baseline level.

**Domains:**  
- **TaleRecording:** `rft:TaleRecording` (aligned with `crm:E33_Linguistic_Object`)  
- **Person:** `prov:Agent`, also typed as `foaf:Person`  
- **Place:** `crm:E53_Place`

#### Baseline linking: TaleRecording ↔ Place

| Local field | Description | RDF property / pattern | Target vocabulary |
|---|---|---|---|
| `recording_place` | Settlement of recording. | `TaleRecording dcterms:spatial Place` | DCTERMS / CIDOC CRM |
| `recording_parish` | Parish associated with the recording location. | included in the same baseline place representation, currently serialized through the place label | DCTERMS / CIDOC CRM |

**Place node**
- Type: `crm:E53_Place`
- Label(s): `rdfs:label` as a human-readable string; in the current export this may combine an English normalization with the original place form.
- Optional additional labels: `skos:prefLabel` / `skos:altLabel` may be added later if place authority control is expanded.

#### Current baseline note

In the present export, spatial information is attached at the **TaleRecording** level through `dcterms:spatial`.  
The linked place node is intentionally lightweight and currently serves as a minimal place representation rather than a full place authority record.

#### Richer model

To distinguish **recording place** from other spatial dimensions more explicitly, a future extension may introduce a recording event:

- `rft:RecordingEvent a prov:Activity`
- `TaleRecording prov:wasGeneratedBy rft:RecordingEvent`
- `rft:RecordingEvent crm:P7_took_place_at Place`
- `rft:RecordingEvent prov:wasAssociatedWith Person`

This keeps the baseline simple while preserving an upgrade path toward fuller CIDOC CRM style event modeling.


### 3.6 Temporal information

**Domains:**  
- **TaleRecording** (baseline archival time anchor): `rft:TaleRecording`, aligned with `crm:E33_Linguistic_Object`  
- **Classifier run** (system-produced time axis): `rft:ClassificationRun`, aligned with `prov:Activity`

This project distinguishes **two time axes**:

1. **Fieldwork / recording time** — archival metadata attached to the recorded folktale text. In the current realization, this is stored on the **TaleRecording** node via `dcterms:created`.  
2. **Computation time** — system provenance for classifier execution, represented separately through PROV activity timestamps such as `prov:startedAtTime` / `prov:endedAtTime`. :contentReference[oaicite:0]{index=0}

**Baseline**

| Local field | Description | RDF property / pattern | Target vocabulary |
|---|---|---|---|
| `recorded_date_start` | Earliest recording date recorded in the archival index. | `TaleRecording dcterms:created` | DCTERMS |
| `recorded_date_end` | Latest recording date for a multi-day recording period. | not currently exported in the baseline graph; retained in the source table for possible future extension | — |

**Notes**
- `recorded_date_start` / `recorded_date_end` refer to the **recording period**, not digitisation or processing time. 
- Full dates use ISO `YYYY-MM-DD`.
- Partial dates use `YYYY-MM` or `YYYY` when only month-level or year-level precision is known.
- In the current RDF realization, `dcterms:created` may therefore be serialized as `xsd:date`, `xsd:gYearMonth`, or `xsd:gYear`, depending on source precision. 
- If the date is approximate or unclear (e.g. “1920s”, “around 1930”), the date field is left empty and the original wording is preserved outside the baseline date triple. 
- Computation time is kept separate from archival time and belongs to provenance-bearing classifier artefacts rather than to TaleRecording itself. 

#### 3.6.1 Classifier run time 

Classifier outputs already contain run-time timestamps; these are not the historical recording dates.

| Produced meta field | Meaning | RDF mapping in JSON-LD export | Target vocabulary |
|---|---|---|---|
| `trained_at` | When the model artifact was trained (training time). | `Model rft:trainedAt` (typed `xsd:dateTime`) | rft (typed literal) |


### 3.7 Content and classification

**Domains:**  
- **TaleRecording (archival text unit):** `rft:TaleRecording`, aligned with `crm:E33_Linguistic_Object`  
- **TaleContent (abstract content unit):** `rft:TaleContent`, aligned with `crm:E28_Conceptual_Object`  
- **Controlled vocabularies:** `rft:TaleType`, aligned with `skos:Concept`, within a `skos:ConceptScheme` (in the current baseline, `rft:ATU_Scheme`)

This section separates **archival content description and cataloguing** from **system-produced classifier outputs**.  
In the current model, the archival text record and the abstract content are not collapsed into a single node:

- `rft:TaleRecording` carries record-level metadata such as bibliographic citation, description, date, place, and attributions.
- `rft:TaleContent` carries the typological assignment.
- The link between them is expressed as `TaleRecording prov:wasDerivedFrom TaleContent`.

Classifier outputs remain a separate provenance layer and may be represented through PROV-described artefacts (e.g. `ClassificationRun`, `ClassificationResult`, `ClassificationCandidate`) that refer to type concepts without changing the archival baseline graph.

#### 3.7.1 Archival content description and cataloguing

| Local field | Description | RDF property / pattern | Target vocabulary |
|---|---|---|---|
| `content_description` | Short archival content note / text description. | `TaleRecording dcterms:description` | DCTERMS |
| `type_code_1`–`type_code_4` | Folktale type codes recorded in the archival index. In the current baseline export, typological assignment is attached to the content node rather than directly to the recording. | `TaleRecording prov:wasDerivedFrom TaleContent` ; `TaleContent dcterms:subject TaleType` ; `TaleType skos:inScheme ConceptScheme` ; `TaleType skos:notation code` | PROV-O / DCTERMS / SKOS |

**Notes**
- The archival content note is stored as `dcterms:description` on `rft:TaleRecording`.
- Typological assignment is stored on `rft:TaleContent`, not directly on the recording.
- In the current baseline realization, the controlled type vocabulary is the ATU scheme; additional schemes (e.g. SUS or national folktale type systems) remain possible extensions.
- Type concepts are modeled as `skos:Concept` / `rft:TaleType`, with the human-readable label carried by `skos:prefLabel` and the code itself carried by `skos:notation`.

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

#### 3.7.3 Schemes and concept identifiers

- Every ATU type is modeled as `rft:TaleType`, aligned with `skos:Concept`.
- Every ATU type belongs to the scheme `rft:ATU_Scheme`, which is modeled as a `skos:ConceptScheme`:  
  `TaleType skos:inScheme rft:ATU_Scheme`.
- The type number is stored as `skos:notation` (e.g. `"709"`, `"510A"`).
- In exports, ATU concepts are referenced by IRIs such as:  
  `.../rdf/taleType/atu/709`
- For type numbers containing a star, the URI path uses a normalized form, while the original code is preserved in `skos:notation`  
  (e.g. `1060*` → `.../rdf/taleType/atu/1060-star` with `skos:notation "1060*"`).
- The preferred human-readable label is stored as `skos:prefLabel`; optional explanatory text may be stored as `skos:definition`.
- In the current profile, ATU concepts are linked not directly from the archival text record but from `rft:TaleContent` via `dcterms:subject`.

This keeps the ontology clean: SKOS carries the structure and semantics of the classification scheme, while the project ontology adds the domain class `rft:TaleType` and connects type concepts to `rft:TaleContent` in the archival graph.
---

## 4. Tale types as SKOS concepts

### 4.1 Concept scheme strategy

In this project, ATU types are modeled as controlled vocabulary concepts rather than as free text labels. This follows the understanding of ATU as a knowledge organization system (KOS), and more specifically as a classification scheme used for retrieval and comparison in folklore research. 

### 4.2 FAIR and identifier policy

There is no openly maintained, authoritative ATU URI scheme that can be adopted as a stable dependency for this project. For this reason, the knowledge graph mints its own persistent ATU concept URIs under the project namespace, for example:

`https://eugeniavd.github.io/magic_tagger/rdf/taleType/atu/707`

This keeps the graph self-contained and stable across releases. It also avoids making the model dependent on external services whose identifiers, coverage, or availability may change. The strategy is consistent with the FAIR-oriented design of the project, which prioritizes stable URIs, reusable exports, and release-level reproducibility. 

The current export defines one concept scheme only: `rft:ATU_Scheme`. Additional schemes, such as East Slavic SUS types or national tale-type systems, remain possible future extensions but are not part of the present TTL release. 

### 4.3 Current scope and future mappings

In the present implementation, ATU concepts are self-contained and no outbound mapping assertions are included. If needed in future releases, external links may be added as optional mappings, for example through:

- `skos:exactMatch`
- `skos:closeMatch`
- `rdfs:seeAlso`

These would be treated as enrichments rather than as required dependencies of the core graph. This preserves the autonomy of the project vocabulary while keeping interoperability options open. 

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
