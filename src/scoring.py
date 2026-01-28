# scoring.py
"""
Scoring and decision helpers for ATU Top-K suggestions.

Policy-agnostic:
- normalize + sort by SCORE
- compute Δ = score1 - score2
- optionally propose co-types (score proximity only)

Confidence policy (High/Else) MUST be applied upstream (classify())
using thresholds loaded from models/meta.json.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

from src.config import (
    ALLOW_MULTI_LABEL,
    CO_TYPE_MAX_SCORE_GAP,
    CO_TYPE_MIN_SCORE,
    MAX_CO_TYPES,
    clip01,
)              # limit additional co-types

# -----------------------------
# Data structures
# -----------------------------
@dataclass(frozen=True)
class Candidate:
    """
    One candidate ATU type for a tale.
    """
    atu_code: str
    score: float   # model score in [0,1]
    anchor: float = 0.0  # backward-compat only; always forced to 0.0


@dataclass(frozen=True)
class Decision:
    """
    Decision output used by UI and persistence.
    """
    tale_status: str  # placeholder, policy lives upstream
    primary_atu: Optional[str]
    co_types: Tuple[str, ...]
    delta_top12: float
    candidates: Tuple[Candidate, ...]


# -----------------------------
# Helpers
# -----------------------------
def _atu_code_soft_norm(code: str) -> str:
    """
    Minimal, policy-agnostic normalization:
    - strip whitespace
    - drop trailing '*' (uncertainty markers)
    Full normalization (e.g., ATU-480A vs 480a) should be upstream.
    """
    return str(code or "").strip().rstrip("*").strip()


def normalize_candidates(candidates: Iterable[Candidate]) -> List[Candidate]:
    """
    Clamp SCORE to [0,1], drop empty codes, minimal-normalize codes,
    and sort desc by SCORE.
    """
    norm: List[Candidate] = []
    for c in candidates:
        code = _atu_code_soft_norm(c.atu_code)
        if not code:
            continue
        norm.append(
            Candidate(
                atu_code=code,
                score=clip01(float(c.score)),
                anchor=0.0,  # anchors disabled in current pipeline
            )
        )

    norm.sort(key=lambda x: x.score, reverse=True)
    return norm


def compute_delta_top12(sorted_candidates: Sequence[Candidate]) -> float:
    """
    Δ = SCORE1 - SCORE2. If no second candidate, Δ = 0.
    Assumes candidates are already sorted desc by SCORE.
    """
    if len(sorted_candidates) < 2:
        return 0.0
    d = float(sorted_candidates[0].score) - float(sorted_candidates[1].score)
    return d if d > 0.0 else 0.0


def propose_co_types(sorted_candidates: Sequence[Candidate]) -> Tuple[str, ...]:
    """
    Optional: propose additional ATU types ("co-types") based on score proximity only.

    A candidate i becomes a co-type if:
      SCORE1 - SCOREi <= CO_TYPE_MAX_SCORE_GAP
      SCOREi >= CO_TYPE_MIN_SCORE

    Returns at most MAX_CO_TYPES.
    """
    if not ALLOW_MULTI_LABEL or len(sorted_candidates) < 2:
        return tuple()

    top1 = sorted_candidates[0]
    co: List[str] = []

    for cand in sorted_candidates[1:]:
        if len(co) >= MAX_CO_TYPES:
            break

        score_gap = float(top1.score) - float(cand.score)
        if score_gap <= CO_TYPE_MAX_SCORE_GAP and float(cand.score) >= CO_TYPE_MIN_SCORE:
            co.append(cand.atu_code)

    return tuple(co)


# -----------------------------
# Main API
# -----------------------------
def make_decision(top_candidates: Sequence[Candidate]) -> Decision:
    """
    Input: list of Candidate(atu_code, score, anchor=0.0).
    Output: normalized+sorted candidates, primary_atu, Δ, optional co-types.

    NOTE:
    - tale_status is a placeholder because policy lives upstream.
      classify() should set the final policy outputs (confidence_band, tale_status, etc.).
    """
    cands = normalize_candidates(top_candidates)
    delta = compute_delta_top12(cands)

    if not cands:
        return Decision(
            tale_status="no_prediction",
            primary_atu=None,
            co_types=tuple(),
            delta_top12=delta,
            candidates=tuple(),
        )

    primary = cands[0]
    co_types = propose_co_types(cands)

    return Decision(
        tale_status="unreviewed",
        primary_atu=primary.atu_code,
        co_types=co_types,
        delta_top12=delta,
        candidates=tuple(cands),
    )


def is_high_confidence_proxy(top_candidates: Sequence[Candidate], threshold: float) -> bool:
    """
    Proxy helper for reporting when you explicitly pass a threshold.
    Thresholds must come from models/meta.json (do not hardcode here).
    """
    cands = normalize_candidates(top_candidates)
    if not cands:
        return False
    return float(cands[0].score) >= float(threshold)
