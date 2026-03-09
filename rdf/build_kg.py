from __future__ import annotations
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import argparse
import ast
import csv
import json
import os
import re

from typing import Dict, List, Optional, Set

import pandas as pd
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, DCTERMS as DCT, XSD
from src.uris import BASE_DATA

# ---------------------------------------------------------------------
# Repo paths
# ---------------------------------------------------------------------
REPO_ROOT = Path("/Users/eugenia/Desktop/thesis/magic_tagger")

DEFAULT_INPUT_CSV = REPO_ROOT / "data" / "processed" / "corpus_a_for_kg.csv"
DEFAULT_OUT_TTL = REPO_ROOT / "rdf" / "rdf_serialization" / "corpus.ttl"

# Mapping: volume_id -> kivike_pid + kivike_url
DEFAULT_VOLUME_MAP_CSV = REPO_ROOT / "data" / "processed" / "volume_kivike_map.csv"
ENV_MAP = "VOLUME_KIVIKE_MAP_CSV"

# Mapping: collection_id -> label_et + seeAlso URLs
DEFAULT_COLLECTIONS_MAP_CSV = REPO_ROOT / "data" / "processed" / "collection_kivike_map.csv"
ENV_COLLECTIONS_MAP = "COLLECTIONS_MAP_CSV"

ENV_INPUT = "CORPUS_CANONICAL_CSV"
ENV_OUT = "CORPUS_VOLUMES_TTL"

# ---------------------------------------------------------------------
# Namespaces
# ---------------------------------------------------------------------
PROV = Namespace("http://www.w3.org/ns/prov#")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
DCMITYPE = Namespace("http://purl.org/dc/dcmitype/")
CRM = Namespace("http://www.cidoc-crm.org/cidoc-crm/")
RFT = Namespace(f"{BASE_DATA}ontology#")

# KEEP LoC MARC relators as role vocabulary
LOCREL = Namespace("http://id.loc.gov/vocabulary/relators/")
ROLE_NARRATOR = LOCREL.nrt  # narrator
ROLE_COLLECTOR = LOCREL.col  # collector

RIGHTS_MAP = {
    "open": RFT.rights_open,
    "restricted_anon": RFT.rights_partly_anonymised,
    "restricted-anon": RFT.rights_partly_anonymised,
}

# Dataset IRI (default; override via --dataset-iri)
DEFAULT_DATASET_IRI = URIRef(f"{BASE_DATA}dataset/corpus/v1")

_WS = re.compile(r"\s+")
_BAD = re.compile(r"[^a-z0-9\-]+")
_DATE_FULL_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_YM_RE = re.compile(r"^\d{4}-\d{2}$")
_DATE_Y_RE = re.compile(r"^\d{4}$")

# ---------------------------------------------------------------------
# IRI policy (minimal)
# ---------------------------------------------------------------------
def iri_volume(volume_id: str) -> URIRef:
    return URIRef(f"{BASE_DATA}volume/{volume_id}")

def iri_collection(collection_code: str) -> URIRef:
    return URIRef(f"{BASE_DATA}collection/{collection_code}")

def iri_person(person_id_or_slug: str) -> URIRef:
    return URIRef(f"{BASE_DATA}person/{person_id_or_slug}")

def iri_tale_recording(tale_id: str) -> URIRef:
    return URIRef(f"{BASE_DATA}TaleRecording/{tale_id}")

def iri_tale_content(tale_id: str) -> URIRef:
    return URIRef(f"{BASE_DATA}taleContent/{tale_id}")

def iri_atu(code: str) -> URIRef:
    """
    Mint ATU URI:
    - remove spaces
    - uppercase
    - '*' -> '-star'
    """
    c = clean_ws(code).replace(" ", "").upper()
    if not c:
        return URIRef(f"{BASE_DATA}taleType/atu/UNKNOWN")
    c = c.replace("*", "-star")
    return URIRef(f"{BASE_DATA}taleType/atu/{c}")

def iri_attribution_tale_recording(tale_id: str, role_code: str, person_id: str) -> URIRef:
    return URIRef(f"{BASE_DATA}attribution/taleRecording/{tale_id}/{role_code}/{person_id}")

def add_attribution(
    g: Graph,
    entity_uri: URIRef,
    agent_uri: URIRef,
    role_uri: URIRef,
    att_uri: URIRef,
) -> None:
    """
    PROV qualified attribution:
      entity prov:wasAttributedTo agent .
      entity prov:qualifiedAttribution att .
      att a prov:Attribution ;
          prov:agent agent ;
          prov:hadRole role .
    """
    g.add((agent_uri, RDF.type, PROV.Agent))
    g.add((agent_uri, RDF.type, FOAF.Person))
    g.add((role_uri, RDF.type, PROV.Role))

    g.add((entity_uri, PROV.wasAttributedTo, agent_uri))
    g.add((entity_uri, PROV.qualifiedAttribution, att_uri))
    g.add((att_uri, RDF.type, PROV.Attribution))
    g.add((att_uri, PROV.agent, agent_uri))
    g.add((att_uri, PROV.hadRole, role_uri))

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

def ensure_url_list(x: object) -> List[str]:
    s = clean_ws(x)
    if not s:
        return []
    parts = re.split(r"\s*\|\s*|,\s*|\s+", s)
    return [p.strip() for p in parts if p.strip()]

def normalize_rights_status(x: object) -> str:
    return clean_ws(x).lower()

def norm_date_literal(x: object) -> Optional[Literal]:
    s = clean_ws(x)
    if not s:
        return None
    s = s.split(" ")[0]
    if _DATE_FULL_RE.match(s):
        return Literal(s, datatype=XSD.date)
    if _DATE_YM_RE.match(s):
        return Literal(s, datatype=XSD.gYearMonth)
    if _DATE_Y_RE.match(s):
        return Literal(s, datatype=XSD.gYear)
    return None

# ---------------------------------------------------------------------
# Collections map loader
# ---------------------------------------------------------------------
def load_collections_map(path: Path) -> Dict[str, Dict[str, object]]:
    """
    Expected columns:
      - collection_id
      - label_et
      - see_also_urls  (one or many; separated by | or spaces)
    Returns dict: collection_id -> {"label_et": str, "see_also_urls": List[str]}
    """
    if not path.exists():
        return {}

    sep = detect_delimiter(path)
    cdf = read_csv_fallback(path, sep=sep)

    if "collection_id" not in cdf.columns:
        raise KeyError(f"Collections map must contain 'collection_id' column: {path}")

    out: Dict[str, Dict[str, object]] = {}
    for _, r in cdf.iterrows():
        cid = clean_ws(r.get("collection_id"))
        if not cid:
            continue
        out[cid] = {
            "label_et": clean_ws(r.get("label_et")),
            "see_also_urls": ensure_url_list(r.get("see_also_urls")),
        }
    return out

# ---------------------------------------------------------------------
# Collector extraction
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

    return [clean_ws(pid) for pid in person_ids if clean_ws(pid)]

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
        series = clean_ws(m.group(1))  # "ERA, Vene"
        volno = clean_ws(m.group(2))   # "5"
        return f"{series} {volno}"
    parts = [p.strip() for p in s.split(",") if p.strip()]
    if len(parts) >= 2:
        return f"{parts[0]}, {parts[1]}"
    return s

# ---------------------------------------------------------------------
# Volume->Kivike mapping loader
# ---------------------------------------------------------------------
def load_volume_kivike_map(path: Path) -> Dict[str, Dict[str, str]]:
    """
    Expected columns:
      - volume_id
      - kivike_pid   (e.g., ERA-17310-43411-19198)
      - kivike_url   (full URL)
    Returns dict: volume_id -> {"kivike_pid": ..., "kivike_url": ...}
    """
    if not path.exists():
        return {}

    sep = detect_delimiter(path)
    mdf = read_csv_fallback(path, sep=sep)

    if "volume_id" not in mdf.columns:
        raise KeyError(f"Mapping CSV must contain 'volume_id' column: {path}")

    pid_col = "kivike_pid" if "kivike_pid" in mdf.columns else None
    url_col = "kivike_url" if "kivike_url" in mdf.columns else None

    out: Dict[str, Dict[str, str]] = {}
    for _, r in mdf.iterrows():
        vid = clean_ws(r.get("volume_id"))
        if not vid:
            continue
        rec = {
            "kivike_pid": clean_ws(r.get(pid_col)) if pid_col else "",
            "kivike_url": clean_ws(r.get(url_col)) if url_col else "",
        }
        if vid not in out:
            out[vid] = rec
        else:
            if not out[vid].get("kivike_pid") and rec["kivike_pid"]:
                out[vid]["kivike_pid"] = rec["kivike_pid"]
            if not out[vid].get("kivike_url") and rec["kivike_url"]:
                out[vid]["kivike_url"] = rec["kivike_url"]
    return out

# ---------------------------------------------------------------------
# Place label builder (single label, temporary until authority file)
# ---------------------------------------------------------------------
def build_place_label(row: pd.Series) -> str:
    parts_en: List[str] = []
    for c in ("recording_place_english", "recording_parish_english", "region_english", "country_english"):
        if c in row.index:
            v = clean_ws(row.get(c))
            if v:
                parts_en.append(v)

    parts_orig: List[str] = []
    for c in ("recording_place", "recording_parish"):
        if c in row.index:
            v = clean_ws(row.get(c))
            if v:
                parts_orig.append(v)

    s_en = ", ".join(parts_en).strip()
    s_orig = ", ".join(parts_orig).strip()

    if s_en and s_orig:
        return f"{s_en} / {s_orig}"
    return s_en or s_orig

# ---------------------------------------------------------------------
# Narrator id resolver (left unchanged on purpose)
# ---------------------------------------------------------------------
def narrator_person_id(row: pd.Series) -> str:
    v = clean_ws(row.get("narrator_person_id")) if "narrator_person_id" in row.index else ""
    if not v or v.lower() in {"<na>", "na", "nan", "none"}:
        return ""
    return v

# ---------------------------------------------------------------------
# ATU codes resolver
# ---------------------------------------------------------------------
def atu_codes_from_row(row: pd.Series) -> List[str]:
    if "atu_codes" not in row.index:
        return []
    codes = ensure_list(row.get("atu_codes"))
    out: List[str] = []
    for c in codes:
        c = clean_ws(c)
        if not c:
            continue
        if c.lower() in {"<na>", "na", "nan", "none"}:
            continue
        out.append(c)
    return out

# ---------------------------------------------------------------------
# Graph builder (Volumes + Collections + TaleRecordings + TaleContents)
# ---------------------------------------------------------------------
def build_graph(
    df: pd.DataFrame,
    volume_map: Optional[Dict[str, Dict[str, str]]] = None,
    collections_map: Optional[Dict[str, Dict[str, object]]] = None,
    dataset_iri: Optional[URIRef] = DEFAULT_DATASET_IRI,
    add_dataset_links: bool = True,
) -> Graph:
    g = Graph()

    g.bind("dcterms", DCT)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)
    g.bind("prov", PROV)
    g.bind("foaf", FOAF)
    g.bind("rft", RFT)
    g.bind("dcmitype", DCMITYPE)
    g.bind("crm", CRM)
    g.bind("locrel", LOCREL)

    g.add((ROLE_NARRATOR, RDF.type, PROV.Role))
    g.add((ROLE_COLLECTOR, RDF.type, PROV.Role))

    required = ["tale_id", "volume_id", "collection"]
    for c in required:
        if c not in df.columns:
            raise KeyError(f"Missing required column: {c}")

    df = df.copy()
    df["tale_id"] = df["tale_id"].map(clean_ws)
    df["volume_id"] = df["volume_id"].map(clean_ws)
    df["collection"] = df["collection"].map(clean_ws)

    volume_map = volume_map or {}
    collections_map = collections_map or {}

    # ----------------------------------------------------------
    # Pre-aggregate attribution targets across all rows:
    # - collectors by volume
    # - collectors by tale
    # - narrators by tale
    # ----------------------------------------------------------
    collectors_by_volume: Dict[str, Set[str]] = {}
    collectors_by_tale: Dict[str, Set[str]] = {}
    narrators_by_tale: Dict[str, Set[str]] = {}

    for _, r in df.iterrows():
        vid0 = clean_ws(r.get("volume_id"))
        tid0 = clean_ws(r.get("tale_id"))

        row_collectors = collectors_from_row(r)

        if vid0:
            for pid in row_collectors:
                collectors_by_volume.setdefault(vid0, set()).add(pid)

        if tid0:
            for pid in row_collectors:
                collectors_by_tale.setdefault(tid0, set()).add(pid)

            npid = narrator_person_id(r)
            if npid:
                narrators_by_tale.setdefault(tid0, set()).add(npid)

    # -------------------------
    # 1) Volumes + Collections
    # -------------------------
    vdf = df[(df["volume_id"] != "") & (df["collection"] != "")]
    vdf = vdf.drop_duplicates(subset=["volume_id"], keep="first")

    for _, row in vdf.iterrows():
        vid = row["volume_id"]
        coll_raw = row["collection"]
        coll_uri = iri_collection(collection_code(coll_raw))
        vol_uri = iri_volume(vid)

        # Volume
        g.add((vol_uri, RDF.type, DCT.BibliographicResource))
        g.add((vol_uri, DCT.identifier, Literal(vid)))
        g.add((vol_uri, DCT.isPartOf, coll_uri))

        if "source_ref" in row.index:
            lbl = volume_label_from_source_ref(row.get("source_ref"))
            if lbl:
                g.add((vol_uri, RDFS.label, Literal(lbl)))

        # Collectors on Volume via dcterms:creator
        for pid in sorted(collectors_by_volume.get(vid, set())):
            agent_uri = iri_person(pid)
            g.add((agent_uri, RDF.type, PROV.Agent))
            g.add((agent_uri, RDF.type, FOAF.Person))
            g.add((vol_uri, DCT.creator, agent_uri))

        # Kivike mappings
        m = volume_map.get(vid, {})
        kiv_pid = clean_ws(m.get("kivike_pid"))
        kiv_url = clean_ws(m.get("kivike_url"))

        if kiv_pid:
            g.add((vol_uri, DCT.identifier, Literal(f"KIVIKE:{kiv_pid}")))

        if kiv_url:
            g.add((vol_uri, FOAF.page, URIRef(kiv_url)))

        # Collection
        g.add((coll_uri, RDF.type, DCMITYPE.Collection))
        g.add((coll_uri, DCT.identifier, Literal(coll_raw)))

        cmeta = collections_map.get(coll_raw, {})
        label_et = clean_ws(cmeta.get("label_et")) if cmeta else ""
        if label_et:
            g.add((coll_uri, RDFS.label, Literal(label_et, lang="et")))
        else:
            g.add((coll_uri, RDFS.label, Literal(coll_raw)))

        urls = cmeta.get("see_also_urls") if cmeta else []
        if urls:
            for u in urls:
                u = clean_ws(u)
                if u:
                    g.add((coll_uri, RDFS.seeAlso, URIRef(u)))

    # -------------------------
    # 2) Tale recordings + Tale contents
    # -------------------------
    tdf = df[df["tale_id"] != ""].drop_duplicates(subset=["tale_id"], keep="first")

    for _, row in tdf.iterrows():
        tid = row["tale_id"]
        vid = clean_ws(row.get("volume_id"))
        vol_uri = iri_volume(vid) if vid else None

        recording_uri = iri_tale_recording(tid)
        content_uri = iri_tale_content(tid)

        # Recording
        g.add((recording_uri, RDF.type, CRM.E33_Linguistic_Object))
        g.add((recording_uri, RDF.type, RFT.TaleRecording))
        g.add((recording_uri, DCT.identifier, Literal(tid)))

        # Content
        g.add((content_uri, RDF.type, CRM.E28_Conceptual_Object))
        g.add((content_uri, RDF.type, RFT.TaleContent))

        # Recording -> content
        g.add((recording_uri, PROV.wasDerivedFrom, content_uri))

        # isPartOf volume
        if vol_uri is not None and vid:
            g.add((recording_uri, DCT.isPartOf, vol_uri))

        # isPartOf dataset
        if add_dataset_links and dataset_iri is not None:
            g.add((recording_uri, DCT.isPartOf, dataset_iri))

        # bibliographic citation
        if "source_ref" in row.index:
            src = clean_ws(row.get("source_ref"))
            if src:
                g.add((recording_uri, DCT.bibliographicCitation, Literal(src)))

        # description/title
        if "content_description_clean" in row.index:
            desc = clean_ws(row.get("content_description_clean"))
            if desc:
                g.add((recording_uri, DCT.description, Literal(desc)))

        # rights (map table values -> ontology individuals)
        if "rights_status" in row.index:
            rs = normalize_rights_status(row.get("rights_status"))
            if rs:
                rights_uri = RIGHTS_MAP.get(rs)
                if rights_uri is None:
                    raise ValueError(f"Unknown rights_status value: {rs}")
                g.add((recording_uri, DCT.accessRights, rights_uri))

        # created date
        if "recorded_date_start" in row.index:
            d = norm_date_literal(row.get("recorded_date_start"))
            if d is not None:
                g.add((recording_uri, DCT.created, d))

        # subjects on TaleContent
        for code in atu_codes_from_row(row):
            g.add((content_uri, DCT.subject, iri_atu(code)))

        # place as temporary blank node label
        place_label = build_place_label(row)
        if place_label:
            place_bn = BNode()
            g.add((place_bn, RDF.type, CRM.E53_Place))
            g.add((place_bn, RDFS.label, Literal(place_label)))
            g.add((recording_uri, DCT.spatial, place_bn))

        # Narrator attribution on TaleRecording
        for n_pid in sorted(narrators_by_tale.get(tid, set())):
            agent_uri = iri_person(n_pid)
            att_uri = iri_attribution_tale_recording(tid, "nrt", n_pid)
            add_attribution(g, recording_uri, agent_uri, ROLE_NARRATOR, att_uri)

        # Collector attribution on TaleRecording
        for c_pid in sorted(collectors_by_tale.get(tid, set())):
            agent_uri = iri_person(c_pid)
            att_uri = iri_attribution_tale_recording(tid, "col", c_pid)
            add_attribution(g, recording_uri, agent_uri, ROLE_COLLECTOR, att_uri)

    return g

# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(
        description="Generate RDF (TTL) for Collections, Volumes, TaleRecordings, and TaleContents from canonical table."
    )
    ap.add_argument("--csv", default=None, help="Input canonical_table CSV path.")
    ap.add_argument("--out", default=None, help="Output TTL path.")
    ap.add_argument("--map", default=None, help="Volume->Kivike mapping CSV path (volume_id,kivike_pid,kivike_url).")
    ap.add_argument(
        "--collections-map",
        dest="collections_map",
        default=None,
        help="Collections mapping CSV (collection_id,label_et,see_also_urls).",
    )
    ap.add_argument("--volume-ids", default=None, help="Comma-separated volume_id list to export (optional).")
    ap.add_argument("--collection", default=None, help="Filter by collection value (e.g., 'era_vene').")
    ap.add_argument("--limit-volumes", type=int, default=None, help="Export only first N unique volumes (after filters).")
    ap.add_argument("--limit-tales", type=int, default=None, help="Export only first N tales (after filters).")

    # dataset link controls
    ap.add_argument(
        "--dataset-iri",
        default=str(DEFAULT_DATASET_IRI),
        help=f"Dataset IRI to link tale recordings to via dcterms:isPartOf (default: {DEFAULT_DATASET_IRI}).",
    )
    ap.add_argument(
        "--no-dataset-links",
        action="store_true",
        help="Disable adding dcterms:isPartOf datasetIRI links for tale recordings.",
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

    map_path = Path(
        args.map
        or os.environ.get(ENV_MAP, "")
        or str(DEFAULT_VOLUME_MAP_CSV)
    ).expanduser().resolve()

    collections_map_path = Path(
        args.collections_map
        or os.environ.get(ENV_COLLECTIONS_MAP, "")
        or str(DEFAULT_COLLECTIONS_MAP_CSV)
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

    # optional limits (applied after filters)
    if args.limit_volumes is not None:
        keep_vids = (
            df[df["volume_id"].map(clean_ws).ne("")]
            .drop_duplicates(subset=["volume_id"], keep="first")
            .head(args.limit_volumes)["volume_id"]
            .tolist()
        )
        df = df[df["volume_id"].isin(keep_vids)]

    if args.limit_tales is not None:
        keep_tids = (
            df[df["tale_id"].map(clean_ws).ne("")]
            .drop_duplicates(subset=["tale_id"], keep="first")
            .head(args.limit_tales)["tale_id"]
            .tolist()
        )
        df = df[df["tale_id"].isin(keep_tids)]

    volume_map = load_volume_kivike_map(map_path) if map_path.exists() else {}
    collections_map = load_collections_map(collections_map_path) if collections_map_path.exists() else {}

    dataset_iri = URIRef(args.dataset_iri) if args.dataset_iri else None
    add_dataset_links = not args.no_dataset_links

    g = build_graph(
        df,
        volume_map=volume_map,
        collections_map=collections_map,
        dataset_iri=dataset_iri,
        add_dataset_links=add_dataset_links,
    )

    out_path.write_text(g.serialize(format="turtle"), encoding="utf-8")
    print(f"Wrote: {out_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())