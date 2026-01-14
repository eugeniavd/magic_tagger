# src/service.py
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List

from src.utils import atu_parent
from src.anchors import AnchorEngine, normalize_atu_code
from src.config import DEFAULT_TOP_K, DEFAULT_ANCHOR_K, clip01
from src.scoring import Candidate, make_decision
from src.model_store import predict_topk 

# Load once (fast for Streamlit reruns)
ANCHOR_ENGINE = AnchorEngine()

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


def _utc_now_iso_z() -> str:
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


def _label_for_code(code: str) -> str:
    # your ATU_LABELS keys are like "ATU-510A"
    key = f"ATU-{code}"
    return ATU_LABELS.get(key, "Unknown ATU type")


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
      - anchors (optional)
    """

    warnings: List[str] = []
    if not (text_ru or "").strip():
        warnings.append("NO_TEXT")
    elif len(text_ru.strip()) < 400:
        warnings.append("SHORT_TEXT")

    # 1) model_store inference (single source of truth)
    pred = predict_topk(
        text=text_ru,
        summary="",
        k=top_k,
        text_col="text_norm",
        summary_col="summary_norm",
        parent_fn=None,
    )

    top_labels = pred.get("top_labels", []) or []
    top_scores = pred.get("top_scores", []) or []
    meta = pred.get("meta", {}) or {}

    # normalize ATU codes
    codes = [normalize_atu_code(c) for c in top_labels]
    scores = [clip01(float(s)) for s in top_scores]

    # time + ids
    created_at = str(meta.get("inferred_at") or _utc_now_iso_z()).replace("+00:00", "Z")
    src_ver = _source_version(text_ru)
    run_id = _run_id(tale_id, src_ver, created_at)

    # model provenance (training meta from model_store)
    model_name = meta.get("model_name") or "MagicTagger ATU classifier"
    model_sha = meta.get("model_version") or "unknown"         # your training sha like a16b3a1
    trained_at = meta.get("trained_at") or meta.get("generated_at")
    task = meta.get("task")
    text_cols = meta.get("text_cols")
    note = meta.get("note")

    # human-readable model tag for UI/LOD (keeps your previous pattern)
    # IMPORTANT: keep it stable because it's used in JSON-LD IRI
    model_version_tag = f"{model_name}+anchors-v0.1.0"

    # 2) Anchors evidence
    anchor_results = ANCHOR_ENGINE.score_types(text_ru, codes) if with_anchors else {}

    # 3) Decision logic candidates
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
                "label": _label_for_code(cand.atu_code),
                "score": float(cand.score),
                "atu_parent": atu_parent(cand.atu_code),
                "confidence_band": _confidence_band(float(cand.score)),
                "rationale_short": "Model SCORE with rule-based motif anchors as evidence.",
                "anchors_summary": {
                    "count": int(min(hit_count, anchor_k)),
                    "top_pages": [],
                },
            }
        )

    payload: Dict[str, Any] = {
        "run": {
            # run identity
            "run_id": run_id,
            "tale_id": tale_id,
            "created_at": created_at,
            "status": "done",
            "warnings": warnings,
            "source_version": src_ver,

            # decision summary
            "tale_status": decision.tale_status.value,
            "primary_atu": decision.primary_atu,
            "co_types": list(decision.co_types),
            "delta_top12": float(decision.delta_top12),

            # training provenance (NOW from model_store, not UI file)
            "task": task,
            "text_cols": text_cols,
            "note": note,
            "trained_at": trained_at,
            "model_name": model_name,
            "model_sha": model_sha,
            "model_version": model_version_tag,
        },
        "suggestions": suggestions,
    }

    # 5) Anchors payload
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
                        "score": float(clip01(ar.anchor_score)),
                        "snippet": h.snippet,
                        "rationale": f"Matched pattern '{h.pattern}' (w={h.w:.2f}).",
                        "source": {
                            "method": "rule_based_motifs",
                            "model_version": model_version_tag,
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
