# streamlit_app.py

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1] 
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


import os
from datetime import datetime, timezone
import copy
from weakref import ref
import pandas as pd
import numpy as np

import html
import json
from typing import Any, Dict, List, Optional, Sequence, Tuple
import streamlit as st
from functools import lru_cache
import altair as alt
from rdflib import Graph 

from src.service import classify
from src.export_jsonld import to_jsonld
from src.model_store import build_export_result


MODELS_DIR = REPO_ROOT / "models"

MODEL_PATH = MODELS_DIR / "model.joblib"
LABELS_PATH = MODELS_DIR / "labels.json"
META_PATH = MODELS_DIR / "meta.json"
ATU_LABELS_PATH = REPO_ROOT / "data" / "processed" / "atu_labels.json"
ATU_REF_PATH = REPO_ROOT / "data" / "processed" / "atu_reference.csv"

DATA_DIR = REPO_ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
CORPUS_PATH = REPO_ROOT / "data" / "processed" / "corpus_a_for_kg.csv"
CORPUS_TTL = REPO_ROOT / "rdf" / "rdf_serialization" / "corpus.ttl"
AGENTS_TTL = REPO_ROOT / "rdf" / "rdf_serialization" / "agents.ttl"

# SPARQL CQ outputs 
CQ_RESULTS_DIR = REPO_ROOT / "rdf" / "queries"  / "query_results"

# RDF / KG export candidates
RDF_EXPORT_DIR = REPO_ROOT / "rdf" / "rdf_serialization"
RDF_JSONLD_DIR = RDF_EXPORT_DIR / "jsonld"

REPO_URL = "https://github.com/eugeniavd/magic_tagger"

TALE_ID_COL = "tale_id"
VOLUME_ID_COL = "volume_id"
COLLECTION_COL = "collection"
NARRATOR_COL = "narrator_label_en"
ATU_COL = "atu_codes" 
APP_TITLE = "MagicTagger — Tale Classifier"
APP_SUBTITLE = "Prototype UI: Top-3 ATU" 

@st.cache_data(show_spinner=False)
def load_training_meta() -> dict:
    with META_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)

def load_csv_if_exists(path: Path) -> pd.DataFrame:
    if not path or not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        # tolerate TSV
        try:
            return pd.read_csv(path, sep="\t")
        except Exception:
            return pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_corpus_min(corpus_path: str) -> pd.DataFrame:
    # expects: tale_id, collection
    df = pd.read_csv(corpus_path, dtype=str)
    # normalize
    if "collection" in df.columns:
        df["collection"] = df["collection"].fillna("").astype(str).str.strip()
    if "tale_id" in df.columns:
        df["tale_id"] = df["tale_id"].fillna("").astype(str).str.strip()
    return df

@st.cache_data(show_spinner=False)
def load_collection_map(map_path: str) -> pd.DataFrame:
    # file is ; separated: collection_id;label_et;see_also_urls
    df = pd.read_csv(map_path, sep=";", dtype=str)
    for c in ["collection_id", "label_et", "see_also_urls"]:
        if c in df.columns:
            df[c] = df[c].fillna("").astype(str).str.strip()
    return df

def attach_training_meta(result: dict, training_meta: dict) -> dict:
    result.setdefault("meta", {})
    
    for key in ["task", "text_cols", "model_name", "model_version", "note", "generated_at"]:
        if key not in result["meta"] and key in training_meta:
            result["meta"][key] = training_meta[key]
    return result

def add_inference_time(result: dict) -> dict:
    result.setdefault("meta", {})
    result["meta"]["inferred_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return result

@lru_cache(maxsize=1)
def load_atu_labels() -> dict:
    """
    Returns mapping { "707": "The ...", "552": "...", ... } or richer dict if you want.
    """
    if not ATU_LABELS_PATH.exists():
        return {}
    try:
        return json.loads(ATU_LABELS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

def get_atu_title(code: str) -> str:
    m = load_atu_labels() or {}
    if not code:
        return "Unknown ATU type"

    v = m.get(code)

    if isinstance(v, str) and v.strip():
        return v.strip()

    if isinstance(v, dict):
        for kk in ("en", "ru", "label", "title"):
            vv = v.get(kk)
            if vv and str(vv).strip():
                return str(vv).strip()

    return "Unknown ATU type"

@st.cache_data(show_spinner=False)
def load_corpus_df(path_str: str, mtime: float) -> pd.DataFrame:
    """
    Streamlit cache invalidation key includes file modification time (mtime),
    so metrics auto-refresh when file changes.
    """
    path = Path(path_str)
    if not path.exists():
        return pd.DataFrame()
    # choose loader by suffix
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)

def get_corpus_df(path: Path) -> pd.DataFrame:
    mtime = path.stat().st_mtime if path.exists() else 0.0
    return load_corpus_df(str(path), mtime)

@st.cache_data(show_spinner=False)
def load_atu_reference(path: Path) -> pd.DataFrame:
    """
    Expected columns: code;title_en;desc_en (semicolon-separated)
    """
    if not path.exists():
        return pd.DataFrame(columns=["code", "title_en", "desc_en"])
    df = pd.read_csv(path, sep=";", dtype=str, keep_default_na=False)
    # normalize
    if "code" in df.columns:
        df["code"] = df["code"].astype(str).str.strip()
    for c in ("title_en", "desc_en"):
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()
    return df

@st.cache_data(show_spinner=False)
def read_text_head(path_str: str, max_lines: int, file_sig: tuple[int, int]) -> str:
    """
    file_sig = (mtime_ns, size) — forces cache invalidation when file changes
    and also differentiates between different chosen files robustly.
    """
    p = Path(path_str)
    if not p.exists():
        return ""
    out: list[str] = []
    with p.open("r", encoding="utf-8", errors="replace") as f:
        for _ in range(max_lines):
            line = f.readline()
            if not line:
                break
            out.append(line)
    return "".join(out)


def atu_ref_lookup(df_ref: pd.DataFrame, code: str) -> dict:
    """
    Returns {"title_en": str|None, "desc_en": str|None} for code.
    Handles codes like '556A*' and possible '-star' variants.
    """
    if df_ref.empty or not code:
        return {"title_en": None, "desc_en": None}

    key = str(code).strip().replace("-star", "*")
    hit = df_ref[df_ref["code"] == key]
    if hit.empty:
        return {"title_en": None, "desc_en": None}

    row = hit.iloc[0]
    return {
        "title_en": (row.get("title_en") or "").strip() or None,
        "desc_en": (row.get("desc_en") or "").strip() or None,
    }

def make_collection_coverage_df(corpus_df: pd.DataFrame, coll_map_df: pd.DataFrame) -> pd.DataFrame:
    # counts unique tales per collection
    d = corpus_df.copy()
    d = d[d["collection"].astype(str).str.strip() != ""]
    counts = (
        d.groupby("collection", as_index=False)["tale_id"]
        .nunique()
        .rename(columns={"collection": "collection_id", "tale_id": "taleCount"})
    )

    # join labels
    if not coll_map_df.empty and "collection_id" in coll_map_df.columns:
        out = counts.merge(
            coll_map_df[["collection_id", "label_et", "see_also_urls"]].drop_duplicates("collection_id"),
            on="collection_id",
            how="left",
        )
    else:
        out = counts.copy()
        out["label_et"] = ""
        out["see_also_urls"] = ""

    # final label
    out["collectionLabel"] = out["label_et"].where(out["label_et"].astype(str).str.len() > 0, out["collection_id"])
    out["taleCount"] = pd.to_numeric(out["taleCount"], errors="coerce").fillna(0).astype(int)

    # sort: most represented first; ties by label
    out = out.sort_values(by=["taleCount", "collectionLabel"], ascending=[False, True], kind="mergesort")
    return out

# -----------------------------
# Utilities
# -----------------------------

def _collection_display_name(collection_id: str) -> str:
    s = (collection_id or "").strip()
    low = s.lower()

    if "era" in low and "vene" in low:
        return "ERA, Vene"
    if "rkm" in low and "vene" in low:
        return "RKM, Vene"
    if ("tru" in low and "vkk" in low) or ("trü" in low):
        return "TRU, VKK"

    return s

def render_collection_coverage_pie(df_corpus_min: pd.DataFrame, df_coll_map: pd.DataFrame) -> None:
    st.markdown("**Coverage by collection**")

    df_cov = make_collection_coverage_df(df_corpus_min, df_coll_map)
    if df_cov.empty:
        st.info("No collection coverage data available.")
        return

    d = df_cov.copy()
    d["collectionDisplay"] = d["collection_id"].apply(_collection_display_name)

    d["taleCount"] = pd.to_numeric(d["taleCount"], errors="coerce").fillna(0).astype(int)
    total = int(d["taleCount"].sum()) if len(d) else 0
    if total == 0:
        st.info("No texts counted for collections.")
        return

    d["share"] = d["taleCount"] / total
    d["sharePct"] = (d["share"] * 100).round(1)

    # Donut chart
    pie_order = alt.Order("taleCount:Q", sort="descending")
    
    pie = (
        alt.Chart(d)
        .mark_arc(innerRadius=55, outerRadius=110)
        .encode(
            theta=alt.Theta("taleCount:Q", stack=True),
            order=pie_order,
            color=alt.Color("collectionDisplay:N", title="Collection"),
            tooltip=[
                alt.Tooltip("collectionDisplay:N", title="Collection (ID)"),
                alt.Tooltip("taleCount:Q", title="Texts", format="d"),
                alt.Tooltip("sharePct:Q", title="Share (%)"),
                alt.Tooltip("see_also_urls:N", title="See also"),
            ],
        )
        .properties(height=260)
    )

    slice_numbers = (
        alt.Chart(d)  
        .mark_text(radius=85, fontSize=12, fontWeight="bold", color="white")
        .encode(
        theta=alt.Theta("taleCount:Q", stack=True),
        order=pie_order,
        text=alt.Text("taleCount:Q", format="d"),
        )
    )
    # Labels 
    labels = (
        alt.Chart(d[d["share"] >= 0.08])  # hide labels for very small slices
        .mark_text(radius=135, size=12)
        .encode(
            theta=alt.Theta("taleCount:Q", stack=True),
            text=alt.Text("collectionDisplay:N"),
        )
    )

    st.altair_chart(pie + slice_numbers + labels, use_container_width=True)

    
def _init_state() -> None:
    st.session_state.setdefault("nav_main", "Home")
    st.session_state.setdefault("nav_explore", "Overview")
    st.session_state.setdefault("last_result", None)          # type: Optional[Dict[str, Any]]
    st.session_state.setdefault("last_text", "")
    st.session_state.setdefault("last_tale_id", "external_001")
    st.session_state.setdefault("selected_atu", None)         # type: Optional[str]
    st.session_state.setdefault("help_open", False)
    st.session_state.setdefault("explore_tab", "Corpus Overview")  


def _first_existing_dir(candidates: List[Path]) -> Optional[Path]:
    for p in candidates:
        try:
            if p.exists() and p.is_dir():
                return p
        except Exception:
            pass
    return None


def _first_existing_file(candidates: List[Path]) -> Optional[Path]:
    for p in candidates:
        try:
            if p.exists() and p.is_file():
                return p
        except Exception:
            pass
    return None


def _set_home() -> None:
    st.session_state["nav_main"] = "Home"


def _safe_get(d: Dict[str, Any], path: Sequence[str], default=None):
    cur: Any = d
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur

def adapt_classify_result_for_jsonld(raw: dict, tale_id: str, k: int = 3) -> dict:
    run = raw.get("run", {}) or {}
    suggestions = raw.get("suggestions", []) or []
     # anchors_map = raw.get("anchors", {}) or {}

    candidates = []
    for s in suggestions[:k]:
        if not isinstance(s, dict):
            continue
        atu = str(s.get("atu_code", "")).strip()
        score = s.get("score", None)

         # anchors = []
         # snippets = []
         # if isinstance(anchors_map, dict) and atu and atu in anchors_map:
             # for a in anchors_map.get(atu, []) or []:
                 # if not isinstance(a, dict):
                    # continue
                # snippet list
                 #sn = a.get("snippet")
                 #if sn:
                     #snippets.append(sn)

                 #anchors.append({
                     #"anchor_id": a.get("anchor_id"),
                     #"score": a.get("score"),
                     #"rationale": a.get("rationale"),
                     #"span": a.get("span"),  # {start_char, end_char} если есть
                 #})

        candidates.append({
            "atu": atu,
            "score": float(score) if score is not None else None,
             # "evidence": {
                # "snippets": snippets,
                 # "anchors": anchors,
             # }
        })

    export_result = {
        "id": tale_id,
        "meta": {
            "k": k,
            "model_name": run.get("model_name", "MagicTagger ATU classifier"),
            "model_version": run.get("model_version", "unknown"),

            "inferred_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
        "candidates": candidates,
    }
    return export_result

def highlight_text_with_spans(text: str, spans: Sequence[Tuple[int, int]]) -> str:
    """
    Render fulltext with <mark> highlights using char offsets.
    - Expects spans as (start, end), 0 <= start < end <= len(text)
    - Handles overlaps by merging.
    Returns HTML string (safe to render with unsafe_allow_html=True).
    """
    if not text:
        return "<div style='white-space: pre-wrap;'></div>"

    n = len(text)
    cleaned: List[Tuple[int, int]] = []
    for s, e in spans:
        try:
            s_i, e_i = int(s), int(e)
        except Exception:
            continue
        if s_i < 0:
            s_i = 0
        if e_i > n:
            e_i = n
        if e_i <= s_i:
            continue
        cleaned.append((s_i, e_i))

    if not cleaned:
        esc = html.escape(text)
        return f"<div style='white-space: pre-wrap; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;'>{esc}</div>"

    cleaned.sort(key=lambda x: (x[0], x[1]))

    # merge overlaps
    merged: List[Tuple[int, int]] = []
    cur_s, cur_e = cleaned[0]
    for s, e in cleaned[1:]:
        if s <= cur_e:
            cur_e = max(cur_e, e)
        else:
            merged.append((cur_s, cur_e))
            cur_s, cur_e = s, e
    merged.append((cur_s, cur_e))

    # build HTML
    parts: List[str] = []
    last = 0
    for s, e in merged:
        parts.append(html.escape(text[last:s]))
        parts.append(f"<mark>{html.escape(text[s:e])}</mark>")
        last = e
    parts.append(html.escape(text[last:]))

    body = "".join(parts)
    return (
        "<div style='white-space: pre-wrap; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;'>"
        f"{body}"
        "</div>"
    )


def make_quick_exports(result: Optional[Dict[str, Any]]) -> Dict[str, bytes]:
    exports: Dict[str, bytes] = {}

    if not result:
        exports["JSON-LD"] = b"{}"
        exports["Turtle"] = b"# empty\n"
        exports["CSV"] = b""
        return exports

    # JSON-LD (placeholder context)
    jsonld_obj = {
        "@context": {
            "@vocab": "https://example.org/vocab/",
            "run": "run",
            "suggestions": "suggestions",
            # "anchors": "anchors",
        },
        **result,
    }
    exports["JSON-LD"] = json.dumps(jsonld_obj, ensure_ascii=False, indent=2).encode("utf-8")

    # Turtle stub
    run_id = _safe_get(result, ["run", "run_id"], "unknown_run")
    tale_id = _safe_get(result, ["run", "tale_id"], "unknown_tale")
    exports["Turtle"] = (
        f"# Turtle export stub (not implemented yet)\n"
        f"# run_id: {run_id}\n"
        f"# tale_id: {tale_id}\n"
    ).encode("utf-8")

    # CSV (suggestions) — SAFE: no backslashes inside f-string expressions
    suggestions = result.get("suggestions", []) if isinstance(result, dict) else []
    lines = ["rank,atu_code,label,score,confidence_band"]

    for s in suggestions:
        if not isinstance(s, dict):
            continue

        rank = s.get("rank", "")
        atu = s.get("atu_code", "")
        label = str(s.get("label", ""))
        label_csv = '"' + label.replace('"', '""') + '"'  
        score = s.get("score", "")
        band = s.get("confidence_band", "")

        lines.append(f"{rank},{atu},{label_csv},{score},{band}")

    exports["CSV"] = ("\n".join(lines) + "\n").encode("utf-8")

    return exports

def apply_expert_override(result: dict, expert_state: dict) -> dict:
    """Return a copy of result with meta updated for export (model vs expert)."""
    effective = copy.deepcopy(result)
    meta = (effective.get("meta", {}) or {}).copy()

    model_primary = meta.get("primary_atu")
    meta["model_primary_atu"] = model_primary

    expert_atu = str((expert_state or {}).get("atu") or "").strip()
    if expert_atu:
        meta["tale_status"] = "by expert"
        meta["final_decision_source"] = "expert"
        meta["final_atu"] = expert_atu
        meta["final_expert_note"] = str((expert_state or {}).get("note") or "").strip()
        meta["final_saved_at"] = str((expert_state or {}).get("saved_at") or "").strip()

       
        meta["primary_atu"] = expert_atu
    else:
        meta["final_decision_source"] = "model"
        meta["final_atu"] = str(model_primary or "")
        meta["final_expert_note"] = ""
        meta["final_saved_at"] = ""

    effective["meta"] = meta
    return effective

def find_cq_file(filename: str) -> Optional[Path]:
 
    if not CQ_RESULTS_DIR.exists():
        return None
    p = CQ_RESULTS_DIR / filename
    return p if p.exists() else None


def safe_metric(value: Any) -> str:
    if value is None:
        return "—"
    try:
        if isinstance(value, (int, np.integer)):
            return f"{int(value)}"
        if isinstance(value, (float, np.floating)):
            if float(value).is_integer():
                return f"{int(value)}"
            return f"{float(value):.2f}"
        s = str(value).strip()
        return s if s else "—"
    except Exception:
        return "—"

def read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except Exception:
        return b""

def _nunique_nonempty(series: pd.Series) -> int:
    s = series.dropna().astype(str).str.strip()
    s = s[s != ""]
    return int(s.nunique())

def _count_unique_atu(df: pd.DataFrame, col: str) -> Optional[int]:
    if col not in df.columns:
        return None
    s = df[col]

    # list-per-row case
    if s.apply(lambda x: isinstance(x, list)).any():
        codes = s.dropna().explode().astype(str).str.strip()
        codes = codes[codes != ""]
        return int(codes.nunique())

    # string case (single or multi)
    ss = s.dropna().astype(str).str.strip()
    if ss.empty:
        return 0

    # if delimiter present, split; else treat as single code
    if ss.str.contains(r"[;,]").any() or ss.str.contains(r"\[").any():
        codes = (
            ss.str.replace(r"[\[\]\"']", "", regex=True)
              .str.split(r"[;,]\s*")
              .explode()
              .astype(str)
              .str.strip()
        )
        codes = codes[codes != ""]
        return int(codes.nunique())

    return _nunique_nonempty(ss)

@st.cache_data(show_spinner=False)
def load_graph_for_tales(ttl_files: tuple[str, ...]):
    g = Graph()
    for fp in ttl_files:
        g.parse(fp, format="turtle")
    return g

import pandas as pd
import streamlit as st

import pandas as pd
import streamlit as st

@st.cache_data(show_spinner=False)
def tales_by_atu_from_ttl(
    ttl_files: tuple[str, ...],
    atu_code: str,
    limit: int = 300,
) -> pd.DataFrame:
    """
    RDFlib-safe: one row per tale (no GROUP BY / no aggregates / no regex).
    Requires ttl_files=(corpus.ttl, agents.ttl) for narrator labels.
    Returns:
      tale, atuConcept, atuCode,
      taleId, sourceRef, rightsStatus,
      narratorLabelEn, createdIn, place, taleDesc
    """

    g = Graph()
    for fp in ttl_files:
        g.parse(fp, format="turtle")

    code = (atu_code or "").strip().replace('"', '\\"')

    sparql = """
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX skos:    <http://www.w3.org/2004/02/skos/core#>
PREFIX rdfs:    <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT
  ?tale
  ?atuConcept
  ?atuCode
  ?taleId
  ?sourceRef
  ?rightsStatus
  ?narratorLabelEn
  ?createdIn
  ?place
  ?taleDesc
WHERE {
  ?tale dcterms:subject ?atuConcept .

  OPTIONAL { ?atuConcept skos:notation ?atuCodeSkos . }
  BIND(
    COALESCE(
      STR(?atuCodeSkos),
      REPLACE(STRAFTER(STR(?atuConcept), "/rdf/taleType/atu/"), "-star$", "*")
    ) AS ?atuCode
  )
  FILTER(?atuCode = "%s") .

  OPTIONAL { ?tale dcterms:identifier ?id . }
  BIND(
    COALESCE(
      STR(?id),
      REPLACE(STR(?tale), ".*/([^/]+)$", "$1")
    ) AS ?taleId
  )

  OPTIONAL { ?tale dcterms:bibliographicCitation ?bc . }
  BIND(COALESCE(STR(?bc), "") AS ?sourceRef)

  OPTIONAL { ?tale dcterms:accessRights ?ar . }
  BIND(COALESCE(STR(?ar), "") AS ?rightsStatus)

  OPTIONAL { ?tale dcterms:contributor ?narrator . }
  OPTIONAL { ?narrator rdfs:label ?labEn . FILTER(LANG(?labEn) = "en") }
  OPTIONAL { ?narrator rdfs:label ?labAny . }

  BIND(
    COALESCE(
      STR(?labEn),
      STR(?labAny),
      IF(BOUND(?narrator), REPLACE(STR(?narrator), ".*/([^/]+)$", "$1"), "")
    ) AS ?narratorLabelEn
  )

  OPTIONAL { ?tale dcterms:created ?created . }
  BIND(COALESCE(STR(?created), "") AS ?createdIn)

  OPTIONAL {
    ?tale dcterms:spatial ?pl .
    OPTIONAL { ?pl rdfs:label ?plLab . }
  }
  BIND(COALESCE(STR(?plLab), "") AS ?place)

  OPTIONAL { ?tale dcterms:description ?desc . }
  BIND(COALESCE(STR(?desc), "") AS ?taleDesc)
}
ORDER BY ?createdIn ?tale
LIMIT %d
""" % (code, int(limit))

    res = g.query(sparql)
    cols = [str(v) for v in res.vars]
    rows = [[("" if v is None else str(v)) for v in row] for row in res]
    df = pd.DataFrame(rows, columns=cols)

    expected = [
        "tale", "atuConcept", "atuCode",
        "taleId", "sourceRef", "rightsStatus",
        "narratorLabelEn", "createdIn", "place", "taleDesc",
    ]
    for c in expected:
        if c not in df.columns:
            df[c] = ""

    return df



def preview_text(text: str, max_chars: int) -> str:
        text = (text or "").strip()
        if not text:
            return ""
        if len(text) <= max_chars:
            return text

        cut = text[:max_chars].rstrip()
        last_space = cut.rfind(" ")
        if last_space > int(max_chars * 0.6):
            cut = cut[:last_space].rstrip()
        return cut + "…"

# -----------------------------
# Navigation
# -----------------------------
def render_left_nav() -> None:
    st.sidebar.markdown("### Jump to section")

    target = st.session_state.pop("nav_main_target", None)
    if target is not None:
        st.session_state["nav_main"] = target

    target_explore = st.session_state.pop("nav_explore_target", None)
    if target_explore is not None:
        st.session_state["nav_explore"] = target_explore

    main = st.sidebar.radio(
        "Main",
        ["Home", "Explore", "Classify"],
        key="nav_main",
        label_visibility="collapsed",
    )


# -----------------------------
# Homepage
# -----------------------------
def page_home() -> None:
    """
    One-screen Home:
    - clear value proposition for folklore researchers
    - two primary workflows (Explore / Classify)
    - short trust/provenance + methodology/export hints
    """

    # Optional: tighten vertical space a bit (safe defaults)
    st.markdown(
        """
        <style>
          .block-container { padding-top: 1.2rem; padding-bottom: 1.2rem; max-width: 1100px; }
          h1 { margin-bottom: 0.25rem; }
          .lead { font-size: 1.05rem; line-height: 1.55; color: rgba(49,51,63,0.85); }
          .meta { font-size: 0.9rem; color: rgba(49,51,63,0.70); }
          .card { padding: 1rem 1.1rem; border: 1px solid rgba(49,51,63,0.15); border-radius: 14px; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # -----------------------------
    # HERO (title + lead)
    # -----------------------------
    st.markdown(f"# {APP_TITLE}")
    st.markdown(
        f"""
        <div class="lead">
          Explore and annotate Russian magic tales from the Estonian Folklore Archives.
          Filter the corpus by provenance metadata and get ATU Top-3 suggestions for new texts.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)

    # -----------------------------
    # Two main CTAs
    # -----------------------------
    c1, c2 = st.columns(2, vertical_alignment="top")

    with c1:
        st.markdown("### Explore corpus")
        st.caption("Browse tales, provenance metadata, and corpus knowledge graph.")
        if st.button("Explore corpus", use_container_width=True, type="primary"):
            st.session_state["nav_main_target"] = "Explore"
            st.session_state["nav_explore_target"] = "Overview"
            st.rerun()
        st.markdown(
            """
            **What you can do**
            - Find tales by **place / decade / collector / ATU**
            - Open a record and inspect **text + provenance**
            - Export knowledge graph for analysis
            """
        )
        st.markdown("</div>", unsafe_allow_html=True)


    with c2:
 
        st.markdown("### Classify a tale")
        st.caption("Paste text → get Top-3 ATU suggestions.")
        if st.button("Classify a text", use_container_width=True):
            st.session_state["nav_main_target"] = "Classify"
            st.rerun()
        st.markdown(
            """
            **What you get**
            - **Top-3 ATU** candidates + confidence scores
            - Exportable output for reporting
            """
        )
        st.markdown("</div>", unsafe_allow_html=True)
  
    st.divider()
    # ---------- LICENSES AND CREDITS (compact) ----------
    st.markdown("### Licenses and Credits")

    st.caption(
    "Data: Estonian Folklore Archives (rights retained by the archive). "
    "Derivative RDF/exports: ODbL 1.0. Code: MIT."
    )

    with st.expander("Read full licenses, rights, and credits"):
        st.markdown(
        """
        **Source archival materials**  
        - The original data is provided by the [Estonian Folklore Archives](https://en.folklore.ee/faq.php) and remains under the archive’s rights and access conditions.

        **Derivative data (RDF / exports)**  
        - The derived metadata and RDF knowledge graph exports generated by this project are released under [**ODbL 1.0**](https://opendatacommons.org/licenses/odbl/1-0/).  
        - Some records may be flagged as `restricted_anon` via `dcterms:accessRights`; these flags reflect source constraints and must be respected in reuse.

        **Code**  
        - The source code is released under the [**MIT License**](https://opensource.org/license/mit).

        **Software**  
        - Built with Streamlit and Python (plus supporting libraries used in the repository).
        """
        )


    # -----------------------------
    # Minimal “status/limitations” line 
    # -----------------------------
    st.write("")
    st.caption(
        "**Research prototype**. Automated type assignments are non-authoritative and provided for exploratory analysis. Use them as starting points and confirm with the original archival record."
    )

# -----------------------------
# Explore
# -----------------------------

def page_explore() -> None:
    # -----------------------------
    # Page header 
    # -----------------------------
    st.markdown("# Explore the Corpus")
    st.write(
        "A structured overview of the corpus composition, metadata coverage, ATU type distribution "
        "and RDF serializations for reuse."
    )

    with st.expander("How the corpus was built"):
        st.markdown(
    """
    - **Source**: Estonian Folklore Archive, Russian-language collections (originally handwritten notebooks), comprising tales of magic collected across the Estonian–Russian border region during the 20th century.
    - **Digitization**: physical notebooks → scanned page images  
    - **Text**: HTR-assisted extraction + manual correction or transcriptions; normalization → corpus tables  
    - **Metadata harmonization**: volumes, collectors, narrators, places, dates (tale-level vs volume-level attribution)  
    - **Typing layer**: ATU concepts linked via `dcterms:subject`   
    - **Knowledge Graph**: JSON-LD / Turtle exports with provenance (PROV-O) and reuse-first vocabularies  
    
    Note: Texts selected for close reading and annotation currently prioritize the subset used to train and evaluate the ATU classifier, 
    with an emphasis on high-frequency types to maximize training signal and coverage.  
    """
)

    # -----------------------------
    # Load CQ outputs 
    # -----------------------------
    q2_path = find_cq_file("Q2.csv")
    q3_path = find_cq_file("Q3.csv")
    q4_path = find_cq_file("Q4.csv")
    q5_path = find_cq_file("Q5.csv")
    q1_all_path = find_cq_file("Q1.csv")  

    df_q2 = load_csv_if_exists(q2_path) if q2_path else pd.DataFrame()
    df_q3 = load_csv_if_exists(q3_path) if q3_path else pd.DataFrame()
    df_q4 = load_csv_if_exists(q4_path) if q4_path else pd.DataFrame()
    df_q5 = load_csv_if_exists(q5_path) if q5_path else pd.DataFrame()
    df_q1 = load_csv_if_exists(q1_all_path) if q1_all_path else pd.DataFrame()

    # -----------------------------
    # Tabs 
    # -----------------------------
    tab_names = ["Corpus Overview", "Metadata", "Types Explorer", "Knowledge Graph"]
    picked = st.session_state.get("explore_tab", "Overview")
    if picked not in tab_names:
       picked = "Overview"

    # reorder so the picked tab becomes the first (active) tab
    ordered = [picked] + [t for t in tab_names if t != picked]
    t1, t2, t3, t4 = st.tabs(ordered)
    tabs = {ordered[0]: t1, ordered[1]: t2, ordered[2]: t3, ordered[3]: t4}
    

    # =========================================================
    # Tab 1 — Overview 
    # =========================================================
    df = get_corpus_df(CORPUS_PATH)
    if df.empty:
       st.warning(f"Corpus file not found or empty: {CORPUS_PATH}")
       return
    
    with tabs["Corpus Overview"]:
        st.markdown("## Key stats")
        
        # Compute counts (robust fallbacks)
        tales_count = _nunique_nonempty(df[TALE_ID_COL]) if TALE_ID_COL in df.columns else int(len(df))
        volumes_count = _nunique_nonempty(df[VOLUME_ID_COL]) if VOLUME_ID_COL in df.columns else None
        collections_count = _nunique_nonempty(df[COLLECTION_COL]) if COLLECTION_COL in df.columns else None
        narrators_count = _nunique_nonempty(df[NARRATOR_COL]) if NARRATOR_COL in df.columns else None
        atu_types_count = _count_unique_atu(df, ATU_COL)

        # Render metric grid
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Tales", safe_metric(tales_count))
        m2.metric("Volumes", safe_metric(volumes_count))
        m3.metric("Collections", safe_metric(collections_count))
        m4.metric("ATU Types", safe_metric(atu_types_count))
        m5.metric("Narrators", safe_metric(narrators_count))
        m6.metric("Pages (work in progress)", "509 ")

        st.divider()
 

        st.markdown("## Corpus overview charts")

        df_corpus_min = load_corpus_min(str(CORPUS_PATH)) 
        df_coll_map = load_collection_map(str(REPO_ROOT / "data" / "processed" / "collection_kivike_map.csv"))

        render_collection_coverage_pie(df_corpus_min, df_coll_map)
    

        st.divider()

        c1, c2 = st.columns(2, vertical_alignment="top")

        with c1:
           st.markdown("**Top ATU types**")

           if df_q2.empty or not {"atuCode", "taleCount"}.issubset(df_q2.columns):
               st.info("Q2 output not found or missing required columns: `atuCode`, `taleCount`.")
           else:
               topn = st.slider(
            "How many types you would like to observe?",
            min_value=5,
            max_value=20,
            value=10,
            step=1,
            key="q2_topn",
            )

               d = df_q2.copy()
               d["taleCount"] = pd.to_numeric(d["taleCount"], errors="coerce").fillna(0).astype(int)
               d["atuCode"] = d["atuCode"].astype(str).str.strip()
               d = d.sort_values("taleCount", ascending=False).head(topn)
  
               chart = (
                  alt.Chart(d)
                  .mark_bar()
                  .encode(
                  x=alt.X(
                  "taleCount:Q",
                  title="Number of tales",
                   axis=alt.Axis(format="d", tickMinStep=1),
                ),
                  y=alt.Y("atuCode:N", sort="-x", title="ATU type"),
                  tooltip=[
                  alt.Tooltip("atuCode:N", title="ATU type"),
                  alt.Tooltip("taleCount:Q", title="Tales Count", format="d"),
               ],
               )
               .properties(height=360)
             )

               st.altair_chart(chart, use_container_width=True)

               st.caption("Want to explore ATU types in detail?")
               if st.button("Go to Types Explorer →", key="go_to_types_from_overview", use_container_width=True):
                 st.session_state["explore_tab"] = "Types Explorer"
                 st.rerun()

        with c2:
            st.markdown("**Top narrators**")

            if df_q3.empty:
              st.info("Q3 output not found.")
            else:
              label_col = "narratorLabel" if "narratorLabel" in df_q3.columns else None
              key_col = (
            "narratorKey"
            if "narratorKey" in df_q3.columns
            else ("narrator" if "narrator" in df_q3.columns else None)
            )

            if not key_col or "taleCount" not in df_q3.columns:
               st.info("Q3 output missing required columns: narrator key + `taleCount`.")
            else:
               topn_n = st.slider(
                "How many narrators do you want to observe?",
                min_value=5,
                max_value=20,
                value=10,
                step=1,
                key="q3_topn",
                )

               d = df_q3.copy()
               d["taleCount"] = pd.to_numeric(d["taleCount"], errors="coerce").fillna(0).astype(int)

               if label_col:
                   d["label"] = d[label_col].fillna(d[key_col].astype(str))
               else:
                   d["label"] = d[key_col].astype(str)

               d["label"] = d["label"].astype(str).str.strip()
               d = d.sort_values("taleCount", ascending=False).head(topn_n)

               chart = (
                alt.Chart(d)
                .mark_bar()
                .encode(
                    x=alt.X("taleCount:Q", title="Number of tales"),
                    y=alt.Y("label:N", sort="-x", title="Narrator"),
                    tooltip=[
                        alt.Tooltip("label:N", title="Narrator"),
                        alt.Tooltip("taleCount:Q", title="Tales Count"),
                    ],
                )
                .properties(height=360)
               )

               st.altair_chart(chart, use_container_width=True)         

        st.divider()       

        st.markdown("**Collectors timeline**")

        required_any_collector = ("collectorLabel" in df_q4.columns) or ("collector" in df_q4.columns)
        required = required_any_collector and ("year" in df_q4.columns) and ("taleCount" in df_q4.columns)

        if df_q4.empty or not required:
           st.info("Q4 output not found or missing required columns: collectorLabel/collector, year, taleCount.")
        else:
           d = df_q4.copy()

        # normalize columns
        d["collectorLabel"] = (
          d["collectorLabel"].fillna(d["collector"].astype(str))
          if "collectorLabel" in d.columns and "collector" in d.columns
          else (d["collectorLabel"].astype(str) if "collectorLabel" in d.columns else d["collector"].astype(str))
        )
        d["collectorLabel"] = d["collectorLabel"].astype(str).str.strip()

        d["year"] = pd.to_numeric(d["year"], errors="coerce")
        d["taleCount"] = pd.to_numeric(d["taleCount"], errors="coerce").fillna(0).astype(int)

        d = d.dropna(subset=["year"])
        d["year"] = d["year"].astype(int)

        topn = st.slider(
        "How many collectors to show?",
          min_value=10,
          max_value=60,
          value=20,
          step=5,
          key="q4_collectors_topn",
        )

        totals = (
            d.groupby("collectorLabel", as_index=False)["taleCount"]
             .sum()
             .rename(columns={"taleCount": "collectorTotal"})
             .sort_values("collectorTotal", ascending=False)
        )

        top_collectors = totals.head(topn)["collectorLabel"].tolist()
        dd = d[d["collectorLabel"].isin(top_collectors)].copy()

        if dd.empty:
            st.warning("No rows left after applying Top-N filter. Try increasing Top-N.")
            st.dataframe(d.head(100), use_container_width=True)
        else:
            # Attach totals for stable sorting in the chart
            dd = dd.merge(totals, on="collectorLabel", how="left")

            # Heatmap timeline: year × collector, color = #tales
            height = max(260, 18 * len(top_collectors))

            chart = (
                alt.Chart(dd)
                .mark_rect()
                .encode(
                    x=alt.X("year:O", title="Year"),
                    y=alt.Y(
                        "collectorLabel:N",
                        title="Collector",
                        sort=alt.SortField(field="collectorTotal", order="descending"),
                    ),
                    color=alt.Color("taleCount:Q", title="Tales number"),
                    tooltip=[
                        alt.Tooltip("collectorLabel:N", title="Collector"),
                        alt.Tooltip("year:O", title="Year"),
                        alt.Tooltip("taleCount:Q", title="Tales number"),
                    ],
                )
                .properties(height=height)
            )

            st.altair_chart(chart, use_container_width=True)

            with st.expander("Show in the table format"):
                st.dataframe(
                    dd.sort_values(["year", "collectorLabel", "collectorTotal"], ascending=[True, False, True]),
                    use_container_width=True,
                    hide_index=True,
                )

        st.divider()     

        st.markdown("**Geographical distribution of top ATU types**")

        # --- Top-N ATU codes from Q2
        df_corpus = get_corpus_df(CORPUS_PATH)
        if df_corpus.empty:
            st.warning(f"Corpus file not found or empty: {CORPUS_PATH}")
            return
        
        # IMPORTANT: use full corpus, not df_corpus_min (min has no region/atu_codes)
        corp = df_corpus.copy()

        if "region_english" not in corp.columns:
            st.info("Column `region_english` not found in corpus dataframe.")
            return
        corp["region_english"] = corp["region_english"].fillna("").astype(str).str.strip()


        if ATU_COL not in corp.columns:
            st.info(f"Column `{ATU_COL}` not found in corpus dataframe.")
            return

        corp["atuCode"] = (
        corp[ATU_COL]
        .fillna("")
        .astype(str)
        .str.replace(r"[\[\]']", "", regex=True)           # if codes stored like ['707']
        .str.replace(",", ";", regex=False)
        .str.split(r"\s*;\s*", regex=True)                 # split on ';' with spaces
      )

        corp = corp.explode("atuCode")
        corp["atuCode"] = corp["atuCode"].fillna("").astype(str).str.strip().str.replace("-star", "*", regex=False)

        
        corp = corp[(corp["atuCode"] != "") & (corp["region_english"] != "")]
        top_codes: list[str] = []

        if df_q2.empty or not {"atuCode", "taleCount"}.issubset(df_q2.columns):
            st.info("Q2 output not found or missing required columns: `atuCode`, `taleCount`.")
            return
        else:
            d_top = df_q2.copy()
            d_top["taleCount"] = pd.to_numeric(d_top["taleCount"], errors="coerce").fillna(0).astype(int)
            d_top["atuCode"] = d_top["atuCode"].astype(str).str.strip()
            d_top = d_top.sort_values("taleCount", ascending=False).head(topn)
            top_codes = d_top["atuCode"].tolist()

        if not top_codes:
            st.info("No ATU codes found in Q2 for the selected Top N.")
            return
        corp = corp[corp["atuCode"].isin(top_codes)]

        reg = (
        corp.groupby(["atuCode", "region_english"], as_index=False)[TALE_ID_COL]
        .nunique()
        .rename(columns={TALE_ID_COL: "taleCount"})
        )

        if reg.empty:
            st.warning("No rows after filtering. Check that corpus has `atu_codes` and `region_english` populated for these top types.")
            return

        reg["atuCode"] = pd.Categorical(reg["atuCode"], categories=top_codes, ordered=True)

        # stacked normalized bars (no explicit share column needed)
        stacked = (
        alt.Chart(reg)
       .mark_bar()
        .encode(
        y=alt.Y("atuCode:N", title="ATU type", sort=None),
        x=alt.X(
            "taleCount:Q",
            title="Share of tales by region",
            stack="normalize",
            axis=alt.Axis(format="%", tickMinStep=0.1),
        ),
        color=alt.Color(
           "region_english:N",
           title="Region",
           scale=alt.Scale(
            range=[
        "#4a8fc7",  
        "#0f3b5f",  
        "#0f86ee",  
        "#b3d9f5",  
        "#2a739f",  
        "#3c89b5",  
        "#5aa3c6",  
        "#7dbad6",  
        "#a8cfe6",  
        "#d6e7f3",  
         ]
        ),
       ),
        tooltip=[
            alt.Tooltip("atuCode:N", title="ATU type"),
            alt.Tooltip("region_english:N", title="Region"),
            alt.Tooltip("taleCount:Q", title="Tales", format="d"),
        ],
        )
        .properties(height=min(28 * len(top_codes) + 70, 560))
        )

        st.altair_chart(stacked, use_container_width=True)


    # =========================================================
    # Tab 2 — Metadata 
    # =========================================================
    with tabs["Metadata"]:
        st.markdown("## What’s inside")
        st.markdown(
        """
        **Core entities and links**
        - **Tale** (`crm:E33_Linguistic_Object`) with text/description and type links  
        - **Volume** as container with collection-level provenance  
        - **ATU Concept** (SKOS) linked via `dcterms:subject`  
        - **People**: narrators (`dcterms:contributor` at tale level) and collectors (`dcterms:creator` at volume level)  
        - **Place**: `dcterms:spatial`, `dcterms:created` (tale-level coverage)   
        - **Time**: `dcterms:created` (tale-level coverage)   
        """
    )
        st.divider()

        st.markdown("## Coverage sanity checks")

        if df_q5.empty or not {"metric", "count"}.issubset(df_q5.columns):
            st.info("Q5 output not found or missing required columns: `metric`, `count`.")
        else:
            d = df_q5.copy()
            d["count"] = pd.to_numeric(d["count"], errors="coerce").fillna(0).astype(int)
            d = d.sort_values("count", ascending=False)

            total_issues = int(d["count"].sum())
            n_metrics = int(len(d))

            c1, c2 = st.columns([1, 3], vertical_alignment="center")
            with c1:
                st.metric("Issues flagged", total_issues)
            with c2:
                if total_issues == 0:
                    st.success("No issues detected by Q5 sanity checks for this snapshot.")
                else:
                    top_metric = d.iloc[0]["metric"]
                    top_count = int(d.iloc[0]["count"])
                    st.warning(
                    f"Top issue: `{top_metric}` ({top_count}). Open the quality log to inspect affected records."
                )

            st.dataframe(d, use_container_width=True, hide_index=True)

            if n_metrics >= 2 and total_issues > 0:
                st.bar_chart(d.set_index("metric")["count"])

            st.caption(
            "Q5 checks cover missing containers (volume/dataset), missing `dcterms:subject` (ATU typing), "
            "missing people links (narrator/collector), missing place, and missing time (`dcterms:created`)."
            )

            with st.expander("Known issues / quality log"):
                qlog_path = REPO_ROOT / "rdf" / "quality" / "quality_log.json"

                if not qlog_path.exists():
                    st.info(f"Quality log not found: {qlog_path}")
                else:
                    try:
                        raw = json.loads(qlog_path.read_text(encoding="utf-8"))
                    except Exception as e:
                        st.error(f"Failed to read quality_log.json: {e}")
                        st.stop()

                    if isinstance(raw, list) and (len(raw) == 0 or isinstance(raw[0], dict)):
                        qdf = pd.DataFrame(raw)
                        st.caption(f"Loaded quality log: {len(qdf)} rows")
                        st.dataframe(qdf.head(200), use_container_width=True, hide_index=True)
                    else:
                        st.caption("Loaded quality log (JSON preview)")
                        st.json(raw)

                    st.download_button(
                    "Download quality_log.json",
                        data=qlog_path.read_bytes(),
                        file_name="quality_log.json",
                       mime="application/json",
                        use_container_width=True,
                    )


    # =========================================================
    # Tab 3 — Types Explorer 
    # =========================================================

    with tabs["Types Explorer"]:
        st.markdown("## Fairy Tale Types")


    # =========================================================
    # A) Overview chart 
    # =========================================================
        if df_q2.empty or not {"atuCode", "taleCount"}.issubset(df_q2.columns):
            st.info("Q2 output not available.")
        else:
            topn = st.slider(
            "How many types you would like to observe?",
            5, 86, 10, 1,
            key="types_topn"
            )

            d = df_q2.copy()
            d["taleCount"] = pd.to_numeric(d["taleCount"], errors="coerce").fillna(0).astype(int)

            d["atuCode"] = d["atuCode"].astype(str).str.strip()
            d["atuCode_norm"] = d["atuCode"].str.replace("-star", "*", regex=False)

            d["atu_num"] = pd.to_numeric(
                d["atuCode_norm"].str.extract(r"^(\d+)", expand=False),
                errors="coerce",
            ).fillna(10**9).astype(int)
            d["atu_suffix"] = d["atuCode_norm"].str.replace(r"^\d+", "", regex=True)

            d = d.sort_values(
                by=["taleCount", "atu_num", "atu_suffix", "atuCode_norm"],
                ascending=[False, True, True, True],
                kind="mergesort",
            ).head(topn)

            chart = (
                alt.Chart(d)
                .mark_bar()
                .encode(
                    x=alt.X(
                    "taleCount:Q",
                    title="Number of tales",
                    axis=alt.Axis(format="d", tickMinStep=1),
                    ),
                    y=alt.Y("atuCode_norm:N", sort="-x", title="ATU type"),
                    tooltip=[
                    alt.Tooltip("atuCode_norm:N", title="ATU type"),
                    alt.Tooltip("taleCount:Q", title="Tales Count", format="d"),
                    ],
                )
                .properties(height=min(28 * len(d) + 40, 700))
            )
            st.altair_chart(chart, use_container_width=True)

        st.divider()

    # =========================================================
    # B) Filter: select ATU code
    # =========================================================
        st.markdown("### Find a type by its code")

        selected_atu = ""
        if not df_q2.empty and "atuCode" in df_q2.columns:
            atu_codes = sorted(
                {str(x).strip() for x in df_q2["atuCode"].dropna().astype(str).tolist() if str(x).strip()}
            )
            selected_atu = st.selectbox(
            "ATU type code",
            options=[""] + atu_codes,
            index=0,
            placeholder="Select a type…",
            key="types_selected_atu",
            )
        else:
            selected_atu = st.text_input(
            "ATU type code",
            value="",
            placeholder="e.g., 707",
            key="types_selected_atu_text",
            ).strip()

    # If no selection -> hide card + tales (as you want)
        if not selected_atu:
            st.caption("Select an ATU type code to view its card and associated tales.")
        else:
            st.divider()

    # =========================================================
    # C) Type card
    # =========================================================
            st.markdown("### Explore a type")
            st.markdown(f"**ATU {selected_atu}**")

            atu_ref_df = load_atu_reference(ATU_REF_PATH)
            ref = atu_ref_lookup(atu_ref_df, str(selected_atu))

            title = ref.get("title_en") or get_atu_title(str(selected_atu))
            st.caption(title if title else "—")

            MAX_TYPE_DESC = 200
            desc_full = (ref.get("desc_en") or "").strip()

            if desc_full:
                st.write(preview_text(desc_full, MAX_TYPE_DESC))
                if len(desc_full) > MAX_TYPE_DESC:
                    with st.expander("Read full description"):
                        st.write(desc_full)
            else:
                st.caption("No long description available for this type in atu_reference.csv.")

            st.divider()

    # =========================================================
    # D) Tales for selected type (from corpus.ttl)
    # =========================================================

            st.markdown("### Tale witnesses for this type")
            st.caption("Browse corpus records typed with this ATU concept and inspect their contents.")

            if not CORPUS_TTL.exists():
               st.info(f"Corpus TTL not found: {CORPUS_TTL}")
               return
        
            d_tales = tales_by_atu_from_ttl(
            ttl_files=(str(CORPUS_TTL), str(AGENTS_TTL)),  
            atu_code=str(selected_atu),
            limit=30,
          )

            if d_tales.empty:
                st.warning("No tales found for this ATU code in corpus.ttl.")
                return

            # --- Normalize fields (keep robust to missing OPTIONALs)
            for c in ["tale", "taleId", "sourceRef", "rightsStatus", "narratorLabelEn", "createdIn", "place", "taleDesc"]:
                if c not in d_tales.columns:
                    d_tales[c] = ""

            for c in ["tale", "taleId", "sourceRef", "rightsStatus", "narratorLabelEn", "createdIn", "place", "taleDesc"]:
                d_tales[c] = d_tales[c].fillna("").astype(str).str.strip()

            # --- Card CSS 
            st.markdown(
            """
    <style>
      .tale-card {
        border: 1px solid rgba(49,51,63,0.16);
        border-radius: 14px;
        padding: 14px 16px;
        background: #fff;
        transition: background-color .15s ease, border-color .15s ease, box-shadow .15s ease;
        margin-bottom: 10px;
        min-height: 310px;               /* <-- key: equal height */
        display: flex;
        flex-direction: column;
      }
      .tale-card:hover {
        background-color: rgba(255, 149, 0, 0.08);
        border-color: rgba(255, 149, 0, 0.35);
        box-shadow: 0 4px 18px rgba(0,0,0,0.06);
      }
      .tale-title {
        font-weight: 700;
        font-size: 0.98rem;
        line-height: 1.2;
        margin: 0 0 6px 0;
      }
      .tale-meta {
        color: rgba(49,51,63,0.70);
        font-size: 0.86rem;
        margin: 0 0 10px 0;
      }
      .tale-row {
        display: flex;
        gap: 10px;
        margin: 3px 0;
        font-size: 0.90rem;
        line-height: 1.35;
      }
      .tale-k {
        min-width: 120px;
        color: rgba(49,51,63,0.78);
        font-weight: 600;
      }
      .tale-v {
        color: rgba(49,51,63,0.92);
        word-break: break-word;
      }

      /* description slot is fixed (same height everywhere) */
      .tale-desc {
        margin-top: 10px;
        color: rgba(49,51,63,0.92);
        font-size: 0.90rem;

        display: -webkit-box;
        -webkit-box-orient: vertical;
        -webkit-line-clamp: 4;          /* <-- same #lines for all cards */
        overflow: hidden;

        min-height: 5.2em;              /* <-- same slot height */
      }
      .tale-desc-muted {
        color: rgba(49,51,63,0.55);
        font-size: 0.88rem;
        margin-top: 10px;
        min-height: 5.2em;
      }
    </style>
    """,
            unsafe_allow_html=True,
            )


            MAX_TALE_DESC = 220

    # --- 3-column grid like your example
            cols = st.columns(3, vertical_alignment="top")

            for i, row in d_tales.reset_index(drop=True).iterrows():
                with cols[i % 3]:
                   tale_iri = row.get("tale", "")
                   tale_id = row.get("taleId", "") or (tale_iri.rsplit("/", 1)[-1] if "/" in tale_iri else tale_iri)
                   source_ref = row.get("sourceRef", "")
                   rights = row.get("rightsStatus", "")
                   narrator_en = row.get("narratorLabelEn", "")
                   created_in = row.get("createdIn", "")
                   place = row.get("place", "")
                   desc_full = row.get("taleDesc", "")

        # Render card (all requested fields)
                   st.markdown(
            f"""
            <div class="tale-card">
              <div class="tale-title">{tale_id}</div>
              <div class="tale-meta">ID: {tale_id}</div>

              <div class="tale-row"><div class="tale-k">Source ref</div><div class="tale-v">{source_ref or "—"}</div></div>
              <div class="tale-row"><div class="tale-k">Rights</div><div class="tale-v">{rights or "—"}</div></div>
              <div class="tale-row"><div class="tale-k">Narrator (EN)</div><div class="tale-v">{narrator_en or "—"}</div></div>
              <div class="tale-row"><div class="tale-k">Created in</div><div class="tale-v">{created_in or "—"}</div></div>
              <div class="tale-row"><div class="tale-k">Place</div><div class="tale-v">{place or "—"}</div></div>

              {f'<div class="tale-desc">{preview_text(desc_full, MAX_TALE_DESC)}</div>' if desc_full else '<div class="tale-desc-muted">No description available.</div>'}
            </div>
            """,
                    unsafe_allow_html=True,
                     )

       
                   if desc_full and len(desc_full) > MAX_TALE_DESC:
                        with st.expander("Open full description", expanded=False):
                            st.write(desc_full)

           
    # =========================================================
    # Tab Knowledge Graph
    # =========================================================
    
    with tabs["Knowledge Graph"]:

        st.markdown("## Ontology in brief")

        st.markdown(
        """
        - **Reuse-first vocabularies**: DCTERMS, SKOS, PROV-O, CIDOC-CRM, DCAT  
        - **Typing**: ATU types are linked with tales via `dcterms:subject` (`skos:Concept`)  
        - **Attribution model**: **narrators at tale level** (`dcterms:contributor`), **collectors at volume level** (`dcterms:creator`)  
        - **Time/Place**: tale/volume-level time metadata via `dcterms:created`; places via `dcterms:spatial` 
        - **Provenance**: exports are designed to keep processing context explicit and traceable (PROV-O) 
        """
      )

        st.markdown("**Method**")
        st.markdown(
        """
        - Introduced links follow a controlled mapping policy (documented rules, stable URI templates).  
        - Each derived assertion is intended to be explainable and traceable (PROV-friendly metadata).  
        - Validation and quality analysis is supported through coverage checks (e.g., Q5) and internal quality logs.  
        """
      )
     
        st.markdown(
    """
    <style>
      .btn-row{
        display:flex;
        align-items:center;
        gap: 5rem;          
        flex-wrap:wrap;
        margin-top:0.25rem;
      }

      .button, .button:link, .button:visited{
        display:inline-flex;
        align-items:center;
        justify-content:center;
        min-height: 38px;      
        line-height: 1;        
        padding: 0 1.2rem;     
        border-radius: 4px;
        background-color: #f97316;
        color: #ffffff !important;
        text-decoration: none !important;
        font-weight: 600;
        font-size: 0.9rem;
        border: none;
        cursor: pointer;
        transition: background-color 0.15s ease, transform 0.15s ease, box-shadow 0.15s ease;
      }
      .button:hover{
        background-color:#ea580c;
        transform:translateY(-1px);
        box-shadow:0 6px 18px rgba(0,0,0,0.10);
      }
      .button:active{
        background-color:#c2410c;
        transform:translateY(0);
        box-shadow:none;
      }

      .pill, .pill:link, .pill:visited{
        display:inline-flex;
        position: relative; top: 8px;
        align-items:center;
        justify-content:center;
        min-height: 38px;      
        line-height: 1;        
        gap:0.45rem;
        padding: 0 0.95rem;
        border-radius:999px;
        background: rgba(30, 64, 175, 0.08);
        border: 1px solid rgba(30, 64, 175, 0.18);
        color:#1e40af !important;
        text-decoration:none !important;
        font-weight:600;
        font-size:0.85rem;
        transition: background-color 0.15s ease, transform 0.15s ease, box-shadow 0.15s ease;
      }
      .pill:hover{
        background: rgba(30, 64, 175, 0.12);
        transform: translateY(-1px);
        box-shadow: 0 6px 18px rgba(0,0,0,0.08);
      }
      .pill:active{
        transform: translateY(0);
        box-shadow:none;
      }
    </style>

    <div class="btn-row">
      <a class="button"
         href="https://github.com/eugeniavd/magic_tagger/blob/main/rdf/ontology/ontology_overview.md"
         target="_blank"
         rel="noopener noreferrer">
         Read documentation
      </a>

      <a class="pill"
         href="#"
         onclick="return false;"
         aria-disabled="true"
         title="Citable bundle (coming soon)">
         <span class="pill-dot"></span>
         Citable bundle
      </a>
    </div>
    """,
    unsafe_allow_html=True,
)


        st.divider()

        st.markdown("## Serialization preview")

        rdf_dir = RDF_EXPORT_DIR
        if not rdf_dir.exists():
            st.info(f"RDF export directory not found. Expected: {rdf_dir}")
            st.stop()  # IMPORTANT: stop only when missing, do NOT return when present

        jsonld_dir = RDF_JSONLD_DIR
        if not jsonld_dir.exists():
            jsonld_dir = None


        TTL_FILES = [
            ("Agents", "agents.ttl"),
            ("ATU Types", "atu_types.ttl"),
            ("Biblio sources", "biblio_sources.ttl"),
            ("Corpus", "corpus.ttl"),
            ("Dataset (corpus v1)", "dataset_corpus_v1.ttl"),
        ]

        JSONLD_FILES = [
            ("Agents", "agents.jsonld"),
            ("ATU Types", "atu_types.jsonld"),
            ("Biblio sources", "biblio_sources.jsonld"),
            ("Corpus", "corpus.jsonld"),
            ("Dataset (corpus v1)", "dataset_corpus_v1.jsonld"),
      ]
        
        ttl_options: list[tuple[str, Path]] = []
        for label, fname in TTL_FILES:
            p = rdf_dir / fname
            if p.exists():
                ttl_options.append((f"{label} (TTL)", p))

        jsonld_options: list[tuple[str, Path]] = []
        if jsonld_dir:
            for label, fname in JSONLD_FILES:
                p = jsonld_dir / fname
                if p.exists():
                    jsonld_options.append((f"{label} (JSON-LD)", p))

        fmt = st.selectbox(
        "Format",
        ["Turtle", "JSON-LD"],
        index=0,
        key="kg_rdf_fmt",
        )

        if fmt == "Turtle":
            if not ttl_options:
                st.warning("No Turtle files found in rdf/rdf_serialization/.")
                st.stop()

            chosen = st.selectbox(
            "Dataset",
            options=ttl_options,
            format_func=lambda x: x[0],
            key="kg_rdf_dataset_ttl",
                )[1]
            language = "ttl"
            mime = "text/turtle"
        else:
            if not jsonld_options:
                st.warning("No JSON-LD files found in rdf/rdf_serialization/jsonld/.")
                st.stop()
            
            chosen = st.selectbox(
            "Dataset",
            options=jsonld_options,
            format_func=lambda x: x[0],
            key="kg_rdf_dataset_jsonld",
             )[1]
            language = "json"
            mime = "application/ld+json"

        chosen_key = f"{fmt}:{chosen.as_posix()}"
        if st.session_state.get("kg_last_chosen") != chosen_key:
            st.session_state["kg_last_chosen"] = chosen_key
            st.cache_data.clear()    

        max_lines = st.slider("Preview lines", 50, 500, 200, 50, key="kg_rdf_preview_lines")

        p = Path(chosen)  # chosen is Path
        sig = (p.stat().st_mtime_ns, p.stat().st_size)

        preview = read_text_head(str(p), max_lines=max_lines, file_sig=sig)


        preview_box = st.empty()
        preview_box.code(preview if preview else "# (empty preview)", language=language)



        st.markdown("### Downloads")
        c1, c2 = st.columns(2, vertical_alignment="top")

        def _download_or_disabled(label: str, path: Path | None, mime_type: str) -> None:
            if path and path.exists():
                st.download_button(
                f"Download {path.name}",
                data=read_bytes(path),
                file_name=path.name,
                mime=mime_type,
                use_container_width=True,
                key=f"kg_dl_{path.name}",  # unique key per file
                )
            else:
                st.button(f"Download {label}", disabled=True, use_container_width=True)

        with c1:
            st.markdown("**Turtle (.ttl)**")
            for label, fname in TTL_FILES:
                p = rdf_dir / fname
                _download_or_disabled(label, p if p.exists() else None, "text/turtle")

        with c2:
            st.markdown("**JSON-LD (.jsonld)**")
            if not jsonld_dir:
                st.info(f"JSON-LD directory not found: {RDF_JSONLD_DIR}")
            else:
                for label, fname in JSONLD_FILES:
                    p = jsonld_dir / fname
                    _download_or_disabled(label, p if p.exists() else None, "application/ld+json")

# -----------------------------
# Classify
# -----------------------------

def page_classify() -> None:
    st.markdown("# Classify your tale")

    # --- Disclaimer (EN)
    st.info(
        "Work in progress. This classifier was trained on a limited subset of tales available in the "
        "corpus snapshot."
    )

    # --- Intro text + source link for ATU
    st.write(
        "Paste or upload a text to check its type according to the "
        "[Aarne–Thompson–Uther Index](https://edition.fi/kalevalaseura/catalog/view/763/715/2750-1). "
        "Classification is currently available only for Russian-language texts. "
        "Predictions should be treated as suggestions rather than authoritative ATU assignments."
    )

    with st.form("classify_form", clear_on_submit=False):
        c1, c2 = st.columns([2, 1])

        with c1:
            tale_id = st.text_input(
                "External tale ID",
                value=st.session_state.get("last_tale_id", "external_001"),
            )

        with c2:
            # reserved (anchors toggle, etc.)
            pass

        uploaded = st.file_uploader("Upload .txt (optional)", type=["txt"])
        if uploaded is not None:
            try:
                text_ru = uploaded.getvalue().decode("utf-8", errors="replace")
            except Exception:
                text_ru = ""
        else:
            text_ru = st.text_area(
                "Paste tale text (Russian)",
                value=st.session_state.get("last_text", ""),
                height=220,
                placeholder="Paste the Russian tale here…",
            )

        submitted = st.form_submit_button("Suggest ATU (Top-3)")

    # -----------------------------
    # Run once on submit -> store canonical model export_result
    # -----------------------------
    if submitted:
        st.session_state["last_tale_id"] = tale_id
        st.session_state["last_text"] = text_ru

        with st.spinner("Classifying…"):
            raw = classify(tale_id=tale_id, text_ru=text_ru, top_k=3)

        export_result = build_export_result(raw, tale_id=tale_id, text_ru=text_ru, k=3)
        st.session_state["last_export_result"] = export_result

        # If user starts a new run, do not carry old expert decision silently
        # (optional but strongly recommended to avoid wrong exports)
        st.session_state["expert_decision"] = {}

    # -----------------------------
    # Source of truth: canonical model result
    # -----------------------------
    result = st.session_state.get("last_export_result")
    if not result:
        st.info("Run classification to see Top-3 suggestions.")
        return

    candidates = result.get("candidates", []) or []
    meta_model = result.get("meta", {}) or {}

    # -----------------------------
    # Human-in-the-loop: Final decision (expert)
    # -----------------------------
    expert_state = st.session_state.get("expert_decision", {}) or {}

    st.subheader("Final decision (expert)")

    atu_options = [c.get("atu") for c in candidates if c.get("atu")]
    atu_options = [x for x in atu_options if x]

    expert_mode_default = "Expert override" if expert_state.get("atu") else "Use model suggestion"
    mode = st.radio(
        "Decision mode",
        options=["Use model suggestion", "Expert override"],
        index=0 if expert_mode_default == "Use model suggestion" else 1,
        horizontal=True,
    )

    expert_atu = ""
    expert_note = ""

    if mode == "Expert override":
        picked = st.selectbox(
            "Final decision (expert): select ATU",
            options=(atu_options + ["Other / custom"]),
            index=0 if (expert_state.get("atu") in atu_options) else (len(atu_options)),
        )

        if picked == "Other / custom":
            expert_atu = st.text_input(
                "Enter ATU code manually (e.g., 707, 510A, 425C)",
                value=str(expert_state.get("atu", "") or ""),
                placeholder="ATU code…",
            ).strip()
        else:
            expert_atu = picked

        expert_note = st.text_area(
            "Expert note (optional)",
            value=str(expert_state.get("note", "") or ""),
            height=80,
            placeholder="Why you override the model (variant, motif cue, catalogue note, etc.)…",
        )

        b1, b2 = st.columns([1, 1])
        with b1:
            if st.button("Save expert decision", use_container_width=True):
                st.session_state["expert_decision"] = {
                    "atu": expert_atu,
                    "note": expert_note,
                    "saved_at": datetime.now(timezone.utc).isoformat(),
                }
                expert_state = st.session_state["expert_decision"]
        with b2:
            if st.button("Clear expert decision", use_container_width=True):
                st.session_state["expert_decision"] = {}
                expert_state = {}
    else:
        st.caption("Using the model output as the final decision for export.")

    # -----------------------------
    # Effective result for export (model vs expert)
    # IMPORTANT:
    # - candidates stay model candidates
    # - meta is rewritten for export + UI summary
    # -----------------------------
    use_expert = (mode == "Expert override") and bool((expert_state or {}).get("atu"))

    effective_result = copy.deepcopy(result)
    effective_meta = (effective_result.get("meta", {}) or {}).copy()

    # Always store model primary ATU explicitly (for provenance)
    model_primary = meta_model.get("primary_atu") or effective_meta.get("primary_atu")
    effective_meta["model_primary_atu"] = model_primary

    # Always reset HITL-related fields to avoid stale exports
    for k_ in ("hitl_activity_uri", "was_derived_from_result_uri", "expert_agent_id"):
        effective_meta.pop(k_, None)

    if use_expert:
        final_atu = str(expert_state.get("atu") or "").strip()

        effective_meta["final_decision_source"] = "expert"
        effective_meta["final_atu"] = final_atu
        effective_meta["final_expert_note"] = str(expert_state.get("note", "") or "").strip()
        effective_meta["final_saved_at"] = str(expert_state.get("saved_at", "") or "").strip()

        # Update effective decision (used in UI + export)
        effective_meta["primary_atu"] = final_atu
        effective_meta["tale_status"] = "review"

        # Optional provenance hooks
        effective_meta["hitl_activity_uri"] = f"{effective_meta.get('run_uri', '')}/hitl"
        effective_meta["was_derived_from_result_uri"] = effective_meta.get("result_uri", "")
        effective_meta["expert_agent_id"] = "expert_1"
    else:
        effective_meta["final_decision_source"] = "model"
        effective_meta["final_atu"] = str(model_primary or "").strip()
        effective_meta["final_expert_note"] = ""
        effective_meta["final_saved_at"] = ""


    effective_result["meta"] = effective_meta

    meta = effective_meta

    # External tale id for export + file name
    effective_tale_id = str(
        meta.get("tale_id") or effective_result.get("id")
        or st.session_state.get("last_tale_id") or "tale"
    ).strip()

    # Keep id consistent for downstream consumers
    effective_result["id"] = effective_tale_id

    st.caption(f"Model version: {meta.get('model_version', '—')}")


    effective_result["id"] = effective_tale_id 
    jsonld_obj = to_jsonld(effective_result, tale_id=effective_tale_id)

    payload = json.dumps(jsonld_obj, ensure_ascii=False, indent=2).encode("utf-8")

    st.download_button(
        "Download JSON-LD",
        data=payload,
        file_name=f"{effective_tale_id}.jsonld",
        mime="application/ld+json",
    )

    # -----------------------------
    # Decision summary (reflects EFFECTIVE meta)
    # -----------------------------
    st.subheader("Decision summary")
    s1, s2, s3, s4, s5 = st.columns(5)
    s1.metric("We Suggest", str(meta.get("tale_status", "—")))
    s2.metric("Final Type", str(meta.get("primary_atu", "—")))
    s3.metric("Model Decision", str(meta.get("model_primary_atu", "—")))
    s4.metric("Confidence", str(meta.get("confidence_band", "—")))
    s5.metric("Top-1 vs Top-2 gap", f"{float(meta.get('delta_top12', 0.0) or 0.0):.2f}")

    # -----------------------------
    # Run metadata
    # Show EFFECTIVE meta (includes HITL fields only if used)
    # -----------------------------
    with st.expander("Run metadata"):
        st.json(meta)

    # -----------------------------
    # Top-3 cards (MODEL candidates only)
    # -----------------------------
    st.subheader("Top-3 ATU candidates")
    if not candidates:
        st.warning("No candidates returned.")
        return

    cols = st.columns(3)
    for i, c in enumerate(candidates[:3]):
        with cols[i]:
            st.markdown(f"**#{c.get('rank', i+1)} — {c.get('atu','')}**")
            atu_code = c.get("atu", "")
            raw_label = str(c.get("label") or "").strip()
            file_label = get_atu_title(atu_code)
            title = file_label if (not raw_label) or raw_label.lower().startswith("unknown") else raw_label

            st.caption(title or "Unknown ATU type")
            st.metric("SCORE", f"{float(c.get('score', 0.0) or 0.0):.2f}")

            # Show the actual per-candidate confidence band from export_result
            st.caption(f"Confidence (policy): {c.get('confidence_band', '—')}")

    # Raw JSON (canonical)
    with st.expander("Model result without expert changes"):
        st.json(result)

    # -----------------------------
    # Minimal “status/limitations” line 
    # -----------------------------
    st.write("")
    st.caption(
        "**Research prototype**. Automated type assignments are non-authoritative and provided for exploratory analysis. Use them as starting points and confirm with the original archival record."
    )    



# rendering

def render_page() -> None:
    main = st.session_state.get("nav_main")
    if main == "Home":
        page_home()
    elif main == "Explore":
        page_explore()
    else:
        page_classify()

def render_footer() -> None:
    st.markdown(
        """
        <hr>
        <div style="text-align: center; line-height: 1.5;">
          <small>
            This website is a project developed by Evgeniia Vdovichenko as a final exam project within the
            <a href="https://corsi.unibo.it/2cycle/DigitalHumanitiesKnowledge" target="_blank" rel="noopener noreferrer">
              Digital Humanities and Digital Knowledge (DHDK) Master's Degree
            </a>
            at
            <a href="https://www.unibo.it/en" target="_blank" rel="noopener noreferrer">
              Alma Mater Studiorum – University of Bologna
            </a>.
            Contact:
            <a href="mailto:evgeniia.vdovichenko@studio.unibo.it">
              evgeniia.vdovichenko@studio.unibo.it
            </a>.
            <br>
            <a href="https://github.com/eugeniavd/magic_tagger" target="_blank" rel="noopener noreferrer">
              Source code
            </a>
          </small>
        </div>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------
# App entry
# -----------------------------
def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    _init_state()

    render_left_nav()
    render_page()
    render_footer() 


if __name__ == "__main__":
    main()
