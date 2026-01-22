# RDF — Russian Folktales Knowledge Graph 

This folder contains the RDF/Linked Data exports of the corpus, the lightweight project ontology
(namespace `rft:`), and a small, reproducible competency query suite used for validation and regression checks.

The design goal is reuse-first: Dublin Core Terms (DCTERMS), SKOS, PROV-O, and a light CIDOC-CRM profile,
with project-specific predicates only where needed for corpus-specific capture context and UX.

---

## 1) RDF exports and serializations

Exports are stored under `rdf/rdf_serialization/` as Turtle (`.ttl`). The exports are modular, but designed
to work together.

Typical files (v1):

- `corpus.ttl` — main corpus graph (tales, volumes, places, basic links)
- `agents.ttl` — person resources (narrators/collectors as agents) + labels/notes
- `atu_types.ttl` — ATU concept scheme + concepts (SKOS)
- `biblio_sources.ttl` — bibliographic resources / sources
- `dataset_corpus_v1.ttl` — dataset-level metadata (DCAT / provenance)

---

## 2) How to build exports

**If you only need to reproduce evaluation**, you can skip this step: the exported TTL files are committed
under `rdf/rdf_serialization/`.

To regenerate exports (project pipeline), run the export step from the project root, writing outputs into
`rdf/rdf_serialization/`:

```bash
python -m rdf/build_kg.py --out rdf/rdf_serialization
```

Recommended convention:
- Treat each corpus release as a versioned export (e.g., `v1`), and regenerate/query expected outputs
  as part of the same release update.

---

## 3) How to validate

Validation is intentionally lightweight and runs locally.

### 4.1 Syntax / parse validation (Turtle)

```bash
python rdf/validation/validate_kg.py
```
This writes: `rdf/validation/report.txt`, `rdf/validation/report.ttl`.

### 4.2 Quality checks 

Run Q5 (coverage checks) and inspect the resulting CSV:

```bash
python rdf/quality/kg_quality_log.py
```

This writes: `rdf/quality/quality_log.json`.

---

## 5) SPARQL competency queries (local, no endpoint)

This folder contains SPARQL competency queries for the corpus knowledge graph export and the corresponding
expected outputs used as lightweight, versioned baselines for validation and regression checks.

### Goal

- **Competency questions**: each query corresponds to a concrete information need (faceted retrieval, analytics, quality checks).
- **No public endpoint required**: queries are executed locally against the exported RDF file.
- **Expected outputs**: small CSV snapshots under `expected/` document “what the graph answers” for a given release and detect regressions.

### Data source

- RDF export (input): `rdf/rdf_serialization/corpus.ttl`

Release alignment:
- Queries and expected outputs are intended to be executed against a **specific dataset release** (e.g., `v1`).
  If the RDF export changes, expected outputs should be regenerated and committed as part of the new release.

### Query list

| ID | File | Competency question | Output |
|----|------|---------------------|--------|
| Q1 | `Q1_tales_by_atu_type.rq` | List all tales for a given **ATU type code X** (baseline snapshot uses a fixed code, e.g. `707`). ATU code is derived from the ATU concept URI (fallback: `skos:notation` if present). | `tale, taleDesc, volume, atuConcept, atuCode` |
| Q2 | `Q2_top_atu_types.rq` | Compute the **Top-N ATU types** by number of tales (distribution). ATU is identified via `dcterms:subject` to ATU concept URIs. | `atuConcept, atuCode, taleCount` |
| Q3 | `Q3_top_narrators.rq` | List **Top narrators** by number of tales, where narrators are linked at tale level via `dcterms:contributor` (labels from `rdfs:label`, with URI fallback if missing). | `narrator, narratorLabel, taleCount` *(or `narratorKey, narratorLabel, taleCount` if using the IRI-or-literal variant)* |
| Q4 | `Q4_top_collectors_time_coverage.rq` | List **Top collectors** by number of tales, where collectors are attached to volumes via `dcterms:creator`, and provide **time coverage** from volume-level `dcterms:created` (min/max, with normalization for `xsd:date` / `xsd:gYear` / date-like strings). | `collector, collectorLabel, taleCount, minDate, maxDate` *(optionally also `volumeCount, datedVolumeCount` if using the extended version)* |
| Q5 | `Q5_coverage_sanity_checks.rq` | Coverage sanity checks over Tales (`crm:E33_Linguistic_Object`): (1) missing **volume membership** (no `dcterms:isPartOf` to a Volume resource), (2) missing **subject** (`dcterms:subject`), (3) missing **place** (none of `dcterms:spatial`, `rft:recordingPlace`, `rft:recordingParish`). | `metric, count` |

### How to run 

We execute SPARQL locally using Python (`rdflib`) over the exported RDF file.

Install dependencies (minimal):

```bash
pip install rdflib pandas
```

Run a query and export CSV:

```bash
python -m rdf.queries.run Q2 \
  --data rdf/rdf_serialization \
  --out rdf/queries/query_results

```

This writes: `rdf/queries/query_results/Q2.csv` and prints a short preview to stdout.

## 6) Export JSON-LD using the canonical context

The file `context.jsonld` defines the project **JSON-LD context** used to serialize RDF exports as JSON-LD in a consistent, reusable way.  

It provides: 
- compact, human-readable keys for common RDF predicates (DCTERMS/SKOS/PROV/DCAT/CIDOC),
- a stable `@base` and namespace prefixes,
- explicit datatype/IRI coercion (e.g., `creator`, `subject`, `isPartOf` as IRIs; `created` as `xsd:date`; `issued` as `xsd:gYear`; `age` as `xsd:integer`).  

Using a shared context makes JSON-LD exports portable across tools (Python/JS/triplestores), reduces schema drift, and ensures that consumers interpret identifiers and dates correctly.

```bash
python rdf/export_jsonld.py \
  --ttl-dir rdf/rdf_serialization \
  --glob "*.ttl" \
  --context rdf/context.json \
  --out-dir rdf/rdf_serialization/jsonld \
  --as-graph
