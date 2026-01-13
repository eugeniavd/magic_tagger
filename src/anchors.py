
from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from src.config import (
    ANCHORS_JSON_PATH,
    ANCHOR_ALPHA,
    ANCHOR_CASEFOLD,
    ANCHOR_MAX_HITS_PER_PATTERN,
    ANCHOR_MAX_HITS_PER_TYPE,
    ANCHOR_SNIPPET_WINDOW,
)

# -----------------------------
# Data structures
# -----------------------------
@dataclass(frozen=True)
class AnchorPattern:
    pattern: str
    w: float
    is_regex: bool = False  # allow future extension


@dataclass(frozen=True)
class AnchorHit:
    pattern: str
    w: float
    start_char: int
    end_char: int
    snippet: str


@dataclass(frozen=True)
class AnchorResult:
    atu_code: str
    anchor_score: float
    sum_w: float
    hits: Tuple[AnchorHit, ...]


# -----------------------------
# Helpers
# -----------------------------
def normalize_atu_code(code: str) -> str:
    """
    Normalize ATU codes across variants:
      "ATU_327A" -> "ATU-327A"
      "atu-327a" -> "ATU-327A"
    """
    c = (code or "").strip()
    if not c:
        return ""
    c = c.upper().replace("_", "-")
    # ensure starts with ATU-
    if c.startswith("ATU") and not c.startswith("ATU-"):
        # "ATU327A" -> "ATU-327A"
        c = "ATU-" + c[3:].lstrip("-")
    return c


def clip01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else float(x)


def make_snippet(text: str, start: int, end: int, window: int) -> str:
    """
    Build a readable snippet around match span.
    """
    n = len(text)
    left = max(0, start - window)
    right = min(n, end + window)
    snippet = text[left:right].strip()
    if left > 0:
        snippet = "…" + snippet
    if right < n:
        snippet = snippet + "…"
    return snippet


# -----------------------------
# AnchorEngine
# -----------------------------
class AnchorEngine:
    def __init__(
        self,
        anchors_path: str = ANCHORS_JSON_PATH,
        alpha: float = ANCHOR_ALPHA,
        casefold: bool = ANCHOR_CASEFOLD,
    ) -> None:
        self.anchors_path = anchors_path
        self.alpha = float(alpha)
        self.casefold = bool(casefold)

        self._patterns_by_type: Dict[str, List[AnchorPattern]] = {}
        self._compiled_by_type: Dict[str, List[Tuple[AnchorPattern, re.Pattern]]] = {}

        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.anchors_path):
            # Empty engine if file missing (graceful for dev)
            self._patterns_by_type = {}
            self._compiled_by_type = {}
            return

        with open(self.anchors_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        patterns_by_type: Dict[str, List[AnchorPattern]] = {}
        for k, items in raw.items():
            atu = normalize_atu_code(k)
            if not atu:
                continue
            lst: List[AnchorPattern] = []
            if isinstance(items, list):
                for it in items:
                    if not isinstance(it, dict):
                        continue
                    p = str(it.get("pattern", "")).strip()
                    if not p:
                        continue
                    w = float(it.get("w", 0.0))
                    is_regex = bool(it.get("is_regex", False))
                    lst.append(AnchorPattern(pattern=p, w=w, is_regex=is_regex))
            patterns_by_type[atu] = lst

        self._patterns_by_type = patterns_by_type

        # Compile regex for each pattern
        compiled: Dict[str, List[Tuple[AnchorPattern, re.Pattern]]] = {}
        flags = re.IGNORECASE if self.casefold else 0

        for atu, pats in self._patterns_by_type.items():
            compiled_list: List[Tuple[AnchorPattern, re.Pattern]] = []
            for ap in pats:
                if ap.is_regex:
                    rx = re.compile(ap.pattern, flags=flags)
                else:
                    rx = re.compile(re.escape(ap.pattern), flags=flags)
                compiled_list.append((ap, rx))
            compiled[atu] = compiled_list

        self._compiled_by_type = compiled

    def score_type(self, text: str, atu_code: str) -> AnchorResult:
        """
        Compute ANCHOR score and hits for a single ATU code.
        - Sum weights over UNIQUE patterns that hit at least once.
        - Collect up to ANCHOR_MAX_HITS_PER_PATTERN matches per pattern.
        - Cap total hits per type for UI.
        """
        atu = normalize_atu_code(atu_code)
        if not atu or atu not in self._compiled_by_type:
            return AnchorResult(atu_code=atu or normalize_atu_code(atu_code), anchor_score=0.0, sum_w=0.0, hits=tuple())

        if not text:
            return AnchorResult(atu_code=atu, anchor_score=0.0, sum_w=0.0, hits=tuple())

        compiled_list = self._compiled_by_type[atu]
        hits: List[AnchorHit] = []
        sum_w = 0.0

        # To avoid weight inflation, count each pattern at most once in sum_w
        for ap, rx in compiled_list:
            per_pattern_hits = 0
            pattern_hit = False

            for m in rx.finditer(text):
                if per_pattern_hits >= ANCHOR_MAX_HITS_PER_PATTERN:
                    break
                start, end = m.start(), m.end()
                snippet = make_snippet(text, start, end, ANCHOR_SNIPPET_WINDOW)
                hits.append(AnchorHit(pattern=ap.pattern, w=float(ap.w), start_char=start, end_char=end, snippet=snippet))
                per_pattern_hits += 1
                pattern_hit = True

                if len(hits) >= ANCHOR_MAX_HITS_PER_TYPE:
                    break

            if pattern_hit:
                sum_w += float(ap.w)

            if len(hits) >= ANCHOR_MAX_HITS_PER_TYPE:
                break

        # ANCHOR = 1 - exp(-alpha * sum_w)
        anchor_score = 1.0 - math.exp(-self.alpha * max(0.0, sum_w))
        return AnchorResult(atu_code=atu, anchor_score=clip01(anchor_score), sum_w=sum_w, hits=tuple(hits))

    def score_types(self, text: str, atu_codes: Sequence[str]) -> Dict[str, AnchorResult]:
        """
        Batch score for a list of ATU codes (e.g., Top-3 from the model).
        """
        out: Dict[str, AnchorResult] = {}
        for c in atu_codes:
            atu = normalize_atu_code(c)
            if not atu:
                continue
            out[atu] = self.score_type(text, atu)
        return out
