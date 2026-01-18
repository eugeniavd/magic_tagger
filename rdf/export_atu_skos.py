# src/export_atu_skos.py
from __future__ import annotations

from typing import Iterable, Set, List, Dict, Optional
import pandas as pd

from rdf.kg_helpers import iri_atu

RFT_ONT = "https://github.com/eugeniavd/magic_tagger/rdf/ontology/#"
ATU_SCHEME_QNAME = "rft:ATU_Scheme"

PREFIXES_TTL = """@prefix rft: <https://github.com/eugeniavd/magic_tagger/rdf/ontology/#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

"""

def _ttl_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').strip()

def _iter_codes_from_df(df: pd.DataFrame, col: str) -> Iterable[str]:
    if col not in df.columns:
        raise KeyError(f"Column '{col}' not found in df")
    for cell in df[col].tolist():
        if cell is None or (isinstance(cell, float) and pd.isna(cell)):
            continue
        if isinstance(cell, list):
            for x in cell:
                if x is None:
                    continue
                s = str(x).strip()
                if s:
                    yield s
        else:
            s = str(cell).strip()
            if s:
                yield s

def collect_unique_atu_codes(df: pd.DataFrame, col: str = "atu_codes") -> List[str]:
    seen: Set[str] = set()
    for raw in _iter_codes_from_df(df, col):
        code = str(raw).strip().replace(" ", "").upper()
        if code:
            seen.add(code)
    return sorted(seen)

def build_code_title_map(
    titles: pd.DataFrame | Dict[str, str],
    code_col: str = "code",
    title_col: str = "title_en",
) -> Dict[str, str]:
    """
    Returns dict: ATU_CODE -> title (English).
    Codes are normalized for lookup: uppercase, no spaces.
    """
    if isinstance(titles, dict):
        out: Dict[str, str] = {}
        for k, v in titles.items():
            code = str(k).strip().replace(" ", "").upper()
            title = str(v).strip()
            if code and title:
                out[code] = title
        return out

    if code_col not in titles.columns or title_col not in titles.columns:
        raise KeyError(f"titles_df must contain columns '{code_col}' and '{title_col}'")

    out: Dict[str, str] = {}
    for _, row in titles.iterrows():
        code = str(row[code_col]).strip().replace(" ", "").upper()
        title = str(row[title_col]).strip()
        if code and title and title.lower() != "nan":
            out[code] = title
    return out

def build_atu_skos_ttl(
    df: pd.DataFrame,
    titles: pd.DataFrame | Dict[str, str],
    *,
    codes_col: str = "atu_codes",
    scheme_label_en: str = "ATU Tale Types (local mint)",
    scheme_source_iri: Optional[str] = None,  # e.g. "https://search.worldcat.org/title/57716857"
    star_policy: str = "hyphen",
) -> str:
    codes = collect_unique_atu_codes(df, col=codes_col)
    code2title = build_code_title_map(titles)

    lines: List[str] = []
    lines.append(PREFIXES_TTL)

    # Scheme
    scheme_lines = [
        f"{ATU_SCHEME_QNAME} a skos:ConceptScheme ;",
        f'  skos:prefLabel "{_ttl_escape(scheme_label_en)}"@en ;',
        '  rdfs:comment "Local SKOS scheme minted from ATU codes observed in the canonical table."@en'
    ]
    if scheme_source_iri:
        scheme_lines[-1] += " ;"
        scheme_lines.append(f"  dcterms:source <{scheme_source_iri}>")
        lines.append("\n".join(scheme_lines) + " .\n")
    else:
        lines.append("\n".join(scheme_lines) + " .\n")

    # Concepts
    for code in codes:
        title = code2title.get(code)
        if title:
            pref = f"ATU {code} {title}"
        else:
            pref = f"ATU {code}"

        concept_iri = f"<{iri_atu(code, star_policy=star_policy)}>"

        lines.append(
            f"{concept_iri} a skos:Concept ;\n"
            f"  skos:inScheme {ATU_SCHEME_QNAME} ;\n"
            f'  skos:notation "{_ttl_escape(code)}" ;\n'
            f'  skos:prefLabel "{_ttl_escape(pref)}"@en .\n'
        )

    return "\n".join(lines)

def write_atu_skos_ttl(
    df: pd.DataFrame,
    titles: pd.DataFrame | Dict[str, str],
    out_path: str,
    *,
    codes_col: str = "atu_codes",
    scheme_label_en: str = "ATU Tale Types (local mint)",
    scheme_source_iri: Optional[str] = None,
    star_policy: str = "hyphen",
) -> str:
    ttl = build_atu_skos_ttl(
        df, titles,
        codes_col=codes_col,
        scheme_label_en=scheme_label_en,
        scheme_source_iri=scheme_source_iri,
        star_policy=star_policy,
    )
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(ttl)
    return out_path
