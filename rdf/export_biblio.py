from __future__ import annotations

import os
from pathlib import Path

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, DCTERMS as DCT, XSD

# -----------------------------
# Repo paths
# -----------------------------
repo_root = Path("/Users/eugenia/Desktop/thesis/magic_tagger")
OUT_TTL = repo_root / "rdf" / "rdf_serialization" / "biblio_sources.ttl"

ENV_OUT = "BIBLIO_OUT_TTL"

# -----------------------------
# Namespaces
# -----------------------------
BASE = "https://github.com/eugeniavd/magic_tagger/rdf/"
RFT = Namespace("https://github.com/eugeniavd/magic_tagger/rdf/ontology/#")
PROV = Namespace("http://www.w3.org/ns/prov#")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")

# -----------------------------
# Authority record data
# -----------------------------
BIBLIO_SET = {
    "id": "biblio/ffc_284-286_2011_uther",
    "label_en": "FFC 284–286 (2011): The Types of International Folktales – A Classification and Bibliography",
    "citation_en": (
        "Folklore Fellows’ Communications (FFC) 284–286. "
        "Sastamala: Vammalan Kirjapaino Oy, 2011. First published in 2004."
    ),
    # Set-level landing page (the set as a whole)
    "see_also_set": [
        "https://edition.fi/kalevalaseura/catalog/view/763/715/2750-1",
    ],
    "identifiers_set": [],
    "contributors": [],

    # Volumes as parts with per-volume edition.fi + per-volume WorldCat (and OCLC)
    "parts": [
        {
            "id": "biblio/ffc_284_2011",
            "label_en": "FFC 284 (2011): Animal Tales, Tales of Magic, Religious Tales, and Realistic Tales",
            "oclc": "974404961",
            "see_also": [
                "https://edition.fi/kalevalaseura/catalog/book/763",
                "https://search.worldcat.org/it/title/974404961",
            ],
            # "isbn": "978-951-41-1054-2",
        },
        {
            "id": "biblio/ffc_285_2011",
            "label_en": "FFC 285 (2011): Tales of the Stupid Ogre, Anecdotes and Jokes, and Formula Tales",
            "oclc": "974406311",
            "see_also": [
                "https://edition.fi/kalevalaseura/catalog/book/765",
                "https://search.worldcat.org/it/title/974406311",
            ],
            # "isbn": "978-951-41-1055-9",
        },
        {
            "id": "biblio/ffc_286_2011",
            "label_en": "FFC 286 (2011): Appendices",
            "oclc": "974415887",
            "see_also": [
                "https://edition.fi/kalevalaseura/catalog/book/769",
                "https://search.worldcat.org/it/title/974415887",
            ],
            # "isbn": "978-951-41-1067-2",
        },
    ],
}


def iri(local_path: str) -> URIRef:
    return URIRef(f"{BASE}{local_path.lstrip('/')}")


def add_person(g: Graph, person_id: str, name: str) -> URIRef:
    p = iri(person_id)
    g.add((p, RDF.type, FOAF.Person))
    g.add((p, FOAF.name, Literal(name)))
    return p


def add_see_also(g: Graph, subj: URIRef, urls) -> None:
    if not urls:
        return
    if isinstance(urls, str):
        urls = [urls]
    for u in urls:
        u = (u or "").strip()
        if u:
            g.add((subj, RDFS.seeAlso, URIRef(u)))


def add_identifier(g: Graph, subj: URIRef, value: str) -> None:
    v = (value or "").strip()
    if v:
        g.add((subj, DCT.identifier, Literal(v)))


def build_graph() -> Graph:
    g = Graph()

    # Prefixes
    g.bind("dcterms", DCT)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)
    g.bind("prov", PROV)
    g.bind("foaf", FOAF)
    g.bind("rft", RFT)

    set_uri = iri(BIBLIO_SET["id"])

    # --- The set (FFC 284–286 as a whole)
    g.add((set_uri, RDF.type, DCT.BibliographicResource))
    g.add((set_uri, RDF.type, PROV.Entity))
    g.add((set_uri, RDFS.label, Literal(BIBLIO_SET["label_en"], lang="en")))
    g.add((set_uri, DCT.bibliographicCitation, Literal(BIBLIO_SET["citation_en"], lang="en")))

    add_see_also(g, set_uri, BIBLIO_SET.get("see_also_set", []))

    for ident in BIBLIO_SET.get("identifiers_set", []):
        add_identifier(g, set_uri, ident)

    # contributors (optional)
    for c in BIBLIO_SET.get("contributors", []):
        pid = (c.get("id") or "").strip()
        pname = (c.get("name") or "").strip()
        role = (c.get("role") or "").strip().lower()
        if not pid or not pname:
            continue
        p_uri = add_person(g, pid, pname)
        if role == "creator":
            g.add((set_uri, DCT.creator, p_uri))
        elif role == "publisher":
            g.add((set_uri, DCT.publisher, p_uri))
        else:
            g.add((set_uri, DCT.contributor, p_uri))

    # --- Parts linked to the set, each with its own OCLC + pages
    for part in BIBLIO_SET.get("parts", []):
        part_uri = iri(part["id"])

        g.add((part_uri, RDF.type, DCT.BibliographicResource))
        g.add((part_uri, RDF.type, PROV.Entity))
        g.add((part_uri, RDFS.label, Literal(part["label_en"], lang="en")))

        # membership
        g.add((part_uri, DCT.isPartOf, set_uri))
        g.add((set_uri, DCT.hasPart, part_uri))

        # per-volume pages (edition.fi + worldcat)
        add_see_also(g, part_uri, part.get("see_also"))

        # per-volume IDs
        if part.get("oclc"):
            add_identifier(g, part_uri, f"OCLC:{part['oclc']}")

        if part.get("isbn"):
            add_identifier(g, part_uri, f"ISBN:{part['isbn']}")

    return g


def main() -> int:
    out_path = Path(os.environ.get(ENV_OUT, str(OUT_TTL))).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    g = build_graph()
    out_path.write_text(g.serialize(format="turtle"), encoding="utf-8")

    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
