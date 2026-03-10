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
python rdf/validation/validate_kg.py \
  --data rdf/rdf_serialization/corpus.ttl \
         rdf/rdf_serialization/agents.ttl \
         rdf/rdf_serialization/atu_types.ttl \
         rdf/rdf_serialization/biblio_sources.ttl \
         rdf/rdf_serialization/dataset_corpus_v1.ttl \
  --shapes rdf/shacl/shapes.ttl \
  --report rdf/validation/report.ttl \
  --report-text rdf/validation/report.txt
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
| Q1 | `Q1_tales_by_atu_type.rq` | List all **tale recordings** for a given **ATU type code X**. The query starts from `rft:TaleRecording`, follows `prov:wasDerivedFrom` to `rft:TaleContent`, and retrieves the ATU type via `dcterms:subject`. ATU code is taken from `skos:notation` when available, with fallback from the ATU concept URI. | `recording, taleDesc, volume, content, atuConcept, atuCode` |
| Q2 | `Q2_top_atu_types.rq` | Compute the distribution of **Top-N ATU types** by number of **tale recordings**. Counting is done over `rft:TaleRecording`, while type assignment is resolved through `rft:TaleContent -> dcterms:subject -> rft:TaleType`. | `atuConcept, atuCode, atuPrefLabel, atuTitle, taleCount` |
| Q3 | `Q3_top_narrators.rq` | List **Top narrators** by number of **tale recordings**. Narrators are linked to `rft:TaleRecording` through `prov:qualifiedAttribution`, with `prov:hadRole locrel:nrt` and `prov:agent ?narrator`. Labels are taken from `rdfs:label`, with fallback to the local identifier from the IRI. | `narratorKey, narratorLabel, taleCount` |
| Q4 | `Q4_yearly_collectors_labeled.rq` | For each collector, count distinct **tale recordings** per year. Collectors are linked directly to `rft:TaleRecording` via `prov:qualifiedAttribution` with `prov:hadRole locrel:col`. Year is derived from `dcterms:created` by extracting the first four digits, so the query supports `xsd:date`, `xsd:gYearMonth`, and `xsd:gYear`. Collector labels are resolved from `rdfs:label`, with fallback to the local IRI identifier. | `collector, collectorLabel, year, taleCount` |
| Q5 | `Q5_coverage_sanity_checks.rq` | Coverage sanity checks over **TaleRecordings** (`rft:TaleRecording`, IRIs only). Returns counts of distinct recordings per metric across five groups: **A) Containers/provenance** — missing **volume container** (`dcterms:isPartOf` to an IRI containing `/rdf/volume/`), missing **dataset container** (`dcterms:isPartOf` to an IRI containing `/dataset/`), missing **content link** (`prov:wasDerivedFrom`); **B) Typing** — missing `dcterms:subject` on the linked `rft:TaleContent`, or subject present but **not an ATU concept URI**; **C) People** — missing **narrator attribution** (`prov:qualifiedAttribution` with `prov:hadRole locrel:nrt`), or missing **collector attribution** (`prov:qualifiedAttribution` with `prov:hadRole locrel:col`); **D) Place** — missing `dcterms:spatial`; **E) Time** — missing `dcterms:created`, or created date present but not typed as one of `xsd:date`, `xsd:gYearMonth`, or `xsd:gYear`. | `metric, count` |

### How to run 

We execute SPARQL locally using Python (`rdflib`) over the exported RDF file.

Install dependencies (minimal):

```bash
pip install rdflib pandas
```

Run a query and export CSV:

```bash
python -m rdf.queries.run Q1 --data rdf/rdf_serialization
```

This writes: `rdf/queries/query_results/Q1.csv` and prints a short preview to stdout.

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
