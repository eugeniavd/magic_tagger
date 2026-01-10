# config.py
"""
Centralized configuration for ATU type assignment (Top-3 + Anchors).

This file fixes:
1) Status thresholds (auto-adopt / needs review / weak) based on:
   - SCORE  : calibrated model confidence in [0, 1]
   - ANCHOR : rule-based evidence strength in [0, 1]
   - Δ      : SCORE1 - SCORE2 (separation between top-1 and top-2)

2) Optional multi-label policy (when one tale can legitimately have several ATU types).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


# -----------------------------
# 1) Tale-level status labels
# -----------------------------
class TaleStatus(str, Enum):
    AUTO_ADOPT_PRIMARY = "auto_adopt_primary"
    NEEDS_REVIEW_A = "needs_review_A"
    NEEDS_REVIEW_B = "needs_review_B"
    WEAK = "weak"


# -----------------------------
# 2) Threshold rules (priority-ordered)
# -----------------------------
@dataclass(frozen=True)
class StatusRule:
    """
    A rule is satisfied when:
      score >= min_score AND anchor >= min_anchor AND (delta >= min_delta if provided)
    """
    priority: int
    label: TaleStatus
    min_score: float
    min_anchor: float
    min_delta: Optional[float] = None  # Δ = SCORE1 - SCORE2 (only for some rules)


# Fixed thresholds per your plan:
# Priority 1: auto-adopt (primary) if SCORE ≥ 0.75 AND ANCHOR ≥ 0.60 AND Δ ≥ 0.15
# Priority 2: needs review (A)      if SCORE ≥ 0.50 AND ANCHOR ≥ 0.40
# Priority 3: needs review (B)      if SCORE ≥ 0.35 AND ANCHOR ≥ 0.70
STATUS_RULES: Tuple[StatusRule, ...] = (
    StatusRule(
        priority=1,
        label=TaleStatus.AUTO_ADOPT_PRIMARY,
        min_score=0.75,
        min_anchor=0.60,
        min_delta=0.15,
    ),
    StatusRule(
        priority=2,
        label=TaleStatus.NEEDS_REVIEW_A,
        min_score=0.50,
        min_anchor=0.40,
        min_delta=None,
    ),
    StatusRule(
        priority=3,
        label=TaleStatus.NEEDS_REVIEW_B,
        min_score=0.35,
        min_anchor=0.70,
        min_delta=None,
    ),
)

DEFAULT_STATUS: TaleStatus = TaleStatus.WEAK

# Convenience threshold used in reporting (“auto-adopt share (max_score ≥ 0.75)” proxy).
HIGH_CONFIDENCE_SCORE_PROXY: float = 0.75


# -----------------------------
# 3) Multi-label assignment policy (optional)
# -----------------------------
# Rationale: even if we always output Top-3, we may also propose "co-types"
# when candidates are close to the primary and have strong evidence.
ALLOW_MULTI_LABEL: bool = True

# Candidate i becomes a co-type if it is close enough to top-1
# and passes minimal confidence/evidence thresholds.
CO_TYPE_MAX_SCORE_GAP: float = 0.10  # allow if SCORE1 - SCOREi <= this value
CO_TYPE_MIN_SCORE: float = 0.55
CO_TYPE_MIN_ANCHOR: float = 0.55

# Limit how many co-types we output (besides primary).
MAX_CO_TYPES: int = 2


# -----------------------------
# 4) Anchors (evidence) display limits (UI-facing)
# -----------------------------
DEFAULT_TOP_K: int = 3          # Top-3 ATU candidates
DEFAULT_ANCHOR_K: int = 8       # anchors per candidate
ANCHOR_SNIPPET_MAX_CHARS: int = 280

# Anchors (rule-based evidence)
ANCHORS_JSON_PATH: str = "models/anchors.json"

# ANCHOR = 1 - exp(-alpha * sum_w)
ANCHOR_ALPHA: float = 6.0

# Matching / UI constraints
ANCHOR_CASEFOLD: bool = True
ANCHOR_MAX_HITS_PER_PATTERN: int = 2     # limit repeated matches of same pattern
ANCHOR_MAX_HITS_PER_TYPE: int = 12       # cap hits shown per ATU candidate
ANCHOR_SNIPPET_WINDOW: int = 120         # chars around match

# -----------------------------
# 5) Evaluation exclusions (for metrics like Hit@3)
# -----------------------------
# Define a consistent “ambiguous excluded” policy for evaluation.
# You can map your dataset columns to these values.
AMBIGUOUS_GOLD_FLAGS = {
    "ambiguous",          # generic
    "uncertain",          # annotator uncertainty
    "conflict",           # conflicting labels
    "needs_review",       # not finalized
    "mapping_ambiguous",  # mapping from local scheme is not reliable
}

MISSING_GOLD_VALUES = {None, "", "NA", "N/A", "no_atu"}


# -----------------------------
# Utility
# -----------------------------
def clip01(x: float) -> float:
    """Clamp a numeric value into [0, 1]."""
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return float(x)

