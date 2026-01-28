"""
Centralized configuration for ATU type assignment (Top-3).

This file defines a SINGLE source of truth for the current decision policy:

- Model outputs Top-K candidates with SCORE in [0,1].
- We compute Δ = SCORE1 - SCORE2.
- We assign a binary confidence band:
    * high  -> can be accepted with minimal review
    * else  -> requires human review
  In UX we display: high / low
  In machine-readable provenance we keep policy id: "high_else"

No anchors/evidence are used in the current pipeline.
"""

from __future__ import annotations

from enum import Enum
from typing import Set

ALLOW_MULTI_LABEL: bool = True

CO_TYPE_MAX_SCORE_GAP: float = 0.10 
CO_TYPE_MIN_SCORE: float = 0.55     
MAX_CO_TYPES: int = 2  

# -----------------------------
# 1) Tale-level routing label (UX-facing)
# -----------------------------
class TaleStatus(str, Enum):
    ACCEPT = "accept"   # ok to accept Top-1 as a suggestion with minimal review
    REVIEW = "review"   # requires human review / verification


DEFAULT_STATUS: TaleStatus = TaleStatus.REVIEW


# -----------------------------
# 2) Decision policy (binary)
# -----------------------------
# Provenance id (machine) and UX label (human)
DECISION_POLICY_ID: str = "high_else"
DECISION_POLICY_LABEL: str = "High/Else"

# Thresholds found on TRAIN/CV analysis:
# Choose the values you decided to operationalize.
# Based on your printed candidates, one good "high" region was:
#   min_score ≈ 0.38 and min_delta ≈ 0.14 (high precision, low coverage).
HIGH_MIN_SCORE: float = 0.38
HIGH_MIN_DELTA: float = 0.14

# Convenience: band names
CONF_BAND_HIGH: str = "high"
CONF_BAND_ELSE: str = "else"  # machine-readable
CONF_BAND_LOW_UX: str = "low" # UX-readable (maps from else)


# -----------------------------
# 3) Top-K defaults (UI-facing)
# -----------------------------
DEFAULT_TOP_K: int = 3


# -----------------------------
# 4) Evaluation exclusions (for metrics like Hit@3)
# -----------------------------
AMBIGUOUS_GOLD_FLAGS: Set[str] = {
    "ambiguous",
    "uncertain",
    "conflict",
    "needs_review",
    "mapping_ambiguous",
}

MISSING_GOLD_VALUES: Set[str] = {None, "", "NA", "N/A", "no_atu"}


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
