# scoring.py
"""
Decision logic for ATU Top-3 + Anchors.

Implements tale-level status assignment using fixed thresholds from config.py:

Priority 1: auto-adopt (primary) if SCORE ≥ 0.75 AND ANCHOR ≥ 0.60 AND Δ ≥ 0.15
Priority 2: needs review (A)      if SCORE ≥ 0.50 AND ANCHOR ≥ 0.40
Priority 3: needs review (B)      if SCORE ≥ 0.35 AND ANCHOR ≥ 0.70
Else: weak

Where:
- SCORE  : calibrated model confidence in [0,1]
- ANCHOR : rule-based evidence strength in [0,1]
- Δ      : SCORE1 - SCORE2 (top-1 vs top-2 separation)

Also supports optional multi-label (co-types) proposal.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

from src.config import (
    TaleStatus,
    STATUS_RULES,
    DEFAULT_STATUS,
    ALLOW_MULTI_LABEL,
    CO_TYPE_MAX_SCORE_GAP,
    CO_TYPE_MIN_SCORE,
    CO_TYPE_MIN_ANCHOR,
    MAX_CO_TYPES,
    clip01,
)


# -----------------------------
# Data structures
# -----------------------------
@dataclass(frozen=True)
class Candidate:
    """
    One candidate ATU type for a tale.
    """
    atu_code: str
    score: float   # calibrated confidence
    anchor: float  # evidence strength


@dataclass(frozen=True)
class Decision:
    """
    Decision output used by UI and persistence.
    """
    tale_status: TaleStatus
    primary_atu: Optional[str]
    co_types: Tuple[str, ...]
    delta_top12: float
    candidates: Tuple[Candidate, ...]  # normalized and sorted by score desc


# -----------------------------
# Helpers
# -----------------------------
def normalize_candidates(candidates: Iterable[Candidate]) -> List[Candidate]:
    """
    Clamp SCORE and ANCHOR to [0,1], drop empty codes, and sort desc by SCORE.
    """
    norm: List[Candidate] = []
    for c in candidates:
        code = (c.atu_code or "").strip()
        if not code:
            continue
        norm.append(
            Candidate(
                atu_code=code,
                score=clip01(float(c.score)),
                anchor=clip01(float(c.anchor)),
            )
        )

    norm.sort(key=lambda x: x.score, reverse=True)
    return norm


def compute_delta_top12(sorted_candidates: Sequence[Candidate]) -> float:
    """
    Δ = SCORE1 - SCORE2. If no second candidate, Δ = 0.
    """
    if len(sorted_candidates) < 2:
        return 0.0
    return clip01(sorted_candidates[0].score - sorted_candidates[1].score)


def decide_status(primary: Candidate, delta_top12: float) -> TaleStatus:
    """
    Apply priority-ordered rules to the primary (top-1) candidate.
    """
    for rule in sorted(STATUS_RULES, key=lambda r: r.priority):
        if primary.score < rule.min_score:
            continue
        if primary.anchor < rule.min_anchor:
            continue
        if rule.min_delta is not None and delta_top12 < rule.min_delta:
            continue
        return rule.label
    return DEFAULT_STATUS


def propose_co_types(sorted_candidates: Sequence[Candidate]) -> Tuple[str, ...]:
    """
    Optional: propose additional ATU types ("co-types") when a tale plausibly
    has multiple correct types. Uses simple closeness + minimum evidence constraints.

    A candidate i becomes a co-type if:
      SCORE1 - SCOREi <= CO_TYPE_MAX_SCORE_GAP
      SCOREi >= CO_TYPE_MIN_SCORE
      ANCHORi >= CO_TYPE_MIN_ANCHOR

    Returns at most MAX_CO_TYPES.
    """
    if not ALLOW_MULTI_LABEL or len(sorted_candidates) < 2:
        return tuple()

    top1 = sorted_candidates[0]
    co: List[str] = []

    for cand in sorted_candidates[1:]:
        if len(co) >= MAX_CO_TYPES:
            break

        score_gap = top1.score - cand.score
        if score_gap <= CO_TYPE_MAX_SCORE_GAP and cand.score >= CO_TYPE_MIN_SCORE and cand.anchor >= CO_TYPE_MIN_ANCHOR:
            co.append(cand.atu_code)

    return tuple(co)


# -----------------------------
# Main API
# -----------------------------
def make_decision(top_candidates: Sequence[Candidate]) -> Decision:
    """
    Input: a list (typically Top-3) of Candidate(atu_code, score, anchor).
    Output: Decision with normalized+sorted candidates, tale-level status, primary,
            optional co-types, and Δ (top-1 vs top-2).

    Notes:
    - Status is determined ONLY from the top-1 candidate + Δ, per your plan.
    - Top-3 is still returned for UI even when status is "weak".
    """
    cands = normalize_candidates(top_candidates)
    delta = compute_delta_top12(cands)

    if not cands:
        return Decision(
            tale_status=DEFAULT_STATUS,
            primary_atu=None,
            co_types=tuple(),
            delta_top12=delta,
            candidates=tuple(),
        )

    primary = cands[0]
    status = decide_status(primary, delta)
    co_types = propose_co_types(cands)

    return Decision(
        tale_status=status,
        primary_atu=primary.atu_code,
        co_types=co_types,
        delta_top12=delta,
        candidates=tuple(cands),
    )


# -----------------------------
# Convenience: proxy metric flag
# -----------------------------
def is_high_confidence_proxy(top_candidates: Sequence[Candidate], threshold: float = 0.75) -> bool:
    """
    For reporting: "auto-adopt share (max_score ≥ 0.75)" proxy.
    """
    cands = normalize_candidates(top_candidates)
    if not cands:
        return False
    return cands[0].score >= float(threshold)