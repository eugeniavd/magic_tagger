from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd

# -----------------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = REPO_ROOT / "models"

MODEL_PATH = MODELS_DIR / "model.joblib"
LABELS_PATH = MODELS_DIR / "labels.json"
META_PATH = MODELS_DIR / "meta.json"

# -----------------------------------------------------------------------------
# Types (MUST be above load_artifacts)
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class ModelArtifacts:
    model: Any
    classes: np.ndarray


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def _normalize_proba(proba: Any) -> np.ndarray:
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

def _build_X_for_inference(*, text: str, summary: str, text_col: str, summary_col: str) -> pd.DataFrame:
    return pd.DataFrame([{text_col: (text or ""), summary_col: (summary or "")}])


# -----------------------------------------------------------------------------
# Loaders (single source of truth = models/meta.json)
# -----------------------------------------------------------------------------
@lru_cache(maxsize=1)
def load_training_meta() -> Dict[str, Any]:
    if not META_PATH.exists():
        raise FileNotFoundError(f"Missing meta file: {META_PATH}")
    with open(META_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)
    if not isinstance(meta, dict):
        raise ValueError("meta.json must contain an object/dict.")
    return meta


@lru_cache(maxsize=1)
def load_artifacts() -> ModelArtifacts:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Missing model file: {MODEL_PATH}")
    if not LABELS_PATH.exists():
        raise FileNotFoundError(f"Missing labels file: {LABELS_PATH}")

    model = joblib.load(MODEL_PATH)

    with open(LABELS_PATH, "r", encoding="utf-8") as f:
        classes = np.asarray(json.load(f), dtype=object)

    return ModelArtifacts(model=model, classes=classes)


# -----------------------------------------------------------------------------
# API
# -----------------------------------------------------------------------------
def predict_topk(
    *,
    text: str,
    summary: str = "",
    k: int = 3,
    text_col: str = "text_norm",
    summary_col: str = "summary_norm",
    parent_fn: Optional[Any] = None,
) -> Dict[str, Any]:
    arts = load_artifacts()
    train_meta = load_training_meta()

    X = _build_X_for_inference(
        text=text,
        summary=summary,
        text_col=text_col,
        summary_col=summary_col,
    )

    proba = _normalize_proba(arts.model.predict_proba(X))
    if proba.ndim != 2 or proba.shape[0] != 1:
        raise ValueError(f"Unexpected proba shape: {proba.shape}")

    p = proba[0]
    k = max(1, min(int(k), len(p)))
    top_idx = np.argsort(-p)[:k]

    top_labels = [str(arts.classes[i]) for i in top_idx]
    top_scores = [float(p[i]) for i in top_idx]

    meta = {
        "task": train_meta.get("task"),
        "model_name": train_meta.get("model_name"),
        "model_version": train_meta.get("model_version"),
        "trained_at": train_meta.get("generated_at"),
        "text_cols": train_meta.get("text_cols"),
        "note": train_meta.get("note"),
        "inferred_at": _utc_now_iso(),
        "inference": {
            "k": int(k),
            "text_col": text_col,
            "summary_col": summary_col,
            "has_summary": bool(summary),
        },
    }

    out: Dict[str, Any] = {"top_labels": top_labels, "top_scores": top_scores, "meta": meta}

    if parent_fn is not None:
        out["top_parents"] = [parent_fn(lab) for lab in top_labels]

    return out

def build_export_result(raw: dict, tale_id: str, text_ru: str, k: int = 3) -> dict:
    run = raw.get("run", {}) or {}
    suggestions = raw.get("suggestions", []) or []
    anchors_map = raw.get("anchors", {}) or {}

    # --- META: single source of truth for provenance & UI "Run metadata"
    meta = {
        # training-time (NOW FROM run)
        "task": run.get("task"),
        "text_cols": run.get("text_cols"),
        "model_name": run.get("model_name"),
        "model_version": run.get("model_version"),
        "trained_at": run.get("trained_at"),
        "note": run.get("note"),
        "model_sha": run.get("model_sha"),

        # inference-time / run-time
        "run_id": run.get("run_id"),
        "tale_id": run.get("tale_id") or tale_id,
        "created_at": run.get("created_at"),
        "status": run.get("status", "done"),
        "warnings": run.get("warnings", []) or [],
        "source_version": run.get("source_version"),

        # decision summary
        "tale_status": run.get("tale_status"),
        "primary_atu": run.get("primary_atu"),
        "co_types": run.get("co_types", []) or [],
        "delta_top12": run.get("delta_top12"),

        "typing_source": run.get("typing_source") or {"id": "ffc_284-286_2011_uther",

        "label": "FFC 284–286 (2011): Animal Tales, Tales of Magic, Religious Tales, Realistic Tales; etc.",

    "citation": (
        "Folklore Fellows’ Communications (FFC) 284–286. "
        "Sastamala: Vammalan Kirjapaino Oy, 2011. "
        "First published in 2004."
    ),

    "uri": "https://edition.fi/kalevalaseura/catalog/view/763/715/2750-1",

    "identifiers": {
        "issn": "0014-5815",
        "issn_l": "0014-5815",
        "ffc": ["284", "285", "286"],
        "isbn": [
            "978-951-41-1054-2",
            "978-951-41-1055-9",
            "978-951-41-1067-2",
        ],
    },

    "publisher": "Vammalan Kirjapaino Oy",
    "place": "Sastamala",
    "year": "2011",
    "note": "First published in 2004.",
}

    }

    # --- CANDIDATES: single source of truth for Top-3 + anchors
    candidates = []
    for rank, s in enumerate(suggestions[:k], start=1):
        if not isinstance(s, dict):
            continue
        atu = str(s.get("atu_code", "")).strip()
        score = s.get("score", None)

        # anchors for this candidate (if present)
        raw_anchors = []
        snippets = []
        if isinstance(anchors_map, dict) and atu:
            for a in anchors_map.get(atu, []) or []:
                if not isinstance(a, dict):
                    continue
                sn = a.get("snippet")
                if sn:
                    snippets.append(sn)

                raw_anchors.append(
                    {
                        "anchor_id": a.get("anchor_id"),
                        "score": a.get("score"),
                        "rationale": a.get("rationale"),
                        "snippet": a.get("snippet"),
                        "span": a.get("span"),  # expects {start_char, end_char}
                    }
                )

        candidates.append(
            {
                "rank": rank,
                "atu": atu,
                "score": float(score) if score is not None else None,

                # optional UX fields (if you want them in UI)
                "label": s.get("label"),
                "confidence_band": s.get("confidence_band"),
                "rationale_short": s.get("rationale_short"),

                "evidence": {
                    "snippets": snippets,
                    "anchors": raw_anchors,
                },
            }
        )

    export_result = {
        "id": tale_id,
        "meta": meta,
        "candidates": candidates,
    }
    return export_result
