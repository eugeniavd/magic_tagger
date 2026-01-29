from __future__ import annotations
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import argparse
import csv
import os
import re

import pandas as pd
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, XSD, DCTERMS as DCT
from src.uris import BASE_DATA, RFT

# ---------------------------------------------------------------------
# Repo paths
# ---------------------------------------------------------------------
repo_root = Path("/Users/eugenia/Desktop/thesis/magic_tagger")

DEFAULT_INPUT_CSV = repo_root / "data" / "processed" / "atu_reference.csv"
DEFAULT_OUT_TTL = repo_root / "rdf" / "rdf_serialization" / "atu_types.ttl"

ENV_INPUT = "ATU_REF_CSV"
ENV_OUT = "ATU_OUT_TTL"

# ---------------------------------------------------------------------
# Namespaces (project)
# ---------------------------------------------------------------------
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
PROV = Namespace("http://www.w3.org/ns/prov#")

# ---------------------------------------------------------------------
# Bibliographic sources
# ---------------------------------------------------------------------
BIBLIO_SET_IRI = f"{BASE_DATA}biblio/ffc_284-286_2011_uther"
BIBLIO_VOL1_IRI = f"{BASE_DATA}biblio/ffc_284_2011"  # < 1000
BIBLIO_VOL2_IRI = f"{BASE_DATA}biblio/ffc_285_2011"  # >= 1000

SCHEME_LABEL_EN = "THE TYPES OF INTERNATIONAL FOLKTALES Based on the System of Antti Aarne and Stith Thompson"

# ---------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------
CYR_TO_LAT = str.maketrans({
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H",
    "О": "O", "Р": "P", "С": "C", "Т": "T", "Х": "X", "У": "Y",
    "а": "A", "в": "B", "е": "E", "к": "K", "м": "M", "н": "H",
    "о": "O", "р": "P", "с": "C", "т": "T", "х": "X", "у": "Y",
})

_WS = re.compile(r"\s+")

def clean_ws(x: object) -> str:
    if x is None:
        return ""
    return _WS.sub(" ", str(x)).strip()

def norm_code_for_notation(x: object) -> str:
    """
    Keep stars and suffixes as-is (after basic cleanup).
    Used for skos:notation.
    """
    s = clean_ws(x)
    if not s or s.lower() in {"<na>", "nan", "none"}:
        return ""
    return s.translate(CYR_TO_LAT).replace(" ", "").upper()

def normalize_code_for_iri(code: str, star_policy: str = "hyphen") -> str:
    """
    Used for minted IRI path segment.
    star_policy:
      - "hyphen": '*' -> '-star' (readable, stable)
      - "percent": '*' -> '%2A'
    """
    c = norm_code_for_notation(code)
    if not c:
        return ""
    if star_policy == "hyphen":
        c = c.replace("*", "-star")
    elif star_policy == "percent":
        c = c.replace("*", "%2A")
    else:
        raise ValueError("star_policy must be 'hyphen' or 'percent'")
    return c

def iri_atu(code: str, star_policy: str = "hyphen") -> URIRef:
    seg = normalize_code_for_iri(code, star_policy=star_policy)
    return URIRef(f"{BASE_DATA}taleType/atu/{seg}")

def detect_delimiter(path: Path) -> str:
    sample = path.read_text(encoding="utf-8")[:5000]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t", "|"])
        return dialect.delimiter
    except Exception:
        header = sample.splitlines()[0] if sample.splitlines() else ""
        candidates = [",", ";", "\t", "|"]
        return max(candidates, key=lambda d: header.count(d))

def sort_key(code: str):
    base = re.sub(r"\*+$", "", code)
    stars = len(code) - len(base)
    m = re.match(r"^(\d+)(.*)$", base)
    if not m:
        return (10**9, base, stars)
    return (int(m.group(1)), m.group(2), stars)

def numeric_prefix(code: str) -> int:
    """
    Extract numeric prefix from a normalized ATU code.
    Ignores trailing stars and letter suffixes for numeric thresholding.
    Examples:
      '999A' -> 999
      '1000' -> 1000
      '1060*' -> 1060
      '677***' -> 677
    """
    c = norm_code_for_notation(code)
    if not c:
        return 10**9
    base = re.sub(r"\*+$", "", c)
    m = re.match(r"^(\d+)", base)
    if not m:
        return 10**9
    return int(m.group(1))

def source_for_code(code: str) -> URIRef:
    """
    Rule:
      - numeric part < 1000 -> vol 1 (FFC 284)
      - numeric part >= 1000 -> vol 2 (FFC 285)
    """
    return URIRef(BIBLIO_VOL2_IRI) if numeric_prefix(code) >= 1000 else URIRef(BIBLIO_VOL1_IRI)

# ---------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------
def build_graph(
    df: pd.DataFrame,
    *,
    star_policy: str = "hyphen",
    scheme_label_en: str = SCHEME_LABEL_EN,
    biblio_set_iri: str = BIBLIO_SET_IRI,
) -> Graph:
    g = Graph()

    # Prefixes
    g.bind("rft", RFT)
    g.bind("skos", SKOS)
    g.bind("dcterms", DCT)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)
    g.bind("prov", PROV)

    # Validate columns
    if "code" not in df.columns:
        raise KeyError("CSV must contain a 'code' column")

    if "title_en" not in df.columns:
        df["title_en"] = ""
    if "desc_en" not in df.columns:
        df["desc_en"] = ""

    df = df.copy()
    df["code"] = df["code"].map(norm_code_for_notation)
    df["title_en"] = df["title_en"].map(clean_ws)
    df["desc_en"] = df["desc_en"].map(clean_ws)

    df = df[df["code"].ne("")].drop_duplicates(subset=["code"], keep="first")
    df = df.sort_values(by="code", key=lambda s: s.map(sort_key), kind="mergesort")

    scheme = RFT.ATU_Scheme
    set_src = URIRef(biblio_set_iri)

    # --- Scheme triples (source points to the SET)
    g.add((scheme, RDF.type, SKOS.ConceptScheme))
    g.add((scheme, SKOS.prefLabel, Literal(scheme_label_en, lang="en")))
    g.add((scheme, DCT.source, set_src))

    # --- Concepts
    for _, row in df.iterrows():
        code = row["code"]
        title = (row.get("title_en") or "").strip()
        desc = (row.get("desc_en") or "").strip()

        concept = iri_atu(code, star_policy=star_policy)

        g.add((concept, RDF.type, SKOS.Concept))
        g.add((concept, RDF.type, RFT.TaleType))

        g.add((concept, SKOS.inScheme, scheme))
        g.add((concept, SKOS.notation, Literal(code)))

        # Concept-level provenance: vol 1 for <1000, vol 2 for >=1000
        g.add((concept, DCT.source, source_for_code(code)))

        pref = f"ATU {code} {title}".strip() if title else f"ATU {code}"
        g.add((concept, SKOS.prefLabel, Literal(pref, lang="en")))

        if desc:
            g.add((concept, SKOS.definition, Literal(desc, lang="en")))

    return g

# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="Generate ATU SKOS vocabulary TTL from atu_reference CSV.")
    ap.add_argument("--csv", default=None, help="Input CSV path (optional if ENV/DEFAULT is set).")
    ap.add_argument("--out", default=None, help="Output TTL path (optional if ENV/DEFAULT is set).")
    ap.add_argument("--star-policy", choices=["hyphen", "percent"], default="hyphen")
    ap.add_argument("--scheme-label", default=SCHEME_LABEL_EN)
    ap.add_argument("--biblio-set-iri", default=BIBLIO_SET_IRI)

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
    df = pd.read_csv(csv_path, sep=sep, dtype=str, keep_default_na=False)

    g = build_graph(
        df,
        star_policy=args.star_policy,
        scheme_label_en=args.scheme_label,
        biblio_set_iri=args.biblio_set_iri,
    )

    out_path.write_text(g.serialize(format="turtle"), encoding="utf-8")
    print(f"Wrote: {out_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
