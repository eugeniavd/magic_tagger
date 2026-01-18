from __future__ import annotations

import re
from urllib.parse import quote

BASE = "https://github.com/eugeniavd/magic_tagger/rdf/"

# -----------------------------
# Helpers
# -----------------------------

def _ensure_str(x: object, field: str) -> str:
    if x is None:
        raise ValueError(f"{field} must not be None")
    s = str(x).strip()
    if not s:
        raise ValueError(f"{field} must not be empty")
    return s

def _path_join(*parts: str) -> str:
    """Join path segments without introducing double slashes."""
    base = BASE.rstrip("/") + "/"
    segs = [p.strip("/") for p in parts if p is not None and str(p).strip("/")]
    return base + "/".join(segs)

def _encode_path_segment(s: str) -> str:
    """
    Percent-encode a single path segment (NOT a full URL).
    Keep RFC3986 unreserved and a few safe chars for readability.
    """
    # unreserved: ALPHA / DIGIT / "-" / "." / "_" / "~"
    return quote(s, safe="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")

# -----------------------------
# ATU normalization
# -----------------------------
_ATU_WS = re.compile(r"\s+")
_ATU_OK = re.compile(r"^[A-Z0-9-]+$")

def normalize_code(code: object, *, star_policy: str = "hyphen") -> str:
    """
    Normalize ATU codes to a stable path-friendly identifier.

    Examples:
        normalize_code("510A")     -> "510A"
        normalize_code("1060*")    -> "1060-star"   (default: star_policy="hyphen")
        normalize_code("1060*",
                       star_policy="percent") -> "1060%2A"

    star_policy:
        - "hyphen": replace '*' with '-star' (readable, stable)
    """
    s = _ensure_str(code, "code")
    s = _ATU_WS.sub("", s).upper()

    if "*" in s:
        if star_policy == "hyphen":
            s = s.replace("*", "-star")
        elif star_policy == "percent":
            # leave '*' in place; it will be percent-encoded later
            pass
        else:
            raise ValueError("star_policy must be 'hyphen' or 'percent'")

    # If already safe (after optional hyphen mapping), return as-is.
    if _ATU_OK.match(s):
        return s

    # Otherwise percent-encode whatever remains unsafe.
    return _encode_path_segment(s)

# -----------------------------
# Public IRI constructors
# -----------------------------

def iri_tale(tale_id: object) -> str:
    """
    Tale record IRI.
    Example: iri_tale("era_vene_12_440_19") -> BASE + "tale/era_vene_12_440_19"
    """
    tid = _ensure_str(tale_id, "tale_id")
    return _path_join("tale", _encode_path_segment(tid))

def iri_volume(volume_id: object) -> str:
    """
    Volume IRI.
    Example: iri_volume("FFC_284") -> BASE + "volume/FFC_284"
    """
    vid = _ensure_str(volume_id, "volume_id")
    return _path_join("volume", _encode_path_segment(vid))

def iri_person(person_id_or_slug: object) -> str:
    """
    Person IRI (collector / narrator / editor).
    Example: iri_person("gromova-olga") -> BASE + "person/gromova-olga"
    """
    pid = _ensure_str(person_id_or_slug, "person_id_or_slug")
    return _path_join("person", _encode_path_segment(pid))

def iri_place(place_id_or_slug: object) -> str:
    """
    Place IRI.
    Example: iri_place("tartu") -> BASE + "place/tartu"
    """
    pl = _ensure_str(place_id_or_slug, "place_id_or_slug")
    return _path_join("place", _encode_path_segment(pl))

def iri_atu(code: object, *, star_policy: str = "hyphen") -> str:
    """
    ATU tale type concept IRI.
    Example: iri_atu("510A") -> BASE + "taleType/atu/510A"
             iri_atu("1060*") -> BASE + "taleType/atu/1060-star"
    """
    norm = normalize_code(code, star_policy=star_policy)
    return _path_join("taleType", "atu", norm)
