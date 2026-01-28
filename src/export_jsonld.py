# src/export_jsonld.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional, List
from urllib.parse import quote


BASE_URI = "https://raw.githubusercontent.com/eugeniavd/magic_tagger/main/rdf/ontology.ttl"
RFT_ONT = BASE_URI + "#"
BASE_DATA = "https://github.com/eugeniavd/magic_tagger/rdf"

# -----------------------------
# External stable references
# -----------------------------
LABELS_URI = "https://github.com/eugeniavd/magic_tagger/blob/main/models/labels.json"
POLICY_URI = "https://github.com/eugeniavd/magic_tagger/blob/main/models/meta.json"

# Dataset publication pointer (immutable permalink; can later be a release asset)
DATASET_URI = "https://github.com/eugeniavd/magic_tagger/commit/1ebea31920a6adc352979b2518e072aa2d1a0332"

# -----------------------------
# OntoDM (for PredictiveModel typing)
# -----------------------------
ONTODM_NS = "http://kt.ijs.si/panovp/OntoDM#"

# ---------------------------------------------------------------------
# JSON-LD context (recommended style: local keys map to IRIs)
# ---------------------------------------------------------------------
CONTEXT: Dict[str, Any] = {
    "ontoDM": ONTODM_NS,
    "dcterms": "http://purl.org/dc/terms/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "crm": "http://www.cidoc-crm.org/cidoc-crm/",
    "prov": "http://www.w3.org/ns/prov#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "probabilisticPredictiveModel": {"@id": "ontoDM:OntoDM_000073", "@type": "@id"},
    

    # common JSON-LD aliases
    "id": "@id",
    "type": "@type",

    # typed literals
    "confidenceScore": {"@id": "rft:confidenceScore", "@type": "xsd:decimal"},
    "rank": {"@id": "rft:rank", "@type": "xsd:integer"},
    "deltaTop12": {"@id": "rft:deltaTop12", "@type": "xsd:decimal"},
    "confidenceBand": {"@id": "rft:confidenceBand", "@type": "xsd:string"},
    "decisionPolicyId": {"@id": "rft:decisionPolicyId", "@type": "xsd:string"},
    "trainedAt": {"@id": "rft:trainedAt", "@type": "xsd:dateTime"},
    "modelSha": {"@id": "rft:modelSha", "@type": "xsd:string"},
    "sourceVersion": {"@id": "rft:sourceVersion", "@type": "xsd:string"},
    "task": {"@id": "rft:task", "@type": "xsd:string"},
    "taleStatus": {"@id": "rft:taleStatus", "@type": "xsd:string"},
    "finalDecisionSource": {"@id": "rft:finalDecisionSource", "@type": "xsd:string"},
    "finalExpertNote": {"@id": "rft:finalExpertNote", "@type": "xsd:string"},
    "finalSavedAt": {"@id": "rft:finalSavedAt", "@type": "xsd:dateTime"},
    "sha256": {"@id": "rft:sha256", "@type": "xsd:string"},

    # IRIs (@id)
    "decisionPolicy": {"@id": "rft:decisionPolicy", "@type": "@id"},
    "labels": {"@id": "rft:labels", "@type": "@id"},

    "forTale": {"@id": "rft:forTale", "@type": "@id"},
    "hasCandidate": {"@id": "rft:hasCandidate", "@type": "@id"},
    "predictedTaleType": {"@id": "rft:predictedTaleType", "@type": "@id"},
    "primaryATU": {"@id": "rft:primaryATU", "@type": "@id"},
    "modelPrimaryATU": {"@id": "rft:modelPrimaryATU", "@type": "@id"},
    "finalATU": {"@id": "rft:finalATU", "@type": "@id"},
    "usedModel": {"@id": "rft:usedModel", "@type": "@id"},

    # PROV
    "startedAtTime": {"@id": "prov:startedAtTime", "@type": "xsd:dateTime"},
    "endedAtTime": {"@id": "prov:endedAtTime", "@type": "xsd:dateTime"},
    "used": {"@id": "prov:used", "@type": "@id"},
    "generated": {"@id": "prov:generated", "@type": "@id"},
    "wasGeneratedBy": {"@id": "prov:wasGeneratedBy", "@type": "@id"},
    "wasDerivedFrom": {"@id": "prov:wasDerivedFrom", "@type": "@id"},
    "wasAttributedTo": {"@id": "prov:wasAttributedTo", "@type": "@id"},

    # Dublin Core / RDFS
    "created": {"@id": "dcterms:created", "@type": "xsd:dateTime"},
    "source": {"@id": "dcterms:source", "@type": "@id"},
    "bibliographicCitation": {"@id": "dcterms:bibliographicCitation", "@type": "xsd:string"},
    "identifier": {"@id": "dcterms:identifier", "@type": "xsd:string"},
    "description": {"@id": "dcterms:description", "@type": "xsd:string"},
    "label": {"@id": "rdfs:label", "@type": "xsd:string"},
    "seeAlso": {"@id": "rdfs:seeAlso", "@type": "@id"},

    # NEW: dataset publication pointer (typed as @id)
    # we map it to rdfs:seeAlso to keep it lightweight and avoid inventing new rft terms
    "datasetUri": {"@id": "rdfs:seeAlso", "@type": "@id"},
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _iri_safe(s: str) -> str:
    return quote(str(s), safe=":/#?&=@[]!$&'()*+,;-%._~")


def _as_z(dt: Any) -> str:
    s = str(dt or "").strip()
    if not s:
        return ""
    return s.replace("+00:00", "Z")


def _ts_slug(iso_ts: str) -> str:
    s = str(iso_ts).strip()
    s = s.replace("+00:00", "Z").replace(":", "-")
    return _iri_safe(s)


def _rdf_iri(*parts: str) -> str:
    path = "/".join(p.strip("/") for p in parts if p is not None and str(p).strip() != "")
    return f"{BASE_DATA}/{path}"


def _atu_norm(code: str) -> str:
    return str(code).strip().rstrip("*")


def _band_title(band: Any) -> str:
    b = str(band or "").strip().lower()
    return "High" if b == "high" else "low"


def to_jsonld(result: Dict[str, Any], tale_id: Optional[str] = None) -> Dict[str, Any]:
    """
    LOD-ready JSON-LD export (lite PROV + rft), with reproducibility pointers.

    Key behaviors:
    - Prefer meta URIs: run_uri/model_uri/input_text_uri/result_uri if present, else mint from BASE_DATA.
    - InputTextSnapshot carries sha256 (meta["text_sha256"]); source_version stays dataset snapshot version.
    - decisionPolicy and labels are IRIs (@id) to meta.json and labels.json.
    - Model typed as ontoDM predictive model (plus your rft classes).
    - DatasetSnapshot optionally points to a published dataset URI (commit permalink / release asset / DOI).
    """
    rid = str(result.get("id") or "").strip()
    tid = str(tale_id or rid or "unknown").strip()

    meta = result.get("meta") or {}
    k = int(meta.get("k") or 3)

    # --- times
    created_at = _as_z(
        meta.get("created_at")
        or meta.get("inferred_at")
        or meta.get("generated_at")
        or _utc_now_iso()
    )
    ts = _ts_slug(created_at)
    trained_at = _as_z(meta.get("trained_at") or meta.get("generated_at") or "")

    # --- identifiers
    run_id = str(meta.get("run_id") or "").strip() or None

    model_version_tag = str(meta.get("model_version") or "unknown").strip()
    model_name = str(meta.get("model_name") or "MagicTagger ATU classifier").strip()
    model_sha = str(meta.get("model_sha") or "").strip()
    model_key = model_sha or model_version_tag

    # --- dataset snapshot (keep source_version as corpus snapshot version)
    source_version = str(meta.get("source_version") or "").strip() or None

    # --- reproducibility pointers
    policy_id = str(meta.get("decision_policy") or "high_else").strip()
    policy_uri = str(meta.get("decision_policy_uri") or POLICY_URI).strip()
    labels_uri = str(meta.get("labels_uri") or LABELS_URI).strip()
    dataset_uri = str(meta.get("dataset_uri") or DATASET_URI).strip()

    # --- decision values
    conf_band = _band_title(meta.get("confidence_band"))
    tale_status = meta.get("tale_status")
    delta_top12 = meta.get("delta_top12")
    primary_atu = meta.get("primary_atu")

    model_primary_atu = meta.get("model_primary_atu")
    final_decision_source = str(meta.get("final_decision_source") or "").strip() or None
    final_atu = meta.get("final_atu")
    final_expert_note = meta.get("final_expert_note")
    final_saved_at = _as_z(meta.get("final_saved_at") or "")

    task = meta.get("task")
    text_cols = meta.get("text_cols")
    note = meta.get("note")

    # --- integrity
    text_sha256 = str(meta.get("text_sha256") or "").strip() or None

    # ------------------------------------------------------------------
    # IRIs: prefer meta-provided URIs
    # ------------------------------------------------------------------
    tale_iri = _rdf_iri("tale", _iri_safe(tid))

    run_iri = str(meta.get("run_uri") or "").strip() or _rdf_iri("run", _iri_safe(run_id or f"{tid}_{ts}"))
    model_iri = str(meta.get("model_uri") or "").strip() or _rdf_iri("model", _iri_safe(model_key))
    input_iri = str(meta.get("input_text_uri") or "").strip() or _rdf_iri("text", _iri_safe(tid))
    result_iri = str(meta.get("result_uri") or "").strip() or _rdf_iri("result", _iri_safe(tid), ts)

    # snapshot nodes
    input_snapshot_iri = _rdf_iri("text", _iri_safe(tid), "snapshot", ts)
    dataset_snapshot_iri = _rdf_iri("datasetSnapshot", _iri_safe(source_version)) if source_version else None

    # --- typing source (bibliographic resource)
    typing_source = meta.get("typing_source") or {}
    biblio_node: Optional[Dict[str, Any]] = None
    biblio_iri: Optional[str] = None

    if isinstance(typing_source, str) and typing_source.strip():
        biblio_iri = typing_source.strip()
        biblio_node = {"id": biblio_iri, "type": ["dcterms:BibliographicResource", "prov:Entity"], "label": "Typing source"}

    elif isinstance(typing_source, dict) and (typing_source.get("uri") or typing_source.get("citation") or typing_source.get("id")):
        src_id = str(typing_source.get("id") or "typing_source").strip()
        biblio_iri = _rdf_iri("biblio", _iri_safe(src_id))
        biblio_node = {
            "id": biblio_iri,
            "type": ["dcterms:BibliographicResource", "prov:Entity"],
            "label": typing_source.get("label") or src_id,
            "bibliographicCitation": typing_source.get("citation"),
            "seeAlso": {"id": typing_source.get("uri")} if typing_source.get("uri") else None,
        }

    # ------------------------------------------------------------------
    # Candidates (mint as nodes, reference from result)
    # ------------------------------------------------------------------
    candidates = result.get("candidates") or []
    cand_nodes: List[Dict[str, Any]] = []
    cand_ids: List[str] = []

    for rank, c in enumerate(candidates[:k], start=1):
        atu_raw = str(c.get("atu", "")).strip()
        atu_norm = _atu_norm(atu_raw)
        score = c.get("score", None)

        cand_id = _rdf_iri("candidate", _iri_safe(tid), ts, str(rank))
        cand_ids.append(cand_id)

        cand_nodes.append(
            {
                "id": cand_id,
                "type": "rft:ClassificationCandidate",
                "rank": rank,
                "predictedTaleType": {"id": _rdf_iri("taleType", "atu", atu_norm)},
                "skos:notation": atu_raw,
                "confidenceScore": float(score) if score is not None else None,
                "confidenceBand": _band_title(c.get("confidence_band")),
            }
        )

    # ------------------------------------------------------------------
    # prov:used (model + input snapshot + dataset snapshot + biblio + policy + labels)
    # ------------------------------------------------------------------
    used_list: List[Dict[str, Any]] = [{"id": model_iri}, {"id": input_snapshot_iri}]
    if dataset_snapshot_iri:
        used_list.append({"id": dataset_snapshot_iri})
    if biblio_iri:
        used_list.append({"id": biblio_iri})
    if policy_uri:
        used_list.append({"id": policy_uri})
    if labels_uri:
        used_list.append({"id": labels_uri})

    # ------------------------------------------------------------------
    # Nodes
    # ------------------------------------------------------------------
    result_node: Dict[str, Any] = {
        "id": result_iri,
        "type": ["rft:ClassificationResult", "prov:Entity"],
        "identifier": tid,
        "forTale": {"id": tale_iri},
        "wasGeneratedBy": {"id": run_iri},
        "hasCandidate": [{"id": x} for x in cand_ids],
        "taleStatus": tale_status,
        "deltaTop12": float(delta_top12) if delta_top12 is not None else None,

        "confidenceBand": conf_band,
        "decisionPolicyId": policy_id,
        "decisionPolicy": policy_uri,
        "labels": labels_uri,

        "primaryATU": {"id": _rdf_iri("taleType", "atu", _atu_norm(str(primary_atu)))} if primary_atu else None,
        "modelPrimaryATU": {"id": _rdf_iri("taleType", "atu", _atu_norm(str(model_primary_atu)))} if model_primary_atu else None,
        "finalATU": {"id": _rdf_iri("taleType", "atu", _atu_norm(str(final_atu)))} if final_atu else None,
        "finalDecisionSource": final_decision_source,
        "finalExpertNote": final_expert_note,
        "finalSavedAt": final_saved_at or None,
    }

    run_node: Dict[str, Any] = {
        "id": run_iri,
        "type": ["prov:Activity", "rft:ClassificationRun"],
        "identifier": run_id,
        "startedAtTime": created_at,
        "forTale": {"id": tale_iri},
        "sourceVersion": source_version,
        "used": used_list,
        "generated": [{"id": result_iri}],
        "usedModel": {"id": model_iri},
        "label": f"ATU classification run for {tid}",
    }

    model_node: Dict[str, Any] = {
        "id": model_iri,
        "type": [
            "prov:Entity",
            "rft:Model",
            "ontoDM:probabilistic_predictive_model",
        ],
        "identifier": model_key,
        "label": model_name,
        "modelSha": model_sha or None,
        "rft:modelTag": model_version_tag,
        "trainedAt": trained_at or None,
        "datasetUri": dataset_uri, 
        "task": task,
        "rft:textCols": text_cols,
        "description": note,
        "source": {"id": biblio_iri} if biblio_iri else None,
    }

    input_node: Dict[str, Any] = {
        "id": input_iri,
        "type": ["prov:Entity", "rft:InputText"],
        "identifier": tid,
        "label": f"Input text ({tid})",
    }

    input_snapshot_node: Dict[str, Any] = {
        "id": input_snapshot_iri,
        "type": ["prov:Entity", "rft:InputTextSnapshot"],
        "identifier": f"{tid}@{ts}",
        "label": f"Input text snapshot for {tid} at {created_at}",
        "wasDerivedFrom": {"id": input_iri},
        "sha256": text_sha256,
    }

    tale_node: Dict[str, Any] = {
        "id": tale_iri,
        "type": "rft:Tale",
        "identifier": tid,
    }

    dataset_snapshot_node: Optional[Dict[str, Any]] = None
    if dataset_snapshot_iri:
        dataset_snapshot_node = {
            "id": dataset_snapshot_iri,
            "type": ["prov:Entity", "rft:DatasetSnapshot"],
            "identifier": source_version,
            "label": "Corpus snapshot (dataset version used for inference)",
            "datasetUri": dataset_uri,  # maps to rdfs:seeAlso (typed as @id)
        }

    # HITL as separate Activity if override
    hitl_node: Optional[Dict[str, Any]] = None
    expert_agent_node: Optional[Dict[str, Any]] = None
    if final_decision_source and final_decision_source != "model":
        hitl_iri = _rdf_iri("run", _iri_safe(run_id or f"{tid}_{ts}"), "hitl")
        expert_agent_id = str(meta.get("expert_agent_id") or "").strip() or None
        expert_agent_iri = _rdf_iri("agent", _iri_safe(expert_agent_id)) if expert_agent_id else None

        hitl_node = {
            "id": hitl_iri,
            "type": ["prov:Activity", "rft:HumanReview"],
            "label": f"HITL review for {tid}",
            "startedAtTime": final_saved_at or created_at,
            "used": [{"id": result_iri}],
        }
        if expert_agent_iri:
            hitl_node["wasAttributedTo"] = {"id": expert_agent_iri}
            expert_agent_node = {
                "id": expert_agent_iri,
                "type": ["prov:Agent"],
                "identifier": expert_agent_id,
                "label": "Expert annotator",
            }

    graph: List[Dict[str, Any]] = [
        result_node,
        run_node,
        model_node,
        input_node,
        input_snapshot_node,
        tale_node,
        *cand_nodes,
    ]
    if dataset_snapshot_node:
        graph.append(dataset_snapshot_node)
    if biblio_node:
        graph.append(biblio_node)
    if hitl_node:
        graph.append(hitl_node)
    if expert_agent_node:
        graph.append(expert_agent_node)

    jsonld: Dict[str, Any] = {"@context": CONTEXT, "@graph": graph}

    # ------------------------------------------------------------------
    # Drop None recursively
    # ------------------------------------------------------------------
    def _drop_none(x: Any) -> Any:
        if isinstance(x, dict):
            return {k: _drop_none(v) for k, v in x.items() if v is not None}
        if isinstance(x, list):
            return [_drop_none(v) for v in x if v is not None]
        return x

    return _drop_none(jsonld)
