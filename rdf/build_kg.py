
from __future__ import annotations

import argparse
import ast
import csv
import json
import os
import re
from pathlib import Path
from typing import List, Tuple

import pandas as pd
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, DCTERMS as DCT, XSD

# ---------------------------------------------------------------------
# Repo paths
# ---------------------------------------------------------------------
REPO_ROOT = Path("/Users/eugenia/Desktop/thesis/magic_tagger")

DEFAULT_INPUT_CSV = REPO_ROOT / "data" / "processed" / "corpus_a_for_kg.csv"
DEFAULT_OUT_TTL = REPO_ROOT / "rdf" / "rdf_serialization" / "corpus.ttl"

ENV_INPUT = "CORPUS_CANONICAL_CSV"
ENV_OUT = "CORPUS_VOLUMES_TTL"

# ---------------------------------------------------------------------
# Namespaces
# ---------------------------------------------------------------------
BASE = "https://github.com/eugeniavd/magic_tagger/rdf/"
RFT = Namespace("https://github.com/eugeniavd/magic_tagger/rdf/ontology/#")
PROV = Namespace("http://www.w3.org/ns/prov#")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
DCMITYPE = Namespace("http://purl.org/dc/dcmitype/")  # ✅ correct

_WS = re.compile(r"\s+")
_BAD = re.compile(r"[^a-z0-9\-]+")

# ---------------------------------------------------------------------
# IRI policy (minimal)
# ---------------------------------------------------------------------
def iri_volume(volume_id: str) -> URIRef:
    return URIRef(f"{BASE}volume/{volume_id}")

def iri_collection(collection_code: str) -> URIRef:
    return URIRef(f"{BASE}collection/{collection_code}")

def iri_person(person_id_or_slug: str) -> URIRef:
    return URIRef(f"{BASE}person/{person_id_or_slug}")

# ---------------------------------------------------------------------
# Robust IO helpers (encoding + delimiter)
# ---------------------------------------------------------------------
def read_sample_text(path: Path, n: int = 5000) -> str:
    raw = path.read_bytes()[: n * 4]
    for enc in ("utf-8-sig", "utf-8", "cp1251", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")

def detect_delimiter(path: Path) -> str:
    sample = read_sample_text(path, n=5000)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t", "|"])
        return dialect.delimiter
    except Exception:
        header = sample.splitlines()[0] if sample.splitlines() else ""
        return max([",", ";", "\t", "|"], key=lambda d: header.count(d))

def read_csv_fallback(path: Path, sep: str) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "cp1251", "cp1252", "latin-1"):
        try:
            return pd.read_csv(path, sep=sep, dtype=str, keep_default_na=False, encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(
        path, sep=sep, dtype=str, keep_default_na=False,
        encoding="utf-8", encoding_errors="replace"
    )

# ---------------------------------------------------------------------
# Value parsing / normalization
# ---------------------------------------------------------------------
def clean_ws(x: object) -> str:
    if x is None:
        return ""
    return _WS.sub(" ", str(x)).strip()

def ensure_list(x: object) -> List[str]:
    if x is None:
        return []
    if isinstance(x, list):
        return [clean_ws(v) for v in x if clean_ws(v)]
    s = clean_ws(x)
    if not s or s.lower() in {"<na>", "na", "nan", "none"}:
        return []

    # JSON
    try:
        v = json.loads(s)
        if isinstance(v, list):
            return [clean_ws(t) for t in v if clean_ws(t)]
        if isinstance(v, str):
            return [clean_ws(v)] if clean_ws(v) else []
    except Exception:
        pass

    # Python literal
    try:
        v = ast.literal_eval(s)
        if isinstance(v, list):
            return [clean_ws(t) for t in v if clean_ws(t)]
        if isinstance(v, str):
            return [clean_ws(v)] if clean_ws(v) else []
    except Exception:
        pass

    # Delimited
    parts = re.split(r"[;,|]\s*|\s{2,}", s)
    return [clean_ws(p) for p in parts if clean_ws(p)]

def slugify(s: str) -> str:
    s = clean_ws(s).lower()
    s = s.replace("_", "-").replace(" ", "-")
    s = _BAD.sub("-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "unknown"

def collection_code(raw: str) -> str:
    return slugify(raw)

# ---------------------------------------------------------------------
# Collector extraction (your exact columns)
# ---------------------------------------------------------------------
def collectors_from_row(row: pd.Series) -> List[str]:
    """
    Return collector person_ids only.
    We do NOT mint new ones from labels here, because people authority is separate.
    """
    person_ids: List[str] = []

    if "collector_person_ids" in row.index:
        person_ids = ensure_list(row.get("collector_person_ids"))

    if not person_ids and "collector_person_ids_str" in row.index:
        person_ids = ensure_list(row.get("collector_person_ids_str"))

    # drop empties
    person_ids = [clean_ws(pid) for pid in person_ids if clean_ws(pid)]
    return person_ids

# ---------------------------------------------------------------------
# Volume label from source_ref (keep "ERA, Vene 5", drop the rest)
# ---------------------------------------------------------------------
_VOL_LABEL_RE = re.compile(r"^\s*([^,]+,\s*[^,]+)\s*,\s*(\d+)\s*(?:,.*)?$")

def volume_label_from_source_ref(source_ref: str) -> str:
    s = clean_ws(source_ref)
    if not s:
        return ""
    m = _VOL_LABEL_RE.match(s)
    if m:
        series = clean_ws(m.group(1))   # "ERA, Vene"
        volno = clean_ws(m.group(2))    # "5"
        return f"{series} {volno}"
    # fallback: take everything before the 3rd comma (or before last comma)
    # safer than keeping the whole string
    parts = [p.strip() for p in s.split(",") if p.strip()]
    if len(parts) >= 2:
        # try to keep first two parts + first number-like token from the rest
        # but if we can't, just keep first two parts
        return f"{parts[0]}, {parts[1]}"
    return s

# ---------------------------------------------------------------------
# Graph builder (Volumes only)
# ---------------------------------------------------------------------
def build_volumes_graph(df: pd.DataFrame) -> Graph:
    g = Graph()

    g.bind("dcterms", DCT)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)
    g.bind("prov", PROV)
    g.bind("foaf", FOAF)
    g.bind("rft", RFT)
    g.bind("dcmitype", DCMITYPE)

    required = ["volume_id", "collection"]
    for c in required:
        if c not in df.columns:
            raise KeyError(f"Missing required column: {c}")

    df = df.copy()
    df["volume_id"] = df["volume_id"].map(clean_ws)
    df["collection"] = df["collection"].map(clean_ws)

    # first row per volume_id is enough for volume-level metadata
    vdf = df[(df["volume_id"] != "") & (df["collection"] != "")]
    vdf = vdf.drop_duplicates(subset=["volume_id"], keep="first")

    for _, row in vdf.iterrows():
        vid = row["volume_id"]
        coll_raw = row["collection"]
        coll_uri = iri_collection(collection_code(coll_raw))
        vol_uri = iri_volume(vid)

        # rdfs:label for volume from source_ref (series + volume no)
        if "source_ref" in row.index:
            lbl = volume_label_from_source_ref(row.get("source_ref"))
            if lbl:
                g.add((vol_uri, RDFS.label, Literal(lbl)))

        # volume a dcterms:BibliographicResource
        g.add((vol_uri, RDF.type, DCT.BibliographicResource))

        # dcterms:identifier from volume_id
        g.add((vol_uri, DCT.identifier, Literal(vid)))

        # dcterms:isPartOf collection
        g.add((vol_uri, DCT.isPartOf, coll_uri))

        # minimal collection node
        g.add((coll_uri, RDF.type, DCMITYPE.Collection))
        g.add((coll_uri, RDFS.label, Literal(coll_raw)))

        # IMPORTANT: do NOT add dcterms:source from source_ref (it is tale-level reference)

        # dcterms:creator from collector person IDs (links only; no agent node generation)
        for pid in collectors_from_row(row):
            g.add((vol_uri, DCT.creator, iri_person(pid)))

    return g

# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="Generate RDF (TTL) for Volume nodes from canonical table.")
    ap.add_argument("--csv", default=None, help="Input canonical_table CSV path.")
    ap.add_argument("--out", default=None, help="Output TTL path.")
    ap.add_argument("--volume-ids", default=None, help="Comma-separated volume_id list to export (optional).")
    ap.add_argument("--collection", default=None, help="Filter by collection value (e.g., 'era_vene').")
    ap.add_argument("--limit", type=int, default=None, help="Export only first N unique volumes (after filters).")

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
        raise FileNotFoundError(
            f"Input CSV not found: {csv_path}\n"
            f"Expected default: {DEFAULT_INPUT_CSV}\n"
            f"Override via --csv or env {ENV_INPUT}."
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)

    sep = detect_delimiter(csv_path)
    df = read_csv_fallback(csv_path, sep=sep)

    # filters
    if args.collection:
        df["collection"] = df["collection"].map(clean_ws)
        df = df[df["collection"] == clean_ws(args.collection)]

    if args.volume_ids:
        vids = [clean_ws(x) for x in args.volume_ids.split(",") if clean_ws(x)]
        df["volume_id"] = df["volume_id"].map(clean_ws)
        df = df[df["volume_id"].isin(vids)]

    if args.limit is not None:
        df = df.drop_duplicates(subset=["volume_id"], keep="first").head(args.limit)

    g = build_volumes_graph(df)
    out_path.write_text(g.serialize(format="turtle"), encoding="utf-8")
    print(f"Wrote: {out_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
