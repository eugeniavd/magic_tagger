# streamlit_app.py
from __future__ import annotations

import html
import io
import json
from typing import Any, Dict, List, Optional, Sequence, Tuple

import streamlit as st
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from service import classify

APP_TITLE = "Magic Tagger — ATU Classifier"
APP_SUBTITLE = "Prototype UI (no model): Top-3 ATU + Anchors"


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


def _set_home() -> None:
    st.session_state["nav_main"] = "Home"


def _safe_get(d: Dict[str, Any], path: Sequence[str], default=None):
    cur: Any = d
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur


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
        label_csv = '"' + label.replace('"', '""') + '"'  # CSV escaping
        score = s.get("score", "")
        band = s.get("confidence_band", "")

        lines.append(f"{rank},{atu},{label_csv},{score},{band}")

    exports["CSV"] = ("\n".join(lines) + "\n").encode("utf-8")

    return exports


# -----------------------------
# Top bar
# -----------------------------
def render_top_bar() -> None:
    col1, col2, col3 = st.columns([6, 3, 2], vertical_alignment="center")

    with col1:
        if st.button(APP_TITLE, use_container_width=True):
            _set_home()
        st.caption(APP_SUBTITLE)

    with col2:
        st.markdown("**Quick Export**")
        exports = make_quick_exports(st.session_state.get("last_result"))
        fmt = st.selectbox("Format", ["JSON-LD", "Turtle", "CSV"], label_visibility="collapsed")
        filename_map = {"JSON-LD": "export.jsonld", "Turtle": "export.ttl", "CSV": "export.csv"}
        st.download_button(
            label=f"Download {fmt}",
            data=exports[fmt],
            file_name=filename_map[fmt],
            mime="application/octet-stream",
            use_container_width=True,
            disabled=(st.session_state.get("last_result") is None),
        )

    with col3:
        st.markdown("**Help**")
        if st.button("Open help", use_container_width=True):
            st.session_state["help_open"] = not st.session_state.get("help_open", False)

    if st.session_state.get("help_open", False):
        with st.expander("Onboarding / Documentation", expanded=True):
            st.markdown(
                """
                **What you can do in this prototype**
                - Navigate Explore pages (placeholders for now).
                - Paste or upload a Russian tale text in **Classify**.
                - Get Top-3 ATU suggestions with anchors (evidence spans) and a status label.

                **Methodology / Licenses**
                - Add links to your methodology, dataset statement, and licenses here.
                - Add a short note on limitations (no model, stub evidence).
                """
            )


# -----------------------------
# Left navigation rail
# -----------------------------
def render_left_nav() -> None:
    st.sidebar.markdown("### Navigation")

    main = st.sidebar.radio(
        "Main",
        ["Home", "Explore", "Classify"],
        key="nav_main",
        label_visibility="collapsed",
    )

    if main == "Explore":
        st.sidebar.markdown("#### Explore")
        st.sidebar.radio(
            "Explore sections",
            ["Overview", "Types", "Maps & Timeline", "Names & Roles"],
            key="nav_explore",
            label_visibility="collapsed",
        )

    st.sidebar.markdown("---")
    st.sidebar.caption("Prototype: UI + service contract (no model)")


# -----------------------------
# Pages
# -----------------------------
def page_home() -> None:
    st.header("Home")
    st.write(
        "Project overview and entry points to core workflows."
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Start exploring", use_container_width=True):
            st.session_state["nav_main"] = "Explore"
            st.session_state["nav_explore"] = "Overview"
    with c2:
        if st.button("Try classification", use_container_width=True):
            st.session_state["nav_main"] = "Classify"

    st.markdown("---")
    st.subheader("Project overview")
    st.info(
        "Replace this block with: corpus scope, data sources, rights statement, and methodology summary."
    )


def page_explore_overview() -> None:
    st.header("Explore — Overview")
    st.write("High-level stats and featured maps/charts (placeholder).")

    m1, m2, m3 = st.columns(3)
    m1.metric("Tales", "—")
    m2.metric("Volumes", "—")
    m3.metric("Collectors", "—")

    st.info("Add: Top ATU types, decade distribution, region map, and collector network highlights.")


def page_explore_types() -> None:
    st.header("Explore — Types")
    st.write("Browse ATU / custom types with links to examples (placeholder).")

    st.info("Add: searchable list of types, type cards, and example tale links.")


def page_explore_maps_timeline() -> None:
    st.header("Explore — Maps & Timeline")
    st.write("Spatial–temporal exploration of tales and collectors (placeholder).")

    st.info("Add: map (parishes/regions) + timeline chart + filters.")


def page_explore_names_roles() -> None:
    st.header("Explore — Names & Roles")
    st.write("People, their roles, and relationships (placeholder).")

    st.info("Add: entity list, role facets, and relationship edges (collector↔narrator↔place).")


def page_classify() -> None:
    st.header("Classify")
    st.write(
        "Paste or upload a text to check its type (Top-3 ATU suggestions), inspect evidence anchors, "
        "and later link to same-type texts and plot variations."
    )

    with st.form("classify_form", clear_on_submit=False):
        c1, c2 = st.columns([2, 1])
        with c1:
            tale_id = st.text_input("External tale ID", value=st.session_state.get("last_tale_id", "external_001"))
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

    if submitted:
        st.session_state["last_tale_id"] = tale_id
        st.session_state["last_text"] = text_ru

        with st.spinner("Classifying (stub)…"):
            result = classify(
                tale_id=tale_id,
                text_ru=text_ru,
                top_k=3,
                with_anchors=with_anchors,
                anchor_k=anchor_k,
            )
        st.session_state["last_result"] = result

        # default selected ATU
        suggestions = result.get("suggestions", [])
        if suggestions and isinstance(suggestions, list) and isinstance(suggestions[0], dict):
            st.session_state["selected_atu"] = suggestions[0].get("atu_code")

    result = st.session_state.get("last_result")
    if not result:
        st.info("Run classification to see Top-3 suggestions and anchors.")
        return

    # Summary
    run = result.get("run", {})
    st.subheader("Decision summary")

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Status", str(run.get("tale_status", "—")))
    s2.metric("Primary", str(run.get("primary_atu", "—")))
    s3.metric("Co-types", ", ".join(run.get("co_types", []) or []) or "—")
    s4.metric("Δ (top1-top2)", f"{run.get('delta_top12', 0.0):.2f}")

    with st.expander("Run metadata"):
        st.json(run)

    # Top-3 cards
    st.subheader("Top-3 ATU candidates")
    suggestions = result.get("suggestions", [])
    if not isinstance(suggestions, list) or not suggestions:
        st.warning("No suggestions returned.")
        return

    cols = st.columns(3)
    for i, s in enumerate(suggestions[:3]):
        if not isinstance(s, dict):
            continue
        with cols[i]:
            st.markdown(f"**#{s.get('rank', i+1)} — {s.get('atu_code','')}**")
            st.caption(s.get("label", ""))
            st.metric("SCORE", f"{float(s.get('score', 0.0)):.2f}")
            st.write(f"Confidence: `{s.get('confidence_band','—')}`")
            st.write(s.get("rationale_short", ""))
            if st.button("View anchors", key=f"view_anchors_{i}", use_container_width=True):
                st.session_state["selected_atu"] = s.get("atu_code")

    # Anchors panel
    st.subheader("Anchors / Evidence")
    atu_options = [s.get("atu_code") for s in suggestions if isinstance(s, dict) and s.get("atu_code")]
    selected_atu = st.selectbox(
        "Candidate",
        options=atu_options,
        index=0 if st.session_state.get("selected_atu") not in atu_options else atu_options.index(st.session_state["selected_atu"]),
    )
    st.session_state["selected_atu"] = selected_atu

    anchors_map = result.get("anchors", {}) or {}
    anchors = anchors_map.get(selected_atu, []) if isinstance(anchors_map, dict) else []

    if not anchors:
        st.info("No anchors available for this candidate.")
        return

    # Show anchor list + compute spans for highlight
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
            st.markdown(f"- **{a.get('anchor_id','')}** (score: {float(a.get('score',0.0)):.2f})")
            st.caption(a.get("rationale", ""))
            st.write(a.get("snippet", "…"))

        with st.expander("Raw anchors JSON"):
            st.json(anchors)

    with right:
        st.markdown("**Full text with highlights**")
        full_text = st.session_state.get("last_text", "")
        html_block = highlight_text_with_spans(full_text, spans)
        st.markdown(html_block, unsafe_allow_html=True)

    # Raw JSON
    with st.expander("Raw response JSON"):
        st.json(result)


def render_page() -> None:
    main = st.session_state.get("nav_main")
    if main == "Home":
        page_home()
        return

    if main == "Explore":
        sub = st.session_state.get("nav_explore", "Overview")
        if sub == "Overview":
            page_explore_overview()
        elif sub == "Types":
            page_explore_types()
        elif sub == "Maps & Timeline":
            page_explore_maps_timeline()
        else:
            page_explore_names_roles()
        return

    # Classify
    page_classify()


# -----------------------------
# App entry
# -----------------------------
def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    _init_state()

    render_top_bar()
    st.divider()

    render_left_nav()
    render_page()


if __name__ == "__main__":
    main()
