# SPARQL Competency Queries — Russian Folktales Knowledge Graph

This folder contains SPARQL competency queries for the corpus knowledge graph export
and the corresponding expected outputs used as lightweight,
versioned baselines for validation and regression checks.

## Goal

- **Competency questions**: each query corresponds to a concrete information need
  (faceted retrieval, corpus analytics, knowledge-quality checks).
- **No public endpoint required**: queries are executed locally against the exported RDF file.
- **Expected outputs**: small CSV snapshots of query results are stored under `expected/`
  to document “what the graph answers” for a given release and to detect regressions.

## Data source

- RDF export (input): `../export/corpus.ttl`

Release alignment:
- These queries and expected outputs are intended to be executed against a **specific dataset release**
  (e.g., `v1`). If the RDF export changes, expected outputs should be regenerated and committed as part of the new release.

## Query list

| ID | File | Competency question | Output |
|----|------|---------------------|--------|
| Q1 | `Q1_tales_by_atu_type.rq` | List all tales for ATU type X (faceted retrieval). | `tale, taleDesc, volume, atuConcept, atuCode` |
| Q2 | `Q2_top_atu_types.rq` | Top-N ATU types by number of tales. | `atuConcept, atuCode, taleCount` |
| Q3 | `Q3_top_narrators.rq` | Top narrators by number of tales. | `narrator, narratorLabel, taleCount` |
| Q4 | `Q4_top_collectors_time_coverage.rq` | Top collectors (via volume) + time coverage (min/max volume date). | `collector, collectorLabel, taleCount, minDate, maxDate` |
| Q5 | `Q5_coverage_sanity_checks.rq` | Coverage checks: missing volume / missing subject / missing place. | `metric, count` |

## How to run (local, no endpoint) — Python workflow

We execute SPARQL locally using Python (e.g., `rdflib`) over the exported RDF file.
This keeps the project lightweight and avoids deploying a SPARQL server.

### 1) Environment

Install dependencies (example):

```bash
pip install rdflib pandas

python run_queries.py --data ../export/corpus.ttl --query Q2_top_atu_types.rq --out expected/Q2_top_atu_types.csv
