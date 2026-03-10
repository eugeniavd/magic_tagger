from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import argparse
import json
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Set

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, DCTERMS as DCT, XSD
from src.uris import BASE_DATA, RFT

# ---------------------------------------------------------------------
# Namespaces
# ---------------------------------------------------------------------
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
PROV = Namespace("http://www.w3.org/ns/prov#")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
CRM = Namespace("http://www.cidoc-crm.org/cidoc-crm/")
DCMITYPE = Namespace("http://purl.org/dc/dcmitype/")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")

# ---------------------------------------------------------------------
# IRIs / terms used in current serialization
# ---------------------------------------------------------------------
FOAF_PAGE = FOAF.page

ROLE_NARRATOR = URIRef("http://id.loc.gov/vocabulary/relators/nrt")
ROLE_COLLECTOR = URIRef("http://id.loc.gov/vocabulary/relators/col")

RIGHTS_OPEN = RFT.rights_open
RIGHTS_PARTLY_ANON = RFT.rights_partly_anonymised

ALLOWED_CREATED_DT = {XSD.date, XSD.gYearMonth, XSD.gYear}
ALLOWED_BIRTH_DT = {XSD.date, XSD.gYearMonth, XSD.gYear}


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def percent(part: int, whole: int) -> float:
    return round((part / whole * 100.0), 2) if whole else 0.0


def load_merged_graph(paths: List[Path], rdf_format: str = "turtle") -> Graph:
    g = Graph()
    for p in paths:
        if not p.exists():
            raise FileNotFoundError(f"TTL not found: {p}")
        g.parse(str(p), format=rdf_format)
    return g


def subjects_of_type(g: Graph, class_iri: URIRef) -> Set[URIRef]:
    return {s for s, _, _ in g.triples((None, RDF.type, class_iri)) if isinstance(s, URIRef)}


def has_any_predicate(g: Graph, s: URIRef, preds: Iterable[URIRef]) -> bool:
    return any(True for p in preds for _ in g.triples((s, p, None)))


def objects_iris(g: Graph, s: URIRef, p: URIRef) -> Set[URIRef]:
    return {o for _, _, o in g.triples((s, p, None)) if isinstance(o, URIRef)}


def attributions_of_entity(g: Graph, entity: URIRef) -> Set[URIRef]:
    return {o for _, _, o in g.triples((entity, PROV.qualifiedAttribution, None)) if isinstance(o, URIRef)}


def has_role_attribution(g: Graph, entity: URIRef, role: URIRef) -> bool:
    for att in attributions_of_entity(g, entity):
        if (att, PROV.hadRole, role) in g:
            return True
    return False


def agents_in_role_attributions(g: Graph, entity: URIRef, role: URIRef) -> Set[URIRef]:
    out: Set[URIRef] = set()
    for att in attributions_of_entity(g, entity):
        if (att, PROV.hadRole, role) not in g:
            continue
        for _, _, ag in g.triples((att, PROV.agent, None)):
            if isinstance(ag, URIRef):
                out.add(ag)
    return out


def iri_contains(node: URIRef, fragment: str) -> bool:
    return isinstance(node, URIRef) and fragment in str(node)


def is_volume_iri(node: URIRef) -> bool:
    return iri_contains(node, "/volume/")


def is_collection_iri(node: URIRef) -> bool:
    return iri_contains(node, "/collection/")


def is_dataset_iri(node: URIRef) -> bool:
    return iri_contains(node, "/dataset/")


def is_biblio_iri(node: URIRef) -> bool:
    return iri_contains(node, "/biblio/")


def is_tale_type_iri(node: URIRef) -> bool:
    return iri_contains(node, "/taleType/atu/")


def is_person_iri(node: URIRef) -> bool:
    return iri_contains(node, "/person/")


def is_literal_lang(lit) -> bool:
    return isinstance(lit, Literal) and getattr(lit, "language", None) is not None


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="Compute KG quality log metrics for the current RDF release.")
    ap.add_argument(
        "--data",
        nargs="+",
        default=[
            str(REPO_ROOT / "rdf" / "rdf_serialization" / "corpus.ttl"),
            str(REPO_ROOT / "rdf" / "rdf_serialization" / "agents.ttl"),
            str(REPO_ROOT / "rdf" / "rdf_serialization" / "atu_types.ttl"),
            str(REPO_ROOT / "rdf" / "rdf_serialization" / "biblio_sources.ttl"),
            str(REPO_ROOT / "rdf" / "rdf_serialization" / "dataset_corpus_v1.ttl"),
        ],
        help="One or more TTL files to merge for metrics.",
    )
    ap.add_argument(
        "--out",
        default=str(REPO_ROOT / "rdf" / "quality" / "quality_log.json"),
        help="Output JSON metrics log",
    )
    ap.add_argument(
        "--data-format",
        default="turtle",
        help="RDF format for inputs (default: turtle).",
    )
    ap.add_argument(
        "--debug-recording",
        default="",
        help="Optional TaleRecording IRI to print debug triples for.",
    )
    args = ap.parse_args()

    data_paths = [Path(p).expanduser().resolve() for p in args.data]
    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    g = load_merged_graph(data_paths, rdf_format=args.data_format)
    triples_count = len(g)

    if args.debug_recording:
        rec = URIRef(args.debug_recording.strip())
        print("DEBUG recording:", rec)
        print("DEBUG created:", list(g.triples((rec, DCT.created, None)))[:10])
        print("DEBUG accessRights:", list(g.triples((rec, DCT.accessRights, None)))[:10])
        print("DEBUG bibliographicCitation:", list(g.triples((rec, DCT.bibliographicCitation, None)))[:10])
        print("DEBUG spatial:", list(g.triples((rec, DCT.spatial, None)))[:10])
        print("DEBUG qualifiedAttribution:", list(g.triples((rec, PROV.qualifiedAttribution, None)))[:10])
        print("DEBUG wasDerivedFrom:", list(g.triples((rec, PROV.wasDerivedFrom, None)))[:10])

    # -----------------------------------------------------------------
    # Entity sets
    # -----------------------------------------------------------------
    tale_recordings = subjects_of_type(g, RFT.TaleRecording)
    tale_contents = subjects_of_type(g, RFT.TaleContent)

    volumes = {
        s for s, _, _ in g.triples((None, RDF.type, DCT.BibliographicResource))
        if isinstance(s, URIRef) and is_volume_iri(s)
    }
    biblio_sources = {
        s for s, _, _ in g.triples((None, RDF.type, DCT.BibliographicResource))
        if isinstance(s, URIRef) and is_biblio_iri(s)
    }
    collections = subjects_of_type(g, DCMITYPE.Collection)
    agents = {
        s for s, _, _ in g.triples((None, RDF.type, PROV.Agent))
        if isinstance(s, URIRef) and is_person_iri(s)
    }
    atu_defined = subjects_of_type(g, RFT.TaleType)
    datasets = subjects_of_type(g, DCAT.Dataset)
    distributions = subjects_of_type(g, DCAT.Distribution)
    attribution_nodes = subjects_of_type(g, PROV.Attribution)

    # Referenced concepts/agents
    atu_refs = {
        o for c in tale_contents
        for o in objects_iris(g, c, DCT.subject)
        if is_tale_type_iri(o)
    }

    person_refs: Set[URIRef] = set()
    for t in tale_recordings:
        for role in (ROLE_NARRATOR, ROLE_COLLECTOR):
            person_refs |= agents_in_role_attributions(g, t, role)
    for v in volumes:
        person_refs |= {o for o in objects_iris(g, v, DCT.creator) if is_person_iri(o)}
    for ds in datasets:
        person_refs |= {o for o in objects_iris(g, ds, DCT.creator) if is_person_iri(o)}
        person_refs |= {o for o in objects_iris(g, ds, DCT.publisher) if is_person_iri(o)}

    # -----------------------------------------------------------------
    # Coverage metrics
    # -----------------------------------------------------------------
    recordings_with_isPartOf_volume = 0
    recordings_with_isPartOf_dataset = 0
    recordings_with_created = 0
    recordings_with_access = 0
    recordings_with_spatial = 0
    recordings_with_biblio_citation = 0
    recordings_with_content_link = 0
    recordings_with_narrator_attr = 0
    recordings_with_collector_attr = 0

    for t in tale_recordings:
        parts = objects_iris(g, t, DCT.isPartOf)
        if any(is_volume_iri(o) for o in parts):
            recordings_with_isPartOf_volume += 1
        if any(is_dataset_iri(o) for o in parts):
            recordings_with_isPartOf_dataset += 1
        if has_any_predicate(g, t, (DCT.created,)):
            recordings_with_created += 1
        if has_any_predicate(g, t, (DCT.accessRights, DCT.rights)):
            recordings_with_access += 1
        if has_any_predicate(g, t, (DCT.spatial,)):
            recordings_with_spatial += 1
        if has_any_predicate(g, t, (DCT.bibliographicCitation,)):
            recordings_with_biblio_citation += 1
        if any(o in tale_contents for o in objects_iris(g, t, PROV.wasDerivedFrom)):
            recordings_with_content_link += 1
        if has_role_attribution(g, t, ROLE_NARRATOR):
            recordings_with_narrator_attr += 1
        if has_role_attribution(g, t, ROLE_COLLECTOR):
            recordings_with_collector_attr += 1

    contents_with_atu_subject = 0
    for c in tale_contents:
        if any(is_tale_type_iri(o) for o in objects_iris(g, c, DCT.subject)):
            contents_with_atu_subject += 1

    volumes_with_creator = sum(1 for v in volumes if has_any_predicate(g, v, (DCT.creator,)))
    volumes_with_foaf_page = sum(1 for v in volumes if has_any_predicate(g, v, (FOAF_PAGE,)))
    volumes_with_dct_source = sum(1 for v in volumes if has_any_predicate(g, v, (DCT.source,)))
    volumes_with_see_also = sum(1 for v in volumes if has_any_predicate(g, v, (RDFS.seeAlso,)))

    collections_label_lang_ok = 0
    for c in collections:
        if any(is_literal_lang(o) for _, _, o in g.triples((c, RDFS.label, None))):
            collections_label_lang_ok += 1

    datasets_with_distribution = sum(1 for ds in datasets if has_any_predicate(g, ds, (DCAT.distribution,)))
    datasets_with_issued = sum(1 for ds in datasets if has_any_predicate(g, ds, (DCT.issued,)))

    # -----------------------------------------------------------------
    # Completeness metrics
    # -----------------------------------------------------------------
    RECORDING_RIGHTS_PREDS = (DCT.accessRights, DCT.rights)
    RECORDING_SOURCE_PREDS = (DCT.bibliographicCitation, DCT.source)
    VOL_SOURCE_PREDS = (FOAF_PAGE, DCT.source, RDFS.seeAlso)

    recordings_complete_rights = sum(1 for t in tale_recordings if has_any_predicate(g, t, RECORDING_RIGHTS_PREDS))
    recordings_complete_date = sum(1 for t in tale_recordings if has_any_predicate(g, t, (DCT.created,)))
    recordings_complete_place = sum(1 for t in tale_recordings if has_any_predicate(g, t, (DCT.spatial,)))
    recordings_complete_content = sum(1 for t in tale_recordings if has_any_predicate(g, t, (PROV.wasDerivedFrom,)))
    contents_complete_subject = sum(1 for c in tale_contents if has_any_predicate(g, c, (DCT.subject,)))

    recordings_complete_source = 0
    for t in tale_recordings:
        if has_any_predicate(g, t, RECORDING_SOURCE_PREDS):
            recordings_complete_source += 1
            continue
        vols = {o for o in objects_iris(g, t, DCT.isPartOf) if is_volume_iri(o)}
        if vols and any(has_any_predicate(g, v, VOL_SOURCE_PREDS) for v in vols):
            recordings_complete_source += 1

    volumes_complete_source = sum(1 for v in volumes if has_any_predicate(g, v, VOL_SOURCE_PREDS))

    # -----------------------------------------------------------------
    # Sanity checks
    # -----------------------------------------------------------------
    bad_created = 0
    for t in tale_recordings:
        for _, _, o in g.triples((t, DCT.created, None)):
            if getattr(o, "datatype", None) not in ALLOWED_CREATED_DT:
                bad_created += 1

    bad_birthdate = 0
    for a in agents:
        for _, _, o in g.triples((a, URIRef("https://schema.org/birthDate"), None)):
            if getattr(o, "datatype", None) not in ALLOWED_BIRTH_DT:
                bad_birthdate += 1

    bad_age_at_recording = 0
    for a in agents:
        for _, _, o in g.triples((a, RFT.ageAtRecording, None)):
            if getattr(o, "datatype", None) != XSD.integer:
                bad_age_at_recording += 1

    bad_access_rights = 0
    for t in tale_recordings:
        for _, _, o in g.triples((t, DCT.accessRights, None)):
            if o not in {RIGHTS_OPEN, RIGHTS_PARTLY_ANON}:
                bad_access_rights += 1

    contents_subject_non_atu = 0
    for c in tale_contents:
        for _, _, o in g.triples((c, DCT.subject, None)):
            if isinstance(o, URIRef) and not is_tale_type_iri(o):
                contents_subject_non_atu += 1

    # -----------------------------------------------------------------
    # Output
    # -----------------------------------------------------------------
    metrics: Dict = {
        "generatedAtTime": datetime.now(timezone.utc).isoformat(),
        "inputs": {"ttl": [str(p) for p in data_paths]},
        "size": {"triples": triples_count},
        "entities": {
            "tale_recordings": len(tale_recordings),
            "tale_contents": len(tale_contents),
            "volumes": len(volumes),
            "collections": len(collections),
            "atu_concepts_defined": len(atu_defined),
            "atu_concepts_referenced": len(atu_refs),
            "persons_defined": len(agents),
            "persons_referenced": len(person_refs),
            "attribution_nodes": len(attribution_nodes),
            "bibliographic_sources": len(biblio_sources),
            "datasets": len(datasets),
            "distributions": len(distributions),
        },
        "coverage": {
            "recordings_with_isPartOf_volume": {
                "count": recordings_with_isPartOf_volume,
                "percent": percent(recordings_with_isPartOf_volume, len(tale_recordings)),
            },
            "recordings_with_isPartOf_dataset": {
                "count": recordings_with_isPartOf_dataset,
                "percent": percent(recordings_with_isPartOf_dataset, len(tale_recordings)),
            },
            "recordings_with_created": {
                "count": recordings_with_created,
                "percent": percent(recordings_with_created, len(tale_recordings)),
            },
            "recordings_with_accessRights_or_rights": {
                "count": recordings_with_access,
                "percent": percent(recordings_with_access, len(tale_recordings)),
            },
            "recordings_with_spatial": {
                "count": recordings_with_spatial,
                "percent": percent(recordings_with_spatial, len(tale_recordings)),
            },
            "recordings_with_bibliographicCitation": {
                "count": recordings_with_biblio_citation,
                "percent": percent(recordings_with_biblio_citation, len(tale_recordings)),
            },
            "recordings_with_content_link": {
                "count": recordings_with_content_link,
                "percent": percent(recordings_with_content_link, len(tale_recordings)),
            },
            "recordings_with_narrator_attribution_locrel_nrt": {
                "count": recordings_with_narrator_attr,
                "percent": percent(recordings_with_narrator_attr, len(tale_recordings)),
            },
            "recordings_with_collector_attribution_locrel_col": {
                "count": recordings_with_collector_attr,
                "percent": percent(recordings_with_collector_attr, len(tale_recordings)),
            },
            "contents_with_atu_subject": {
                "count": contents_with_atu_subject,
                "percent": percent(contents_with_atu_subject, len(tale_contents)),
            },
            "volumes_with_creator": {
                "count": volumes_with_creator,
                "percent": percent(volumes_with_creator, len(volumes)),
            },
            "collections_with_label_langtag": {
                "count": collections_label_lang_ok,
                "percent": percent(collections_label_lang_ok, len(collections)),
            },
            "datasets_with_distribution": {
                "count": datasets_with_distribution,
                "percent": percent(datasets_with_distribution, len(datasets)),
            },
            "datasets_with_issued": {
                "count": datasets_with_issued,
                "percent": percent(datasets_with_issued, len(datasets)),
            },
        },
        "completeness": {
            "recordings_with_rights": {
                "count": recordings_complete_rights,
                "percent": percent(recordings_complete_rights, len(tale_recordings)),
            },
            "recordings_with_source": {
                "count": recordings_complete_source,
                "percent": percent(recordings_complete_source, len(tale_recordings)),
            },
            "recordings_with_place": {
                "count": recordings_complete_place,
                "percent": percent(recordings_complete_place, len(tale_recordings)),
            },
            "recordings_with_date": {
                "count": recordings_complete_date,
                "percent": percent(recordings_complete_date, len(tale_recordings)),
            },
            "recordings_with_content": {
                "count": recordings_complete_content,
                "percent": percent(recordings_complete_content, len(tale_recordings)),
            },
            "contents_with_subject": {
                "count": contents_complete_subject,
                "percent": percent(contents_complete_subject, len(tale_contents)),
            },
            "volumes_with_source": {
                "count": volumes_complete_source,
                "percent": percent(volumes_complete_source, len(volumes)),
            },
        },
        "volume_source_breakdown": {
            "volumes_with_foaf_page": {
                "count": volumes_with_foaf_page,
                "percent": percent(volumes_with_foaf_page, len(volumes)),
            },
            "volumes_with_dct_source": {
                "count": volumes_with_dct_source,
                "percent": percent(volumes_with_dct_source, len(volumes)),
            },
            "volumes_with_rdfs_seeAlso": {
                "count": volumes_with_see_also,
                "percent": percent(volumes_with_see_also, len(volumes)),
            },
        },
        "sanity": {
            "recordings_created_wrong_datatype": bad_created,
            "agents_birthDate_wrong_datatype": bad_birthdate,
            "agents_ageAtRecording_wrong_datatype": bad_age_at_recording,
            "recordings_accessRights_uncontrolled": bad_access_rights,
            "contents_subject_non_atu_iri": contents_subject_non_atu,
        },
        "notes": {
            "recordings_with_narrator_definition": (
                "TaleRecording has prov:qualifiedAttribution node where prov:hadRole = locrel:nrt and prov:agent is a URI"
            ),
            "recordings_with_collector_definition": (
                "TaleRecording has prov:qualifiedAttribution node where prov:hadRole = locrel:col and prov:agent is a URI"
            ),
            "recordings_with_source_definition": (
                "direct: TaleRecording has dcterms:bibliographicCitation OR dcterms:source; "
                "fallback: TaleRecording dcterms:isPartOf volume AND volume has foaf:page OR dcterms:source OR rdfs:seeAlso"
            ),
            "contents_with_subject_definition": "TaleContent has dcterms:subject pointing to /taleType/atu/ IRI",
            "volumes_with_source_definition": "volume has foaf:page OR dcterms:source OR rdfs:seeAlso",
            "rights_controlled_values": {
                "rft:rights_open": str(RIGHTS_OPEN),
                "rft:rights_partly_anonymised": str(RIGHTS_PARTLY_ANON),
            },
            "allowed_created_datatypes": [str(x) for x in ALLOWED_CREATED_DT],
            "allowed_birthDate_datatypes": [str(x) for x in ALLOWED_BIRTH_DT],
            "foaf_page_iri_used": str(FOAF_PAGE),
            "role_uris_used": {
                "locrel:nrt": str(ROLE_NARRATOR),
                "locrel:col": str(ROLE_COLLECTOR),
            },
        },
    }

    out_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())