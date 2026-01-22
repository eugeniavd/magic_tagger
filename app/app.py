# streamlit_app.py
from __future__ import annotations
import os
import sys
from datetime import datetime, timezone
import copy
import pandas as pd
import numpy as np

import html
import json
from typing import Any, Dict, List, Optional, Sequence, Tuple
from pathlib import Path
import streamlit as st
from functools import lru_cache
import altair as alt


from src.service import classify
from src.utils import atu_parent
from src.export_jsonld import to_jsonld
from src.model_store import build_export_result



ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from src.service import classify

REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = REPO_ROOT / "models"

MODEL_PATH = MODELS_DIR / "model.joblib"
LABELS_PATH = MODELS_DIR / "labels.json"
META_PATH = MODELS_DIR / "meta.json"
ATU_LABELS_PATH = REPO_ROOT / "data" / "processed" / "atu_labels.json"

DATA_DIR = REPO_ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
CORPUS_PATH = REPO_ROOT / "data" / "processed" / "corpus_a_for_kg.csv"

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

APP_TITLE = "MagicTagger — Tale Classifier"
APP_SUBTITLE = "Prototype UI: Top-3 ATU + Anchors"

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

# -----------------------------
# Utilities
# -----------------------------


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
    anchors_map = raw.get("anchors", {}) or {}

    candidates = []
    for s in suggestions[:k]:
        if not isinstance(s, dict):
            continue
        atu = str(s.get("atu_code", "")).strip()
        score = s.get("score", None)

        anchors = []
        snippets = []
        if isinstance(anchors_map, dict) and atu and atu in anchors_map:
            for a in anchors_map.get(atu, []) or []:
                if not isinstance(a, dict):
                    continue
                # snippet list
                sn = a.get("snippet")
                if sn:
                    snippets.append(sn)

                anchors.append({
                    "anchor_id": a.get("anchor_id"),
                    "score": a.get("score"),
                    "rationale": a.get("rationale"),
                    "span": a.get("span"),  # {start_char, end_char} если есть
                })

        candidates.append({
            "atu": atu,
            "score": float(score) if score is not None else None,
            "evidence": {
                "snippets": snippets,
                "anchors": anchors,
            }
        })

    export_result = {
        "id": tale_id,
        "meta": {
            "k": k,
            "model_name": run.get("model_name", "MagicTagger ATU classifier"),
            "model_version": run.get("model_version", "unknown"),
            # время инференса (лучше для prov:generatedAtTime)
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
            "anchors": "anchors",
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
        meta["tale_status"] = "expert_override"
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


def read_text_head(path: Path, max_lines: int = 200) -> str:
    if not path or not path.exists():
        return ""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            lines = []
            for i, line in enumerate(f):
                if i >= max_lines:
                    break
                lines.append(line.rstrip("\n"))
        return "\n".join(lines)
    except Exception:
        return ""


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
# -----------------------------
# Navigation
# -----------------------------
def render_left_nav() -> None:
    st.sidebar.markdown("### Navigation")

    main = st.sidebar.radio(
        "Main",
        ["Home", "Explore", "Classify"],
        key="nav_main",
        label_visibility="collapsed",
    )

    st.sidebar.markdown("---")
    st.sidebar.caption("Prototype, work in progress")


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
          Filter the corpus by provenance metadata and get ATU Top-3 suggestions with evidence anchors for new texts.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Trust / provenance line (compact, researcher-relevant)
    st.markdown(
        """
        <div class="meta">
          Data source: Estonian Folklore Archives (ERA), Russian-language collections (e.g., ERA, Vene; RKM, Vene).
          Exports support FAIR/LOD workflows (CSV / JSON-LD / Turtle).
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")  # small breathing space

    # -----------------------------
    # Two main CTAs
    # -----------------------------
    c1, c2 = st.columns(2, vertical_alignment="top")

    with c1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### Explore corpus")
        st.caption("Browse tales, provenance metadata, and corpus structure.")
        if st.button("Explore corpus", use_container_width=True, type="primary"):
            st.session_state["nav_main"] = "Explore"
            st.session_state["nav_explore"] = "Overview"  # or your default explore subpage
        st.markdown(
            """
            **What you can do**
            - Find tales by **place / decade / collector / ATU**
            - Open a record and inspect **text + provenance + annotations**
            - Export filtered results for analysis
            """
        )
        st.markdown("</div>", unsafe_allow_html=True)


    with c2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### Classify a tale")
        st.caption("Paste text → get Top-3 ATU suggestions with evidence anchors.")
        if st.button("Classify a text", use_container_width=True):
            st.session_state["nav_main"] = "Classify"
        st.markdown(
            """
            **What you get**
            - **Top-3 ATU** candidates (+ confidence scores, if available)
            - **Anchors** (evidence spans) to support interpretability
            - Exportable output for reporting / LOD
            """
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # -----------------------------
    # Minimal “status/limitations” line 
    # -----------------------------
    st.write("")
    st.caption(
        "Note: In this build, some pages or model outputs may be unavailable depending on the demo mode. "
        "The interface and export contract remain stable."
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
    - **Source**: Estonian Folklore Archive, Russian-language collections (originally handwritten notebooks)  
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
 

        st.markdown("## Corpus overview charts")

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
                x=alt.X("taleCount:Q", title="Number of tales"),
                y=alt.Y("atuCode:N", sort="-x", title="ATU type"),
                tooltip=[
                    alt.Tooltip("atuCode:N", title="ATU type"),
                    alt.Tooltip("taleCount:Q", title="# tales"),
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
                        alt.Tooltip("taleCount:Q", title="# tales"),
                    ],
                )
                .properties(height=360)
               )

               st.altair_chart(chart, use_container_width=True)         

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

            # Optional: compact table under the chart
            with st.expander("Show in the table format"):
                st.dataframe(
                    dd.sort_values(["year", "collectorLabel", "collectorTotal"], ascending=[True, False, True]),
                    use_container_width=True,
                    hide_index=True,
                )
       

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
        st.subheader("Fairy tale Types")

        if df_q2.empty or not {"atuCode", "taleCount"}.issubset(df_q2.columns):
            st.info("Q2 output not available.")
        else:
            topn = st.slider("How many types you would like to observe?", 5, 86, 10, 1, key="types_topn")

            d = df_q2.copy()
            d["taleCount"] = pd.to_numeric(d["taleCount"], errors="coerce").fillna(0).astype(int)

            d["atuCode"] = d["atuCode"].astype(str).str.strip()
            d["atuCode_norm"] = d["atuCode"].str.replace("-star", "*", regex=False)

        # tie-break ordering: numeric part + suffix
            d["atu_num"] = pd.to_numeric(
                d["atuCode_norm"].str.extract(r"^(\d+)", expand=False),
                errors="coerce",
            ).fillna(10**9).astype(int)
            d["atu_suffix"] = d["atuCode_norm"].str.replace(r"^\d+", "", regex=True)

        # sort: popular first; ties by ATU numbering asc
            d = d.sort_values(
                by=["taleCount", "atu_num", "atu_suffix", "atuCode_norm"],
                ascending=[False, True, True, True],
                kind="mergesort",
            ).head(topn)

        # Altair: force top-down by sorting Y by descending X (count)
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



        st.subheader("C0. Filters")
        # Minimal filters (extend if you have more facets)
        selected_atu = None
        if not df_q2.empty and "atuCode" in df_q2.columns:
            atu_codes = sorted([str(x) for x in df_q2["atuCode"].dropna().astype(str).unique()])
            selected_atu = st.selectbox("ATU type code", options=[""] + atu_codes, index=0)
        else:
            selected_atu = st.text_input("ATU type code", value="", placeholder="e.g., 707")

        
        st.subheader("C2. Type card")
        if selected_atu:
            st.markdown(f"**ATU {selected_atu}**")
            st.caption(get_atu_title(str(selected_atu)))
            # If you have SKOS relations, render them here (broader/narrower/related)
        else:
            st.caption("Select an ATU type code to view its card and associated tales.")

        st.subheader("C3. Tales for selected type (CQ Q1)")
        if not selected_atu:
            st.info("Choose an ATU type to list associated tales (Q1).")
        else:
            
            if df_q1.empty or not {"atuCode", "tale", "volume"}.issubset(df_q1.columns):
                st.info(
                    "Q1 output not found. Recommended: materialize a file `Q1_tales_by_atu_type.csv` with columns:\n"
                    "`tale, taleDesc, volume, atuConcept, atuCode` for all types."
                )
            else:
                d = df_q1.copy()
                d["atuCode"] = d["atuCode"].astype(str)
                d = d[d["atuCode"] == str(selected_atu)]
                if d.empty:
                    st.warning("No tales found for this ATU code in the Q1 output.")
                else:
                    
                    cols = [c for c in ["tale", "taleDesc", "volume", "atuConcept", "atuCode"] if c in d.columns]
                    st.dataframe(d[cols], use_container_width=True, hide_index=True)


    # =========================================================
    # Tab D — Type Ontology 
    # =========================================================
    
    with tabs["Knowledge Graph"]:
        st.subheader("D1. Ontology in brief")

        st.markdown(
        """
        - **Reuse-first vocabularies**: DCTERMS, SKOS, PROV-O, CIDOC-CRM (light), DCAT  
        - **Typing**: ATU concepts are linked via `dcterms:subject` (SKOS Concept URIs; `skos:notation` as fallback)  
        - **Attribution model**: **narrators at tale level** (`dcterms:contributor`), **collectors at volume level** (`dcterms:creator`)  
        - **Time/Place**: tale/volume-level time metadata via `dcterms:created`; places via `dcterms:spatial` / recording place properties  
        - **Provenance**: exports are designed to keep processing context explicit (what was derived vs asserted)  
        """
      )

        st.markdown("**Method (how we account for introduced entities/links)**")
        st.markdown(
        """
        - Introduced links follow a **controlled mapping policy** (documented rules, stable URI templates).  
        - Each derived assertion is intended to be explainable and traceable (PROV-friendly metadata).  
        - Validation/QA is supported through coverage checks (e.g., Q5) and internal quality logs.  
        """
      )

        st.subheader("D2. Serialization preview (RDF preview)")

        rdf_dir = RDF_EXPORT_DIR if RDF_EXPORT_DIR.exists() else None
        if not rdf_dir:
           st.info(
            "RDF export directory not found. Expected: "
            f"{RDF_EXPORT_DIR}"
          )
           st.stop()

        jsonld_dir = RDF_JSONLD_DIR if RDF_JSONLD_DIR.exists() else None

        ttl_agents = rdf_dir / "agents.ttl"
        ttl_atu = rdf_dir / "atu_types.ttl"

        jsonld_agents = (jsonld_dir / "agents.jsonld") if jsonld_dir else None
        jsonld_atu = (jsonld_dir / "atu_types.jsonld") if jsonld_dir else None

        ttl_options = []
        if ttl_agents.exists():
            ttl_options.append(("Agents (TTL)", ttl_agents))
        if ttl_atu.exists():
            ttl_options.append(("ATU Types (TTL)", ttl_atu))

        jsonld_options = []
        if jsonld_agents and jsonld_agents.exists():
            jsonld_options.append(("Agents (JSON-LD)", jsonld_agents))
        if jsonld_atu and jsonld_atu.exists():
            jsonld_options.append(("ATU Types (JSON-LD)", jsonld_atu))

        fmt = st.selectbox("Format", ["Turtle", "JSON-LD"], index=0, key="rdf_fmt")

        if fmt == "Turtle":
            if not ttl_options:
                st.warning("No Turtle files found in rdf/rdf_serialization/.")
                st.stop()

            label, chosen = st.selectbox(
                "Dataset",
                options=ttl_options,
                format_func=lambda x: x[0],
                key="rdf_dataset_ttl",
            )
            language = "ttl"

        else:  # JSON-LD
            if not jsonld_options:
                st.warning("No JSON-LD files found in rdf/rdf_serialization/jsonld/.")
                st.stop()

            label, chosen = st.selectbox(
                "Dataset",
                options=jsonld_options,
                format_func=lambda x: x[0],
                key="rdf_dataset_jsonld",
            )
            language = "json"

    # Preview
        max_lines = st.slider("Preview lines", 50, 500, 200, 50, key="rdf_preview_lines")
        preview = read_text_head(chosen, max_lines=max_lines)
        st.code(preview if preview else "# (empty preview)", language=language)

    # Downloads
        st.markdown("### Downloads (RDF only)")
        c1, c2 = st.columns(2, vertical_alignment="top")

        with c1:
            if ttl_agents.exists():
                st.download_button(
                "Download agents.ttl",
                    data=read_bytes(ttl_agents),
                   file_name="agents.ttl",
                    mime="text/turtle",
                    use_container_width=True,
                )
            else:
                st.button("Download agents.ttl", disabled=True, use_container_width=True)

            if ttl_atu.exists():
                st.download_button(
                 "Download atu_types.ttl",
                data=read_bytes(ttl_atu),
                file_name="atu_types.ttl",
                mime="text/turtle",
                use_container_width=True,
            )
            else:
                st.button("Download atu_types.ttl", disabled=True, use_container_width=True)

        with c2:
            if jsonld_agents and jsonld_agents.exists():
                st.download_button(
                "Download agents.jsonld",
                data=read_bytes(jsonld_agents),
                file_name="agents.jsonld",
                mime="application/ld+json",
                use_container_width=True,
            )
            else:
                st.button("Download agents.jsonld", disabled=True, use_container_width=True)

            if jsonld_atu and jsonld_atu.exists():
                st.download_button(
                "Download atu_types.jsonld",
                data=read_bytes(jsonld_atu),
                file_name="atu_types.jsonld",
                mime="application/ld+json",
                use_container_width=True,
            )
            else:
               st.button("Download atu_types.jsonld", disabled=True, use_container_width=True)

        st.markdown("---")
        st.markdown("**Links**")
        st.markdown(f"- Repository: {REPO_URL}")







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
            with_anchors = st.checkbox("With anchors", value=True)

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

        anchor_k = st.slider("Anchors per candidate", min_value=3, max_value=12, value=8, step=1)
        submitted = st.form_submit_button("Suggest ATU (Top-3)")

    # Run once on submit -> build canonical export_result -> store in session_state
    if submitted:
        st.session_state["last_tale_id"] = tale_id
        st.session_state["last_text"] = text_ru

        with st.spinner("Classifying…"):
            raw = classify(
                tale_id=tale_id,
                text_ru=text_ru,
                top_k=3,
                with_anchors=with_anchors,
                anchor_k=anchor_k,
            )

        export_result = build_export_result(raw, tale_id=tale_id, text_ru=text_ru, k=3)
        st.session_state["last_export_result"] = export_result

        # default selected ATU
        cands = export_result.get("candidates", []) or []
        if cands:
            st.session_state["selected_atu"] = cands[0].get("atu")

    # -----------------------------
    # Source of truth: canonical model result
    # -----------------------------
    result = st.session_state.get("last_export_result")
    if not result:
        st.info("Run classification to see Top-3 suggestions and anchors.")
        return

    # -----------------------------
    # Human-in-the-loop: Final decision (expert)
    # (UI state only; export will be built from this state every rerun)
    # -----------------------------
    candidates = result.get("candidates", []) or []
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
                expert_state = st.session_state["expert_decision"]  # keep local in sync
        with b2:
            if st.button("Clear expert decision", use_container_width=True):
                st.session_state["expert_decision"] = {}
                expert_state = {}
    else:
        st.caption("Using the model output as the final decision for export.")

    # -----------------------------
    # Effective result for export (model vs expert) — computed on EVERY rerun
    # -----------------------------
    use_expert = bool((expert_state or {}).get("atu"))

    effective_result = copy.deepcopy(result)
    effective_meta = (effective_result.get("meta", {}) or {}).copy()

    model_primary = effective_meta.get("primary_atu")
    effective_meta["model_primary_atu"] = model_primary

    if use_expert:
        final_atu = str(expert_state.get("atu") or "").strip()
        effective_meta["final_decision_source"] = "expert"
        effective_meta["final_atu"] = final_atu
        effective_meta["final_expert_note"] = str(expert_state.get("note", "") or "").strip()
        effective_meta["final_saved_at"] = str(expert_state.get("saved_at", "") or "").strip()
        effective_meta["primary_atu"] = final_atu
        effective_meta["tale_status"] = "expert_override"
    else:
        effective_meta["final_decision_source"] = "model"
        effective_meta["final_atu"] = str(model_primary or "")
        effective_meta["final_expert_note"] = ""
        effective_meta["final_saved_at"] = ""

    effective_result["meta"] = effective_meta

    meta = effective_meta
    tale_id = effective_result.get("id") or st.session_state.get("last_tale_id", "tale")
    st.caption(f"Model version: {meta.get('model_version', '—')}")

    # --- Download JSON-LD (export uses EFFECTIVE result)
    jsonld_obj = to_jsonld(effective_result)
    payload = json.dumps(jsonld_obj, ensure_ascii=False, indent=2).encode("utf-8")

    st.download_button(
        "Download JSON-LD",
        data=payload,
        file_name=f"{tale_id}.jsonld",
        mime="application/ld+json",
    )

    # --- Summary
    st.subheader("Decision summary")
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Status", str(meta.get("tale_status", "—")))
    s2.metric("Final", str(meta.get("primary_atu", "—")))
    s3.metric("Model primary", str(meta.get("model_primary_atu", "—")))
    s4.metric("Δ (top1-top2)", f"{float(meta.get('delta_top12', 0.0) or 0.0):.2f}")

    with st.expander("Run metadata"):
        st.json(meta)

    # --- Top-3 cards
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
            if (not raw_label) or (raw_label.lower().startswith("unknown")):
                title = file_label
            else:
                title = raw_label

            st.caption(title or "Unknown ATU type")
            st.metric("SCORE", f"{float(c.get('score', 0.0) or 0.0):.2f}")
            st.write(f"Confidence: `{c.get('confidence_band','—')}`")
            st.write(c.get("rationale_short", "") or "")
            if st.button("View anchors", key=f"view_anchors_{i}", use_container_width=True):
                st.session_state["selected_atu"] = c.get("atu")

    # --- Anchors panel
    st.subheader("Anchors / Evidence")

    if not atu_options:
        st.info("No candidates available for anchor inspection.")
        return

    selected_atu = st.selectbox(
        "Candidate",
        options=atu_options,
        index=0
        if st.session_state.get("selected_atu") not in atu_options
        else atu_options.index(st.session_state["selected_atu"]),
    )
    st.session_state["selected_atu"] = selected_atu

    cand = next((c for c in candidates if c.get("atu") == selected_atu), None)
    anchors = (cand or {}).get("evidence", {}).get("anchors", []) or []

    if not anchors:
        st.info("No anchors available for this candidate.")
        return

    # Compute spans for highlight
    spans: List[Tuple[int, int]] = []
    for a in anchors:
        if not isinstance(a, dict):
            continue
        span = a.get("span", {}) or {}
        if isinstance(span, dict) and "start_char" in span and "end_char" in span:
            spans.append((int(span["start_char"]), int(span["end_char"])))

    left, right = st.columns([2, 3], vertical_alignment="top")

    with left:
        st.markdown("**Anchors list**")
        for a in anchors:
            if not isinstance(a, dict):
                continue
            st.markdown(
                f"- **{a.get('anchor_id','')}** (score: {float(a.get('score',0.0) or 0.0):.2f})"
            )
            st.caption(a.get("rationale", ""))
            st.write(a.get("snippet", "…"))

        with st.expander("Raw anchors JSON"):
            st.json(anchors)

    with right:
        st.markdown("**Full text with highlights**")
        full_text = st.session_state.get("last_text", "")
        html_block = highlight_text_with_spans(full_text, spans)
        st.markdown(html_block, unsafe_allow_html=True)

    # Raw JSON (canonical)
    with st.expander("Raw export result (source of truth)"):
        st.json(result)



# rendering

def render_page() -> None:
    main = st.session_state.get("nav_main")
    if main == "Home":
        page_home()
        return

    if main == "Explore":
        page_explore()
        return

    # Classify
    page_classify()


# -----------------------------
# App entry
# -----------------------------
def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    _init_state()

    render_left_nav()
    render_page()


if __name__ == "__main__":
    main()
