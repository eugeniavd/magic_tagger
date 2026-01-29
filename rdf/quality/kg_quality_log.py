from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Set, Iterable

from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS, DCTERMS as DCT, XSD

# Use explicit IRIs for robustness (do not rely on rdflib FOAF namespace mapping)
FOAF_PAGE = URIRef("http://xmlns.com/foaf/0.1/page")

CRM_E33 = URIRef("http://www.cidoc-crm.org/cidoc-crm/E33_Linguistic_Object")
DCMITYPE_COLLECTION = URIRef("http://purl.org/dc/dcmitype/Collection")


def subjects_of_type(g: Graph, class_iri: URIRef) -> Set[URIRef]:
    return {s for s, _, _ in g.triples((None, RDF.type, class_iri)) if isinstance(s, URIRef)}


def percent(part: int, whole: int) -> float:
    return round((part / whole * 100.0), 2) if whole else 0.0


def has_any_predicate(g: Graph, s: URIRef, preds: Iterable[URIRef]) -> bool:
    for p in preds:
        for _ in g.triples((s, p, None)):
            return True
    return False


def objects_iris(g: Graph, s: URIRef, p: URIRef) -> Set[URIRef]:
    return {o for _, _, o in g.triples((s, p, None)) if isinstance(o, URIRef)}


def main() -> int:
    ap = argparse.ArgumentParser(description="Compute KG quality log metrics for a TTL graph.")
    ap.add_argument("--ttl", default="rdf/rdf_serialization/corpus.ttl", help="Input TTL path")
    ap.add_argument("--out", default="rdf/quality/quality_log.json", help="Output JSON metrics log")
    ap.add_argument(
        "--base",
        default="https://github.com/eugeniavd/magic_tagger/rdf/",
        help="BASE IRI prefix for heuristics (reserved; not required by current metrics).",
    )
    ap.add_argument(
        "--debug-volume",
        default="",
        help="Optional: volume IRI to print triples for (e.g., https://.../rdf/volume/era_vene_13).",
    )
    args = ap.parse_args()

    ttl_path = Path(args.ttl).expanduser().resolve()
    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not ttl_path.exists():
        raise FileNotFoundError(f"TTL not found: {ttl_path}")

    g = Graph()
    g.parse(str(ttl_path), format="turtle")
    triples_count = len(g)

    # Optional debug: confirm that foaf:page is actually present in this TTL
    if args.debug_volume:
        v = URIRef(args.debug_volume.strip())
        print("DEBUG volume:", v)
        print("DEBUG foaf:page triples:", list(g.triples((v, FOAF_PAGE, None)))[:10])
        print("DEBUG dct:source triples:", list(g.triples((v, DCT.source, None)))[:10])
        print("DEBUG rdfs:seeAlso triples:", list(g.triples((v, RDFS.seeAlso, None)))[:10])

    # ---- entity sets ----
    tales = subjects_of_type(g, CRM_E33)  # crm:E33_Linguistic_Object
    volumes = {s for s, _, _ in g.triples((None, RDF.type, DCT.BibliographicResource)) if isinstance(s, URIRef)}
    collections = {s for s, _, _ in g.triples((None, RDF.type, DCMITYPE_COLLECTION)) if isinstance(s, URIRef)}

    # referenced ATU concepts = unique IRIs in dcterms:subject (objects)
    atu_refs = {o for _, _, o in g.triples((None, DCT.subject, None)) if isinstance(o, URIRef)}

    # referenced agents (persons) from volumes creators and tale contributors
    person_refs: Set[URIRef] = set()
    for _, _, o in g.triples((None, DCT.creator, None)):
        if isinstance(o, URIRef):
            person_refs.add(o)
    for _, _, o in g.triples((None, DCT.contributor, None)):
        if isinstance(o, URIRef):
            person_refs.add(o)

    # -------------------------
    # Coverage metrics for tales
    # -------------------------
    def tales_with(p: URIRef) -> int:
        return len({s for s, _, _ in g.triples((None, p, None)) if s in tales})

    tales_is_part_of = tales_with(DCT.isPartOf)
    tales_with_atu = len({s for s, _, o in g.triples((None, DCT.subject, None)) if s in tales and isinstance(o, URIRef)})
    tales_with_created = len({s for s, _, _ in g.triples((None, DCT.created, None)) if s in tales})
    tales_with_access = len({s for s, _, _ in g.triples((None, DCT.accessRights, None)) if s in tales})
    tales_with_rights = len({s for s, _, _ in g.triples((None, DCT.rights, None)) if s in tales})
    tales_with_narr = len({s for s, _, o in g.triples((None, DCT.contributor, None)) if s in tales and isinstance(o, URIRef)})
    tales_with_spatial = len({s for s, _, _ in g.triples((None, DCT.spatial, None)) if s in tales})

    # datatype sanity: dcterms:created should be xsd:date
    bad_created = 0
    for s, _, o in g.triples((None, DCT.created, None)):
        if s in tales:
            if getattr(o, "datatype", None) != XSD.date:
                bad_created += 1

    # collections label language tag sanity
    collections_label_lang_ok = 0
    for c in collections:
        ok = False
        for _, _, o in g.triples((c, RDFS.label, None)):
            if getattr(o, "language", None):  # has lang tag
                ok = True
                break
        if ok:
            collections_label_lang_ok += 1

    # -------------------------
    # COMPLETENESS (rights/source/place/date)
    # Key change: "source" for volume includes foaf:page
    # -------------------------
    TALE_RIGHTS_PREDS = (DCT.accessRights, DCT.rights)

    # Tale-level source (if you ever add it): URI or citation string
    TALE_SOURCE_PREDS = (DCT.source, DCT.bibliographicCitation)

    # Volume-level source (your actual model): foaf:page (Kivike landing page)
    # plus backward compatibility if you had used these earlier
    VOL_SOURCE_PREDS = (FOAF_PAGE, DCT.source, RDFS.seeAlso)

    # 1) Tale rights/date/place (direct)
    tales_complete_rights = sum(1 for t in tales if has_any_predicate(g, t, TALE_RIGHTS_PREDS))
    tales_complete_date = sum(1 for t in tales if has_any_predicate(g, t, (DCT.created,)))
    tales_complete_place = sum(1 for t in tales if has_any_predicate(g, t, (DCT.spatial,)))

    # 2) Tale source:
    #    - direct (if present): dcterms:source OR dcterms:bibliographicCitation
    #    - fallback derived: tale isPartOf volume AND volume has foaf:page (or legacy predicates)
    tales_complete_source = 0
    for t in tales:
        if has_any_predicate(g, t, TALE_SOURCE_PREDS):
            tales_complete_source += 1
            continue

        vols = objects_iris(g, t, DCT.isPartOf)
        if not vols:
            continue

        if any(has_any_predicate(g, v, VOL_SOURCE_PREDS) for v in vols):
            tales_complete_source += 1

    # 3) Volume completeness for source (direct)
    volumes_complete_source = sum(1 for v in volumes if has_any_predicate(g, v, VOL_SOURCE_PREDS))

    # Optional breakdown to prove foaf:page is being counted
    volumes_with_foaf_page = sum(1 for v in volumes if has_any_predicate(g, v, (FOAF_PAGE,)))
    volumes_with_dct_source = sum(1 for v in volumes if has_any_predicate(g, v, (DCT.source,)))
    volumes_with_see_also = sum(1 for v in volumes if has_any_predicate(g, v, (RDFS.seeAlso,)))

    metrics: Dict = {
        "generatedAtTime": datetime.now(timezone.utc).isoformat(),
        "inputs": {"ttl": str(ttl_path)},
        "size": {"triples": triples_count},
        "entities": {
            "tales": len(tales),
            "volumes": len(volumes),
            "collections": len(collections),
            "atu_concepts_referenced": len(atu_refs),
            "persons_referenced": len(person_refs),
        },
        "coverage": {
            "tales_with_isPartOf_volume": {"count": tales_is_part_of, "percent": percent(tales_is_part_of, len(tales))},
            "tales_with_atu_subject": {"count": tales_with_atu, "percent": percent(tales_with_atu, len(tales))},
            "tales_with_created": {"count": tales_with_created, "percent": percent(tales_with_created, len(tales))},
            "tales_with_accessRights": {"count": tales_with_access, "percent": percent(tales_with_access, len(tales))},
            "tales_with_rights": {"count": tales_with_rights, "percent": percent(tales_with_rights, len(tales))},
            "tales_with_contributor_narrator": {"count": tales_with_narr, "percent": percent(tales_with_narr, len(tales))},
            "tales_with_spatial": {"count": tales_with_spatial, "percent": percent(tales_with_spatial, len(tales))},
            "collections_with_label_langtag": {"count": collections_label_lang_ok, "percent": percent(collections_label_lang_ok, len(collections))},
        },
        "completeness": {
            "tales_with_rights": {"count": tales_complete_rights, "percent": percent(tales_complete_rights, len(tales))},
            "tales_with_source": {"count": tales_complete_source, "percent": percent(tales_complete_source, len(tales))},
            "tales_with_place": {"count": tales_complete_place, "percent": percent(tales_complete_place, len(tales))},
            "tales_with_date": {"count": tales_complete_date, "percent": percent(tales_complete_date, len(tales))},
            "volumes_with_source": {"count": volumes_complete_source, "percent": percent(volumes_complete_source, len(volumes))},
        },
        "volume_source_breakdown": {
            "volumes_with_foaf_page": {"count": volumes_with_foaf_page, "percent": percent(volumes_with_foaf_page, len(volumes))},
            "volumes_with_dct_source": {"count": volumes_with_dct_source, "percent": percent(volumes_with_dct_source, len(volumes))},
            "volumes_with_rdfs_seeAlso": {"count": volumes_with_see_also, "percent": percent(volumes_with_see_also, len(volumes))},
        },
        "sanity": {
            "tales_created_wrong_datatype": bad_created,
        },
        "notes": {
            "tales_with_source_definition": (
                "direct: tale has dcterms:source OR dcterms:bibliographicCitation; "
                "fallback: tale dcterms:isPartOf volume AND volume has foaf:page OR dcterms:source OR rdfs:seeAlso"
            ),
            "volumes_with_source_definition": "volume has foaf:page OR dcterms:source OR rdfs:seeAlso",
            "foaf_page_iri_used": str(FOAF_PAGE),
        },
    }

    out_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
