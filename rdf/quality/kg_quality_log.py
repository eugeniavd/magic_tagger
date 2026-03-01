from __future__ import annotations
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import argparse
import json
from datetime import datetime, timezone
from typing import Dict, Set, Iterable

from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS, DCTERMS as DCT, XSD
from src.uris import BASE_DATA

# --- core IRIs ---
FOAF_PAGE = URIRef("http://xmlns.com/foaf/0.1/page")

CRM_E33 = URIRef("http://www.cidoc-crm.org/cidoc-crm/E33_Linguistic_Object")
DCMITYPE_COLLECTION = URIRef("http://purl.org/dc/dcmitype/Collection")

# --- PROV + LoC roles (MUST match your new serialization) ---
PROV = URIRef("http://www.w3.org/ns/prov#")  # unused as Namespace; keep for base if needed
PROV_NS = URIRef("http://www.w3.org/ns/prov#")

# Use URIRefs explicitly (robust in scripts)
PROV_ENTITY = URIRef("http://www.w3.org/ns/prov#Entity")
PROV_ATTRIBUTION = URIRef("http://www.w3.org/ns/prov#Attribution")
PROV_AGENT_P = URIRef("http://www.w3.org/ns/prov#agent")
PROV_HAD_ROLE = URIRef("http://www.w3.org/ns/prov#hadRole")
PROV_QUAL_ATTR = URIRef("http://www.w3.org/ns/prov#qualifiedAttribution")

LOCREL = URIRef("http://id.loc.gov/vocabulary/relators/")
ROLE_NARRATOR = URIRef("http://id.loc.gov/vocabulary/relators/nrt")
ROLE_COLLECTOR = URIRef("http://id.loc.gov/vocabulary/relators/col")


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


def attributions_of_entity(g: Graph, entity: URIRef) -> Set[URIRef]:
    """Return attribution nodes linked from entity via prov:qualifiedAttribution."""
    return {o for _, _, o in g.triples((entity, PROV_QUAL_ATTR, None)) if isinstance(o, URIRef)}


def has_role_attribution(g: Graph, entity: URIRef, role: URIRef) -> bool:
    """True if entity has any prov:qualifiedAttribution node with prov:hadRole = role."""
    for _, _, att in g.triples((entity, PROV_QUAL_ATTR, None)):
        if (att, PROV_HAD_ROLE, role) in g:
            return True
    return False


def agents_in_role_attributions(g: Graph, entity: URIRef, role: URIRef) -> Set[URIRef]:
    """Return prov:agent URIs for entity's attributions matching a given role."""
    out: Set[URIRef] = set()
    for _, _, att in g.triples((entity, PROV_QUAL_ATTR, None)):
        if (att, PROV_HAD_ROLE, role) not in g:
            continue
        for _, _, ag in g.triples((att, PROV_AGENT_P, None)):
            if isinstance(ag, URIRef):
                out.add(ag)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Compute KG quality log metrics for a TTL graph.")
    ap.add_argument("--ttl", default="rdf/rdf_serialization/corpus.ttl", help="Input TTL path")
    ap.add_argument("--out", default="rdf/quality/quality_log.json", help="Output JSON metrics log")
    ap.add_argument(
        "--base",
        default=BASE_DATA,
        help="BASE_DATA IRI prefix for heuristics (reserved; not required by current metrics).",
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

    # Optional debug: confirm that foaf:page is present
    if args.debug_volume:
        v = URIRef(args.debug_volume.strip())
        print("DEBUG volume:", v)
        print("DEBUG foaf:page triples:", list(g.triples((v, FOAF_PAGE, None)))[:10])
        print("DEBUG dct:source triples:", list(g.triples((v, DCT.source, None)))[:10])
        print("DEBUG rdfs:seeAlso triples:", list(g.triples((v, RDFS.seeAlso, None)))[:10])
        print("DEBUG qualifiedAttribution:", list(g.triples((v, PROV_QUAL_ATTR, None)))[:10])

    # ---- entity sets ----
    tales = subjects_of_type(g, CRM_E33)  # crm:E33_Linguistic_Object
    volumes = {s for s, _, _ in g.triples((None, RDF.type, DCT.BibliographicResource)) if isinstance(s, URIRef)}
    collections = {s for s, _, _ in g.triples((None, RDF.type, DCMITYPE_COLLECTION)) if isinstance(s, URIRef)}

    # referenced ATU concepts = unique IRIs in dcterms:subject (objects)
    atu_refs = {o for _, _, o in g.triples((None, DCT.subject, None)) if isinstance(o, URIRef)}

    # referenced agents (persons) now come from PROV attribution nodes (prov:agent)
    person_refs: Set[URIRef] = {o for _, _, o in g.triples((None, PROV_AGENT_P, None)) if isinstance(o, URIRef)}

    # also count attribution nodes explicitly (helps sanity)
    attribution_nodes: Set[URIRef] = {s for s, _, _ in g.triples((None, RDF.type, PROV_ATTRIBUTION)) if isinstance(s, URIRef)}

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
    tales_with_spatial = len({s for s, _, _ in g.triples((None, DCT.spatial, None)) if s in tales})

    # NEW: narrator coverage via PROV qualified attribution + role locrel:nrt
    tales_with_narrator_attr = sum(1 for t in tales if has_role_attribution(g, t, ROLE_NARRATOR))

    # NEW: collector coverage on volumes via PROV qualified attribution + role locrel:col
    volumes_with_collector_attr = sum(1 for v in volumes if has_role_attribution(g, v, ROLE_COLLECTOR))

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
    # (still valid after your KG changes)
    # -------------------------
    TALE_RIGHTS_PREDS = (DCT.accessRights, DCT.rights)
    TALE_SOURCE_PREDS = (DCT.source, DCT.bibliographicCitation)
    VOL_SOURCE_PREDS = (FOAF_PAGE, DCT.source, RDFS.seeAlso)

    tales_complete_rights = sum(1 for t in tales if has_any_predicate(g, t, TALE_RIGHTS_PREDS))
    tales_complete_date = sum(1 for t in tales if has_any_predicate(g, t, (DCT.created,)))
    tales_complete_place = sum(1 for t in tales if has_any_predicate(g, t, (DCT.spatial,)))

    tales_complete_source = 0
    for t in tales:
        # direct source/citation on tale
        if has_any_predicate(g, t, TALE_SOURCE_PREDS):
            tales_complete_source += 1
            continue

        # fallback: isPartOf volume + volume has source page
        vols = objects_iris(g, t, DCT.isPartOf)
        if vols and any(has_any_predicate(g, v, VOL_SOURCE_PREDS) for v in vols):
            tales_complete_source += 1

    volumes_complete_source = sum(1 for v in volumes if has_any_predicate(g, v, VOL_SOURCE_PREDS))

    # breakdown
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
            "attribution_nodes": len(attribution_nodes),
        },
        "coverage": {
            "tales_with_isPartOf_volume": {"count": tales_is_part_of, "percent": percent(tales_is_part_of, len(tales))},
            "tales_with_atu_subject": {"count": tales_with_atu, "percent": percent(tales_with_atu, len(tales))},
            "tales_with_created": {"count": tales_with_created, "percent": percent(tales_with_created, len(tales))},
            "tales_with_accessRights": {"count": tales_with_access, "percent": percent(tales_with_access, len(tales))},
            "tales_with_rights": {"count": tales_with_rights, "percent": percent(tales_with_rights, len(tales))},
            "tales_with_spatial": {"count": tales_with_spatial, "percent": percent(tales_with_spatial, len(tales))},
            "tales_with_narrator_attribution_locrel_nrt": {
                "count": tales_with_narrator_attr,
                "percent": percent(tales_with_narrator_attr, len(tales)),
            },
            "volumes_with_collector_attribution_locrel_col": {
                "count": volumes_with_collector_attr,
                "percent": percent(volumes_with_collector_attr, len(volumes)),
            },
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
            "tales_with_narrator_definition": (
                "tale has prov:qualifiedAttribution node where prov:hadRole = locrel:nrt and prov:agent is a URI"
            ),
            "volumes_with_collector_definition": (
                "volume has prov:qualifiedAttribution node where prov:hadRole = locrel:col and prov:agent is a URI"
            ),
            "tales_with_source_definition": (
                "direct: tale has dcterms:source OR dcterms:bibliographicCitation; "
                "fallback: tale dcterms:isPartOf volume AND volume has foaf:page OR dcterms:source OR rdfs:seeAlso"
            ),
            "volumes_with_source_definition": "volume has foaf:page OR dcterms:source OR rdfs:seeAlso",
            "foaf_page_iri_used": str(FOAF_PAGE),
            "role_uris_used": {"locrel:nrt": str(ROLE_NARRATOR), "locrel:col": str(ROLE_COLLECTOR)},
        },
    }

    out_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())