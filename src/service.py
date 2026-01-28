from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from src.utils import atu_parent
from src.config import DEFAULT_TOP_K, clip01
from src.scoring import Candidate, make_decision
from src.model_store import predict_topk, load_training_meta


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

# Robust pattern: optional "ATU", optional dash, digits, optional letter suffix, optional trailing "*"
_ATU_RE = re.compile(r"(?i)\b(?:ATU)?\s*[-–—]?\s*(\d{1,4})\s*([A-Z]{0,3})\s*(\*?)\b")


def normalize_atu_code_any(x: Any) -> str:
    """
    Robust ATU code normalizer supporting:
      - letters: 480a -> 480A
      - star: 480A* -> 480A*
      - prefixes: ATU-480A*, atu 480a*, ATU480A*, etc.
    If no ATU-like pattern is found, returns a conservative cleaned string (digits/letters/*).
    """
    s = str(x or "").strip()
    if not s:
        return ""

    s2 = s.replace("–", "-").replace("—", "-")
    s2 = re.sub(r"\s+", " ", s2)

    m = _ATU_RE.search(s2)
    if m:
        num = m.group(1)
        suf = (m.group(2) or "").upper()
        star = "*" if (m.group(3) or "") else ""
        return f"{num}{suf}{star}"

    # fallback: strip obvious prefixes and keep only [0-9A-Za-z*]
    s3 = re.sub(r"(?i)\bATU\b", "", s2)
    s3 = s3.replace("-", "").replace(" ", "")
    s3 = re.sub(r"[^0-9A-Za-z\*]", "", s3).upper()
    return s3


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


def _label_for_code(code: str) -> str:
    # Labels are stored without the trailing "*", so lookup uses the base form.
    base = re.sub(r"\*$", "", (code or "").strip())
    key = f"ATU-{base}"
    return ATU_LABELS.get(key, "Unknown ATU type")


def _load_policy_from_meta(meta: Dict[str, Any]) -> Dict[str, Any]:
    dp = meta.get("decision_policy") or {}
    return dp if isinstance(dp, dict) else {}


def _high_else_band(score1: float, score2: float, policy: Dict[str, Any]) -> Tuple[str, float]:
    """
    Returns: (band, delta) with band in {"high","low"}.
    """
    delta = float(score1) - float(score2)
    high_rule = policy.get("high_rule") or {}
    min_s = float(high_rule.get("min_score1", 1.0))
    min_d = float(high_rule.get("min_delta", 1.0))
    band = "high" if (score1 >= min_s and delta >= min_d) else "low"
    return band, delta


def classify(
    *,
    tale_id: str,
    text_ru: str,
    top_k: int = DEFAULT_TOP_K,
) -> Dict[str, Any]:
    """
    Contract-shaped response:
      - run
      - suggestions (Top-K)
    Notes:
      - Model metadata and decision policy are loaded from models/meta.json (via load_training_meta()).
      - ATU codes are normalized to support letter suffixes and trailing '*' (e.g., 480A, 480A*).
    """
    # --- single source of truth: models/meta.json
    meta_file = load_training_meta()
    policy = _load_policy_from_meta(meta_file)

    warnings: List[str] = []
    if not (text_ru or "").strip():
        warnings.append("NO_TEXT")
    elif len(text_ru.strip()) < 400:
        warnings.append("SHORT_TEXT")

    # 1) inference (labels + scores)
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

    # normalize ATU codes robustly (supports letters and trailing '*')
    codes = [normalize_atu_code_any(c) for c in top_labels]
    scores = [clip01(float(s)) for s in top_scores]

    # robust top1/top2 for policy
    score1 = float(scores[0]) if len(scores) > 0 else 0.0
    score2 = float(scores[1]) if len(scores) > 1 else 0.0
    band, delta = _high_else_band(score1=score1, score2=score2, policy=policy)
    tale_status = "accept" if band == "high" else "review"

    # time + ids
    created_at = _utc_now_iso_z()
    src_ver = _source_version(text_ru)
    run_id = _run_id(tale_id, src_ver, created_at)

    # --- model provenance: strictly from meta.json
    model_name = meta_file.get("model_name") or "MagicTagger ATU classifier"
    model_sha = meta_file.get("model_sha") or meta_file.get("model_version") or "unknown"
    trained_at = meta_file.get("trained_at") or meta_file.get("generated_at")
    task = meta_file.get("task")
    text_cols = meta_file.get("text_cols")
    note = meta_file.get("note")
    model_version_tag = meta_file.get("model_version_tag") or f"{model_name}-v0.1.0"

    # 2) Build candidates (no anchors)
    candidates: List[Candidate] = [
        Candidate(atu_code=code, score=float(score), anchor=0.0)
        for code, score in zip(codes, scores)
    ]
    decision = make_decision(candidates)

    # 3) Suggestions payload
    suggestions: List[Dict[str, Any]] = []
    for i, cand in enumerate(decision.candidates[:top_k], start=1):
        # parent computation should ignore trailing '*' (classification variant marker)
        base_for_parent = re.sub(r"\*$", "", cand.atu_code)

        suggestions.append(
            {
                "rank": i,
                "atu_code": cand.atu_code,  # keeps letters and '*' if present
                "label": _label_for_code(cand.atu_code),
                "score": float(cand.score),
                "atu_parent": atu_parent(base_for_parent),

                # policy band is meaningful primarily for the top-1 decision
                "confidence_band": band if i == 1 else "low",
            }
        )

    payload: Dict[str, Any] = {
        "run": {
            "run_id": run_id,
            "tale_id": tale_id,
            "created_at": created_at,
            "status": "done",
            "warnings": warnings,
            "source_version": src_ver,

            # decision summary
            "tale_status": tale_status,
            "primary_atu": decision.primary_atu,
            "co_types": list(decision.co_types),

            # policy signals
            "score1": score1,
            "score2": score2,
            "delta_top12": float(delta),
            "confidence_band": band,
            "decision_policy": policy.get("type", "high_else"),

            # training provenance (FROM meta.json)
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

    return payload
