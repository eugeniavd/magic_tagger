
from __future__ import annotations

import argparse
import ast
import csv
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, DCTERMS as DCT, XSD

# ---------------------------------------------------------------------
# Repo paths
# ---------------------------------------------------------------------
REPO_ROOT = Path("/Users/eugenia/Desktop/thesis/magic_tagger")

DEFAULT_INPUT_CSV = REPO_ROOT / "data" / "processed" / "corpus_a_for_kg.csv"
DEFAULT_OUT_TTL = REPO_ROOT / "rdf" / "rdf_serialization" / "agents.ttl"

ENV_INPUT = "CORPUS_CANONICAL_CSV"
ENV_OUT = "CORPUS_AGENTS_TTL"

# ---------------------------------------------------------------------
# Namespaces
# ---------------------------------------------------------------------
BASE = "https://github.com/eugeniavd/magic_tagger/rdf/"
RFT = Namespace("https://github.com/eugeniavd/magic_tagger/rdf/ontology/#")
PROV = Namespace("http://www.w3.org/ns/prov#")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
CRM = Namespace("http://www.cidoc-crm.org/cidoc-crm/")

_WS = re.compile(r"\s+")
_CYR = re.compile(r"[\u0400-\u04FF]")  # Cyrillic block

# ---------------------------------------------------------------------
# IRI policy
# ---------------------------------------------------------------------
def iri_person(person_id: str) -> URIRef:
    return URIRef(f"{BASE}person/{person_id}")

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
        path,
        sep=sep,
        dtype=str,
        keep_default_na=False,
        encoding="utf-8",
        encoding_errors="replace",
    )

# ---------------------------------------------------------------------
# Normalization / parsing
# ---------------------------------------------------------------------
def clean_ws(x: object) -> str:
    if x is None:
        return ""
    return _WS.sub(" ", str(x)).strip()

def ensure_list(x: object) -> List[str]:
    """
    Accepts:
      - python-list string: "['a','b']"
      - json list string: '["a","b"]'
      - single string
      - comma/semicolon/pipe separated string
    """
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

    # Delimited fallback
    parts = re.split(r"[;,|]\s*|\s{2,}", s)
    return [clean_ws(p) for p in parts if clean_ws(p)]

def guess_lang(s: str) -> str:
    s = clean_ws(s)
    if not s:
        return ""
    return "ru" if _CYR.search(s) else "et"

def lit_lang(s: str) -> Optional[Literal]:
    s = clean_ws(s)
    if not s:
        return None
    return Literal(s, lang=guess_lang(s))

def to_gyear(y: str) -> Optional[Literal]:
    y = clean_ws(y)
    if not y:
        return None
    m = re.search(r"\b(\d{4})\b", y)
    if not m:
        return None
    return Literal(m.group(1), datatype=XSD.gYear)

def to_int(x: str) -> Optional[Literal]:
    x = clean_ws(x)
    if not x:
        return None
    m = re.search(r"\b(\d+)\b", x)
    if not m:
        return None
    return Literal(int(m.group(1)), datatype=XSD.integer)

# ---------------------------------------------------------------------
# Extractors (YOUR exact columns)
# ---------------------------------------------------------------------
NARRATOR_ID_COL = "narrator_person_id"
NARRATOR_LABEL_EN_COL = "narrator_label_en"
NARRATOR_BIRTH_YEAR_COL = "narrator_birth_year"
NARRATOR_AGE_COL = "narrator_age"
NARRATOR_NOTE_RAW_COL = "narrator_note_raw"
NARRATOR_NAME_RAW_COL = "narrator_name_raw"

COLLECTOR_IDS_COL = "collector_person_ids_str"
COLLECTOR_LABELS_COL = "collectors_norm"

def extract_narrator_id(row: pd.Series) -> str:
    return clean_ws(row.get(NARRATOR_ID_COL)) if NARRATOR_ID_COL in row.index else ""

def extract_narrator_fields(row: pd.Series) -> Dict[str, str]:
    return {
        "label_en": clean_ws(row.get(NARRATOR_LABEL_EN_COL)) if NARRATOR_LABEL_EN_COL in row.index else "",
        "birth_year": clean_ws(row.get(NARRATOR_BIRTH_YEAR_COL)) if NARRATOR_BIRTH_YEAR_COL in row.index else "",
        "age": clean_ws(row.get(NARRATOR_AGE_COL)) if NARRATOR_AGE_COL in row.index else "",
        "note_raw": clean_ws(row.get(NARRATOR_NOTE_RAW_COL)) if NARRATOR_NOTE_RAW_COL in row.index else "",
        "name_raw": clean_ws(row.get(NARRATOR_NAME_RAW_COL)) if NARRATOR_NAME_RAW_COL in row.index else "",
    }

def extract_collectors(row: pd.Series) -> Tuple[List[str], List[str]]:
    """
    Returns (collector_ids, collector_labels).

    IDs: collector_person_ids_str (list-like string)
    Labels: collectors_norm (list-like string)
    """
    ids: List[str] = []
    labels: List[str] = []

    if COLLECTOR_IDS_COL in row.index:
        ids = ensure_list(row.get(COLLECTOR_IDS_COL))

    if COLLECTOR_LABELS_COL in row.index:
        labels = ensure_list(row.get(COLLECTOR_LABELS_COL))

    ids = [clean_ws(x) for x in ids if clean_ws(x)]
    labels = [clean_ws(x) for x in labels if clean_ws(x)]
    return ids, labels

# ---------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------
def build_agents_graph(df: pd.DataFrame) -> Graph:
    g = Graph()
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)
    g.bind("dcterms", DCT)
    g.bind("prov", PROV)
    g.bind("foaf", FOAF)
    g.bind("crm", CRM)
    g.bind("rft", RFT)

    narrator_ids: Set[str] = set()
    collector_ids: Set[str] = set()

    narrator_meta: Dict[str, Dict[str, str]] = {}
    collector_labels_by_id: Dict[str, Set[str]] = {}

    for _, row in df.iterrows():
        # Narrators
        nid = extract_narrator_id(row)
        if nid:
            narrator_ids.add(nid)
            meta = extract_narrator_fields(row)
            if nid not in narrator_meta:
                narrator_meta[nid] = meta
            else:
                # fill only missing
                for k, v in meta.items():
                    if v and not narrator_meta[nid].get(k):
                        narrator_meta[nid][k] = v

        # Collectors
        cids, clabels = extract_collectors(row)
        for cid in cids:
            collector_ids.add(cid)
            collector_labels_by_id.setdefault(cid, set())

        # Attach labels to ids when possible
        if cids and clabels:
            if len(cids) == len(clabels):
                for cid, lab in zip(cids, clabels):
                    if lab:
                        collector_labels_by_id.setdefault(cid, set()).add(lab)
            else:
                # if mismatch, add all labels to all ids (conservative)
                for cid in cids:
                    for lab in clabels:
                        if lab:
                            collector_labels_by_id.setdefault(cid, set()).add(lab)

    all_ids = sorted(narrator_ids.union(collector_ids))

    for pid in all_ids:
        p_uri = iri_person(pid)

        # Core typing
        g.add((p_uri, RDF.type, PROV.Agent))
        g.add((p_uri, RDF.type, CRM.E21_Person))
        g.add((p_uri, RDF.type, FOAF.Person))

        # Role typing (query-friendly)
        if pid in narrator_ids:
            g.add((p_uri, RDF.type, RFT.Narrator))
        if pid in collector_ids:
            g.add((p_uri, RDF.type, RFT.Collector))

        # Narrator-rich metadata
        if pid in narrator_meta:
            meta = narrator_meta.get(pid, {})

            lab_en = clean_ws(meta.get("label_en", ""))
            if lab_en:
                g.add((p_uri, RDFS.label, Literal(lab_en, lang="en")))

            name_raw = clean_ws(meta.get("name_raw", ""))
            if name_raw:
                l = lit_lang(name_raw)
                if l is not None:
                    g.add((p_uri, RDFS.label, l))

            note = clean_ws(meta.get("note_raw", ""))
            if note:
                l = lit_lang(note)
                if l is not None:
                    g.add((p_uri, RDFS.comment, l))

            by = to_gyear(meta.get("birth_year", ""))
            if by is not None:
                g.add((p_uri, RFT.birthYear, by))

            age = to_int(meta.get("age", ""))
            if age is not None:
                g.add((p_uri, RFT.age, age))

        # Collector labels (from collectors_norm)
        if pid in collector_ids:
            labs = sorted(collector_labels_by_id.get(pid, set()))
            for lab in labs:
                # collectors_norm is usually a name (often ru/et; we’ll use heuristic)
                l = lit_lang(lab)
                if l is not None:
                    g.add((p_uri, RDFS.label, l))

        # Absolute fallback: ensure there is at least one label
        # (helps debugging & UI)
        if (p_uri, RDFS.label, None) not in g:
            g.add((p_uri, RDFS.label, Literal(pid)))

    return g

# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="Generate RDF (TTL) for Agents (Narrators + Collectors) from canonical table.")
    ap.add_argument("--csv", default=None, help="Input canonical_table CSV path.")
    ap.add_argument("--out", default=None, help="Output TTL path.")
    ap.add_argument("--limit", type=int, default=None, help="Read only first N rows (debug).")

    args = ap.parse_args()

    csv_path = Path(args.csv or os.environ.get(ENV_INPUT, "") or str(DEFAULT_INPUT_CSV)).expanduser().resolve()
    out_path = Path(args.out or os.environ.get(ENV_OUT, "") or str(DEFAULT_OUT_TTL)).expanduser().resolve()

    if not csv_path.exists():
        raise FileNotFoundError(
            f"Input CSV not found: {csv_path}\n"
            f"Expected default: {DEFAULT_INPUT_CSV}\n"
            f"Override via --csv or env {ENV_INPUT}."
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)

    sep = detect_delimiter(csv_path)
    df = read_csv_fallback(csv_path, sep=sep)

    if args.limit is not None:
        df = df.head(args.limit)

    g = build_agents_graph(df)
    out_path.write_text(g.serialize(format="turtle"), encoding="utf-8")
    print(f"Wrote: {out_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
