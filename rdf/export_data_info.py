
from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import argparse
import os
import re
from typing import List, Optional

import pandas as pd
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, DCTERMS as DCT, XSD
from src.uris import BASE_DATA, RFT

# ---------------------------------------------------------------------
# Repo paths
# ---------------------------------------------------------------------
REPO_ROOT = Path("/Users/eugenia/Desktop/thesis/magic_tagger")

DEFAULT_INPUT_CSV = REPO_ROOT / "data" / "processed" / "corpus_a_for_kg.csv"
DEFAULT_OUT_TTL = REPO_ROOT / "rdf" / "rdf_serialization" / "dataset_corpus_v1.ttl"

ENV_INPUT = "CORPUS_CANONICAL_CSV"
ENV_OUT = "CORPUS_DATASET_TTL"

# ---------------------------------------------------------------------
# Namespaces
# ---------------------------------------------------------------------

PROV = Namespace("http://www.w3.org/ns/prov#")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
DCAT = Namespace("http://www.w3.org/ns/dcat#")

_WS = re.compile(r"\s+")


def clean_ws(x: object) -> str:
    if x is None:
        return ""
    return _WS.sub(" ", str(x)).strip()


def iri_tale(tale_id: str) -> URIRef:
    return URIRef(f"{BASE_DATA}tale/{tale_id}")


def iri_dataset(dataset_id: str = "corpus/v1") -> URIRef:
    return URIRef(f"{BASE_DATA}dataset/{dataset_id}")

def iri_person(person_id_or_slug: str) -> URIRef:
    return URIRef(f"{BASE_DATA}person/{person_id_or_slug}")

def add_distribution(
    g: Graph,
    dataset_iri: URIRef,
    dist_id: str,
    title_en: str,
    access_url: str,
    download_url: Optional[str],
    media_type: str,
) -> URIRef:
    """
    Create a dcat:Distribution and attach to dataset via dcat:distribution.
    """
    dist_iri = URIRef(f"{BASE_DATA}distribution/corpus/v1/{dist_id}")

    g.add((dist_iri, RDF.type, DCAT.Distribution))
    g.add((dist_iri, DCT.title, Literal(title_en, lang="en")))
    g.add((dist_iri, DCT.format, Literal(media_type)))

    # Access URL 
    g.add((dist_iri, DCAT.accessURL, URIRef(access_url)))

    # Download URL 
    if download_url:
        g.add((dist_iri, DCAT.downloadURL, URIRef(download_url)))

    g.add((dataset_iri, DCAT.distribution, dist_iri))
    return dist_iri


def main() -> int:
    ap = argparse.ArgumentParser(description="Build dataset-level DCAT metadata for corpus/v1 + tale->dataset membership links.")
    ap.add_argument("--csv", default=None, help="Input canonical corpus CSV (must include tale_id).")
    ap.add_argument("--out", default=None, help="Output TTL path for dataset metadata + membership triples.")
    ap.add_argument("--year", default="2026", help="Issued year (xsd:gYear), default 2026.")
    ap.add_argument(
        "--derived-from",
        default=None,
        help="Optional | separated URLs for prov:wasDerivedFrom (e.g. Kivike collection pages).",
    )

    args = ap.parse_args()

    csv_path = Path(
        args.csv
        or os.environ.get(ENV_INPUT, "")
        or str(DEFAULT_INPUT_CSV)
    ).expanduser().resolve()

    out_path = Path(
        args.out
        or os.environ.get(ENV_OUT, "")
        or str(DEFAULT_OUT_TTL)
    ).expanduser().resolve()

    if not csv_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {csv_path}")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Read CSV (robust enough for your canonical table)
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False, encoding="utf-8", encoding_errors="replace")
    if "tale_id" not in df.columns:
        raise KeyError("CSV must contain 'tale_id' column")

    # Prepare graph
    g = Graph()
    g.bind("dcterms", DCT)
    g.bind("dcat", DCAT)
    g.bind("prov", PROV)
    g.bind("foaf", FOAF)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)

    dataset = iri_dataset("corpus/v1")

    # --- Agent (publisher/creator)

    me = iri_person("evgeniia-vdovichenko")
    g.add((me, RDF.type, FOAF.Person))
    g.add((me, RDF.type, PROV.Agent))
    g.add((me, RDFS.label, Literal("Evgeniia Vdovichenko")))

    # --- Dataset core
    g.add((dataset, RDF.type, DCAT.Dataset))
    g.add((dataset, DCT.title, Literal("Corpus v1", lang="en")))
    g.add((
        dataset,
        DCT.description,
        Literal(
            "A curated corpus of Russian-language magic folktales from the Estonian Folklore Archives "
            "(Estonian Literary Museum, Tartu), modeled as a knowledge graph with linked agents, "
            "bibliographic volumes/collections, and ATU tale type concepts.",
            lang="en",
        ),
    ))

    # creator / publisher as agent resources 
    g.add((dataset, DCT.creator, me))
    g.add((dataset, DCT.publisher, me))

    # license
    g.add((dataset, DCT.license, URIRef("https://creativecommons.org/licenses/by/4.0/")))

    # source (your canonical CSV in repo)
    g.add((dataset, DCT.source, URIRef("https://github.com/eugeniavd/magic_tagger/blob/main/data/processed/corpus_a_for_kg.csv")))

    # accessRights (PUBLIC)
    g.add((dataset, DCT.accessRights, URIRef("http://publications.europa.eu/resource/authority/access-right/PUBLIC")))

    # issued year
    year = clean_ws(args.year)
    if year:
        g.add((dataset, DCAT.issued, Literal(year, datatype=XSD.gYear)))

    # keywords (multilingual)
    g.add((dataset, DCAT.keyword, Literal("folktale", lang="en")))
    g.add((dataset, DCAT.keyword, Literal("fairytale", lang="en")))
    g.add((dataset, DCAT.keyword, Literal("ATU types", lang="en")))
    g.add((dataset, DCAT.keyword, Literal("сказка", lang="ru")))

    # theme: CULT (Culture)
    g.add((dataset, DCAT.theme, URIRef("https://publications.europa.eu/resource/authority/data-theme/CULT")))

    # language (BCP47 tags as literals)
    g.add((dataset, DCT.language, Literal("en")))
    g.add((dataset, DCT.language, Literal("ru")))
    g.add((dataset, DCT.language, Literal("et")))

    # spatial (IRI)
    g.add((dataset, DCT.spatial, URIRef("http://www.wikidata.org/entity/Q191")))  # Estonia
    g.add((dataset, DCT.spatial, URIRef("http://www.wikidata.org/entity/Q159")))  # Russia

    # prov:wasDerivedFrom 
    if args.derived_from:
        for u in [x.strip() for x in args.derived_from.split("|") if x.strip()]:
            g.add((dataset, PROV.wasDerivedFrom, URIRef(u)))
    else:
       
        g.add((dataset, PROV.wasDerivedFrom, URIRef("https://kivike.kirmus.ee/")))

    # --- Distributions
    # Repo landing paths (accessURL) + raw (downloadURL)
   
    repo_blob_base = "https://github.com/eugeniavd/magic_tagger/blob/main"
    repo_raw_base = "https://raw.githubusercontent.com/eugeniavd/magic_tagger/main"

    add_distribution(
        g, dataset,
        dist_id="corpus-ttl",
        title_en="Corpus graph (Turtle)",
        access_url=f"{repo_blob_base}/rdf/rdf_serialization/corpus.ttl",
        download_url=f"{repo_raw_base}/rdf/rdf_serialization/corpus.ttl",
        media_type="text/turtle",
    )
    add_distribution(
        g, dataset,
        dist_id="biblio-ttl",
        title_en="Bibliographic sources graph (Turtle)",
        access_url=f"{repo_blob_base}/rdf/rdf_serialization/biblio_sources.ttl",
        download_url=f"{repo_raw_base}/rdf/rdf_serialization/biblio_sources.ttl",
        media_type="text/turtle",
    )
    add_distribution(
        g, dataset,
        dist_id="types-ttl",
        title_en="Tale type concepts graph (Turtle)",
        access_url=f"{repo_blob_base}/rdf/rdf_serialization/types.ttl",
        download_url=f"{repo_raw_base}/rdf/rdf_serialization/types.ttl",
        media_type="text/turtle",
    )
    
    add_distribution(
        g, dataset,
        dist_id="agents-ttl",
        title_en="Agents graph (Turtle)",
        access_url=f"{repo_blob_base}/rdf/rdf_serialization/agents.ttl",
        download_url=f"{repo_raw_base}/rdf/rdf_serialization/agents.ttl",
        media_type="text/turtle",
    )
    # SHACL shapes 
    add_distribution(
        g, dataset,
        dist_id="shacl-ttl",
        title_en="SHACL shapes (Turtle)",
        access_url=f"{repo_blob_base}/rdf/shacl/shapes.ttl",
        download_url=f"{repo_raw_base}/rdf/shacl/shapes.ttl",
        media_type="text/turtle",
    )
    # Queries bundle
    add_distribution(
        g, dataset,
        dist_id="queries-bundle",
        title_en="SPARQL queries bundle (repository folder)",
        access_url=f"{repo_blob_base}/rdf/queries",
        download_url=None,
        media_type="text/sparql",
    )
    # Canonical CSV itself as a distribution
    add_distribution(
        g, dataset,
        dist_id="canonical-csv",
        title_en="Canonical table (CSV)",
        access_url=f"{repo_blob_base}/data/processed/corpus_a_for_kg.csv",
        download_url=f"{repo_raw_base}/data/processed/corpus_a_for_kg.csv",
        media_type="text/csv",
    )

    # --- Membership: tale dcterms:isPartOf dataset
    tale_ids: List[str] = (
        df["tale_id"].map(clean_ws)
        .loc[lambda s: s.ne("")]
        .drop_duplicates()
        .tolist()
    )
    for tid in tale_ids:
        g.add((iri_tale(tid), DCT.isPartOf, dataset))

    out_path.write_text(g.serialize(format="turtle"), encoding="utf-8")
    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
