# src/service.py
from __future__ import annotations
import numpy as np
import pandas as pd


import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple


from src.utils import atu_parent
from src.anchors import AnchorEngine, normalize_atu_code
from src.config import DEFAULT_TOP_K, DEFAULT_ANCHOR_K, clip01
from src.scoring import Candidate, make_decision
from src.model_store import predict_topk as _predict_topk, load_artifacts


# Load once (fast for Streamlit reruns)
ANCHOR_ENGINE = AnchorEngine()

def _model_version() -> str:
    try:
        arts = load_artifacts()
        name = arts.meta.get("model_name", "baseline")
        return f"{name}+anchors-v0.1.0"
    except Exception:
        return "baseline-unknown+anchors-v0.1.0"

MODEL_VERSION = _model_version()

ATU_LABELS: Dict[str, str] = {
    "ATU-510A": "Cinderella",
    "ATU-300": "The Dragon-Slayer",
    "ATU-327A": "The Children and the Ogre",
    "ATU-400": "The Quest for the Lost Husband",
    "ATU-425A": "The Animal as Bridegroom",
    "ATU-480": "The Kind and the Unkind Girls",
    "ATU-550": "The Quest for the Golden Bird",
    "ATU-555": "The Fisherman and His Wife",
    "ATU-650A": "Strong John",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _source_version(text: str) -> str:
    normalized = re.sub(r"\s+", " ", (text or "").strip())
    return f"sha256:{_sha256_hex(normalized)}"


def _run_id(tale_id: str, source_ver: str, created_at: str) -> str:
    seed = f"{tale_id}|{source_ver}|{created_at}"
    short = _sha256_hex(seed)[:6]
    return f"cls_{created_at}_{short}"


def _confidence_band(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.50:
        return "medium"
    return "low"


# -----------------------------
# Real model inference (Top-K)
# -----------------------------
def model_predict_topk(
    text_ru: str,
    top_k: int = 3,
    *,
    summary_ru: str = "",
) -> List[Tuple[str, float]]:
    """
    Uses saved sklearn Pipeline from models/model.joblib.
    Returns list of (atu_code, score) with score in [0, 1].
    """
    arts = load_artifacts()  # cached via lru_cache(maxsize=1) inside model_store.py
    model = arts.model
    classes = arts.classes  # order must match predict_proba columns

    # ColumnTransformer in your pipeline expects specific column names.
    # In training you used ("summary_norm", "text_norm").
    X = pd.DataFrame([{
        "text_norm": (text_ru or ""),
        "summary_norm": (summary_ru or ""),
    }])

    proba = model.predict_proba(X)

    # Defensive: OvR may return list-of-arrays; normalize to 2D
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
        proba = np.column_stack(cols)
    else:
        proba = np.asarray(proba)

    p = proba[0]  # (n_classes,)
    top_idx = np.argsort(-p)[:top_k]

    out: List[Tuple[str, float]] = []
    for i in top_idx:
        out.append((str(classes[i]), float(p[i])))

    return out


# -----------------------------
# Main service API
# -----------------------------
def classify(
    *,
    tale_id: str,
    text_ru: str,
    top_k: int = DEFAULT_TOP_K,
    with_anchors: bool = True,
    anchor_k: int = DEFAULT_ANCHOR_K,
) -> Dict[str, Any]:
    """
    Contract-shaped response:
      - run
      - suggestions (Top-K)
      - anchors (evidence hits with spans/snippets), optional
    """

    created_at = _utc_now_iso()
    src_ver = _source_version(text_ru)
    run_id = _run_id(tale_id, src_ver, created_at)

    warnings: List[str] = []
    if not (text_ru or "").strip():
        warnings.append("NO_TEXT")
    elif len(text_ru.strip()) < 400:
        warnings.append("SHORT_TEXT")

    # 1) Model predictions (Top-K)
    preds = model_predict_topk(text_ru, top_k=top_k)
    codes = [normalize_atu_code(c) for c, _ in preds]
    scores = [clip01(float(s)) for _, s in preds]

    # 2) Rule-based anchors for these codes (evidence layer)
    anchor_results = ANCHOR_ENGINE.score_types(text_ru, codes) if with_anchors else {}

    # 3) Build candidates for decision logic (SCORE from model, ANCHOR from anchors)
    candidates: List[Candidate] = []
    for code, score in zip(codes, scores):
        ar = anchor_results.get(normalize_atu_code(code))
        anchor_score = float(ar.anchor_score) if ar else 0.0
        candidates.append(Candidate(atu_code=normalize_atu_code(code), score=score, anchor=clip01(anchor_score)))

    decision = make_decision(candidates)

    # 4) Suggestions payload
    suggestions: List[Dict[str, Any]] = []
    for i, cand in enumerate(decision.candidates[:top_k], start=1):
        ar = anchor_results.get(cand.atu_code)
        hit_count = len(ar.hits) if (with_anchors and ar) else 0

        suggestions.append(
            {
                "rank": i,
                "atu_code": cand.atu_code,
                "label": ATU_LABELS.get(cand.atu_code, "Unknown ATU type"),
                "score": float(cand.score),
                "atu_parent": atu_parent(cand.atu_code),
                "confidence_band": _confidence_band(cand.score),
                "rationale_short": "Model SCORE with rule-based motif anchors as evidence.",
                "anchors_summary": {
                    "count": int(min(hit_count, anchor_k)),
                    "top_pages": [],  # you store fulltext, no pagination
                },
            }
        )

    payload: Dict[str, Any] = {
        "run": {
            "run_id": run_id,
            "tale_id": tale_id,
            "model_version": MODEL_VERSION,
            "source_version": src_ver,
            "created_at": created_at,
            "status": "done",
            "warnings": warnings,
            "tale_status": decision.tale_status.value,
            "primary_atu": decision.primary_atu,
            "co_types": list(decision.co_types),
            "delta_top12": float(decision.delta_top12),
        },
        "suggestions": suggestions,
    }

    # 5) Anchors payload (hits with spans/snippets)
    if with_anchors:
        anchors_out: Dict[str, List[Dict[str, Any]]] = {}

        for cand in decision.candidates[:top_k]:
            ar = anchor_results.get(cand.atu_code)
            if not ar:
                anchors_out[cand.atu_code] = []
                continue

            hits = []
            for j, h in enumerate(ar.hits[:anchor_k]):
                hits.append(
                    {
                        "anchor_id": f"{cand.atu_code}_anc_{j+1}",
                        "rank": j + 1,
                        "score": float(clip01(ar.anchor_score)),  # per-type evidence strength
                        "snippet": h.snippet,
                        "rationale": f"Matched pattern '{h.pattern}' (w={h.w:.2f}).",
                        "source": {
                            "method": "rule_based_motifs",
                            "model_version": MODEL_VERSION,
                        },
                        "span": {
                            "text_unit": "plain",
                            "start_char": int(h.start_char),
                            "end_char": int(h.end_char),
                        },
                    }
                )

            anchors_out[cand.atu_code] = hits

        payload["anchors"] = anchors_out

    return payload


if __name__ == "__main__":
    import json

    demo = classify(tale_id="external_001", text_ru="Это пример текста сказки. " * 60)
    print(json.dumps(demo, ensure_ascii=False, indent=2))
