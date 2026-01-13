from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import joblib
import numpy as np
import pandas as pd


# -----------------------------------------------------------------------------
# Paths: repo_root/models/{model.joblib, labels.json, meta.json}
# File location: repo_root/src/model_store.py
# -----------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = REPO_ROOT / "models"

MODEL_PATH = MODELS_DIR / "model.joblib"
LABELS_PATH = MODELS_DIR / "labels.json"
META_PATH = MODELS_DIR / "meta.json"


@dataclass(frozen=True)
class ModelArtifacts:
    model: Any
    classes: np.ndarray
    meta: Dict[str, Any]


def _normalize_proba(proba: Any) -> np.ndarray:
    """
    sklearn OvR can return:
      - np.ndarray (n_samples, n_classes)
      - list of arrays (n_classes items), each (n_samples, 2) for binary probs
    Normalize to np.ndarray (n_samples, n_classes).
    """
    if isinstance(proba, list):
        cols = []
        for p in proba:
            p = np.asarray(p)
            if p.ndim == 2 and p.shape[1] == 2:
                cols.append(p[:, 1])
            elif p.ndim == 2 and p.shape[1] == 1:
                cols.append(p[:, 0])
            else:
                cols.append(p.reshape(-1))
        return np.column_stack(cols)
    return np.asarray(proba)


@lru_cache(maxsize=1)
def load_artifacts() -> ModelArtifacts:
    """
    Cached loader (process-level).
    Streamlit reruns scripts; this prevents re-loading on each rerun
    within the same Python process.
    """
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Missing model file: {MODEL_PATH}")
    if not LABELS_PATH.exists():
        raise FileNotFoundError(f"Missing labels file: {LABELS_PATH}")
    if not META_PATH.exists():
        raise FileNotFoundError(f"Missing meta file: {META_PATH}")

    model = joblib.load(MODEL_PATH)

    with open(LABELS_PATH, "r", encoding="utf-8") as f:
        classes = np.asarray(json.load(f), dtype=object)

    with open(META_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)

    return ModelArtifacts(model=model, classes=classes, meta=meta)


def _build_X_for_inference(
    *,
    text: str,
    summary: str,
    text_col: str,
    summary_col: str,
) -> pd.DataFrame:
    """
    Build a single-row DataFrame that matches the columns expected by the model.
    Keep it minimal: only text columns (no IDs, no metadata).
    """
    return pd.DataFrame([{text_col: (text or ""), summary_col: (summary or "")}])


def predict_topk(
        
    *,
    text: str,
    summary: str = "",
    k: int = 3,
    text_col: str = "text_norm",
    summary_col: str = "summary_norm",
    parent_fn: Optional[Any] = None,  # pass your atu_parent here if needed
) -> Dict[str, Any]:
    """
    Predict Top-k labels + scores (+ optional parent codes).
    Returns:
      {
        "top_labels": [...],
        "top_scores": [...],
        "meta": {...},
        "top_parents": [...]   # only if parent_fn provided
      }
    """
    arts = load_artifacts()

    if not hasattr(arts.model, "predict_proba"):
        raise AttributeError("Loaded model has no predict_proba(). Expected sklearn Pipeline with OvR.")

    X = _build_X_for_inference(
        text=text,
        summary=summary,
        text_col=text_col,
        summary_col=summary_col,
    )

    proba = _normalize_proba(arts.model.predict_proba(X))
    if proba.ndim != 2 or proba.shape[0] != 1:
        raise ValueError(f"Unexpected proba shape: {proba.shape}")

    p = proba[0]  # (n_classes,)
    k = max(1, min(int(k), len(p)))
    top_idx = np.argsort(-p)[:k]

    top_labels = [str(arts.classes[i]) for i in top_idx]
    top_scores = [float(p[i]) for i in top_idx]

    out: Dict[str, Any] = {"top_labels": top_labels, "top_scores": top_scores, "meta": arts.meta}

    if parent_fn is not None:
        out["top_parents"] = [parent_fn(lab) for lab in top_labels]

    return out

