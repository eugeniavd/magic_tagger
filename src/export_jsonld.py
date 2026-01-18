
# src/export_jsonld.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional, List
from urllib.parse import quote

BASE_RDF = "https://github.com/eugeniavd/magic_tagger/rdf"
RFT_ONT = "https://github.com/eugeniavd/magic_tagger/rdf/ontology/#"

CONTEXT: Dict[str, Any] = {
    "rft": RFT_ONT,
    "dcterms": "http://purl.org/dc/terms/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "crm": "http://www.cidoc-crm.org/cidoc-crm/",
    "prov": "http://www.w3.org/ns/prov#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",

    # typed fields
    "rft:confidenceScore": {"@type": "xsd:decimal"},
    "rft:rank": {"@type": "xsd:integer"},
    "prov:generatedAtTime": {"@type": "xsd:dateTime"},
    "dcterms:created": {"@type": "xsd:dateTime"},
    "dcterms:source": {"@type": "@id"},
    "dcterms:bibliographicCitation": {"@type": "xsd:string"},
    "rdfs:seeAlso": {"@type": "@id"},

    # provenance / run fields (UI meta -> JSON-LD)
    "rft:trainedAt": {"@type": "xsd:dateTime"},
    "rft:modelSha": {"@type": "xsd:string"},
    "rft:sourceVersion": {"@type": "xsd:string"},
    "rft:task": {"@type": "xsd:string"},
    "rft:deltaTop12": {"@type": "xsd:decimal"},
    "rft:taleStatus": {"@type": "xsd:string"},

    # human-in-the-loop (model vs expert)
    "rft:finalDecisionSource": {"@type": "xsd:string"},
    "rft:finalExpertNote": {"@type": "xsd:string"},
    "rft:finalSavedAt": {"@type": "xsd:dateTime"},

    # IRIs to ATU types
    "rft:modelPrimaryATU": {"@type": "@id"},
    "rft:finalATU": {"@type": "@id"},
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _iri_safe(s: str) -> str:
    return quote(str(s), safe=":/#?&=@[]!$&'()*+,;-%._~")


def _ts_slug(iso_ts: str) -> str:
    s = str(iso_ts).strip()
    s = s.replace("+00:00", "Z")
    s = s.replace(":", "-")
    return _iri_safe(s)


def _rdf_iri(*parts: str) -> str:
    path = "/".join(p.strip("/") for p in parts if p is not None and str(p).strip() != "")
    return f"{BASE_RDF}/{path}"


def _atu_norm(code: str) -> str:
    return str(code).strip().rstrip("*")


def _as_z(dt: str) -> str:
    s = str(dt).strip()
    if not s:
        return s
    return s.replace("+00:00", "Z")


def to_jsonld(result: Dict[str, Any], tale_id: Optional[str] = None) -> Dict[str, Any]:
    """
    LOD-ready JSON-LD export.
    Expects canonical export_result shape:

      {
        "id": "...",
        "meta": { ... },          # single source of truth (UI meta)
        "candidates": [
          {
            "rank": 1,
            "atu": "709",
            "score": 0.52,
            "evidence": {
              "snippets": [...],
              "anchors": [
                {"anchor_id": "...", "score": 0.3, "rationale": "...", "snippet": "...",
                 "span": {"start_char": 10, "end_char": 40}}
              ]
            }
          }
        ]
      }

    Optional meta.typing_source:
      - string URL/IRI
      - or dict: {"id": "...", "label": "...", "citation": "...", "uri": "..."}
    """
    rid = str(result.get("id") or "").strip()
    tid = str(tale_id or rid or "unknown").strip()

    meta = result.get("meta") or {}
    k = int(meta.get("k") or 3)

    # --- model fields (UI meta)
    model_version_tag = str(meta.get("model_version") or "unknown").strip()  # e.g. "...+anchors-v0.1.0"
    model_name = str(meta.get("model_name") or "MagicTagger ATU classifier").strip()
    model_sha = str(meta.get("model_sha") or "").strip()  # training sha (e.g., a16b3a1)

    # Prefer sha-based model IRI (stable). Fallback to model_version_tag if sha missing.
    model_key = model_sha or model_version_tag

    # --- typing source (bibliographic resource)
    typing_source = meta.get("typing_source") or {}
    biblio_node: Optional[Dict[str, Any]] = None
    biblio_iri: Optional[str] = None

    if isinstance(typing_source, str) and typing_source.strip():
        # If stored as a plain URI/IRI string
        biblio_iri = typing_source.strip()
        biblio_node = {
            "@id": biblio_iri,
            "@type": ["dcterms:BibliographicResource", "prov:Entity"],
            "rdfs:label": "Typing source",
        }

    elif isinstance(typing_source, dict) and (
        typing_source.get("uri") or typing_source.get("citation") or typing_source.get("id")
    ):
        src_id = str(typing_source.get("id") or "typing_source").strip()
        biblio_iri = _rdf_iri("biblio", _iri_safe(src_id))

        label = typing_source.get("label") or src_id
        citation = typing_source.get("citation")
        uri = typing_source.get("uri")

        biblio_node = {
            "@id": biblio_iri,
            "@type": ["dcterms:BibliographicResource", "prov:Entity"],
            "rdfs:label": label,
            "dcterms:bibliographicCitation": citation,
            "rdfs:seeAlso": {"@id": uri} if uri else None,
        }

    # --- time: prefer created_at from UI meta
    created_at = _as_z(
        meta.get("created_at")
        or meta.get("inferred_at")
        or meta.get("generated_at")
        or _utc_now_iso()
    )
    ts = _ts_slug(created_at)

    trained_at = _as_z(meta.get("trained_at") or meta.get("generated_at") or "")
    run_id = meta.get("run_id")
    source_version = meta.get("source_version")
    task = meta.get("task")
    text_cols = meta.get("text_cols")
    note = meta.get("note")
    tale_status = meta.get("tale_status")
    delta_top12 = meta.get("delta_top12")
    primary_atu = meta.get("primary_atu")

    # --- human-in-the-loop fields (model vs expert)
    model_primary_atu = meta.get("model_primary_atu")
    final_decision_source = meta.get("final_decision_source")
    final_atu = meta.get("final_atu")
    final_expert_note = meta.get("final_expert_note")
    final_saved_at = _as_z(meta.get("final_saved_at") or "")

    # --- IRIs
    tale_iri = _rdf_iri("tale", _iri_safe(tid))
    event_iri = _rdf_iri("classificationEvent", _iri_safe(tid), ts)
    result_iri = _rdf_iri("classificationResult", _iri_safe(tid), ts)
    model_iri = _rdf_iri("model", _iri_safe(model_key))
    input_iri = _rdf_iri("inputText", _iri_safe(tid), ts)

    candidates = result.get("candidates") or []
    cand_nodes: List[Dict[str, Any]] = []

    for rank, c in enumerate(candidates[:k], start=1):
        atu_raw = str(c.get("atu", "")).strip()
        atu_norm = _atu_norm(atu_raw)
        score = c.get("score", None)

        ev = c.get("evidence") or {}
        snippets = ev.get("snippets") or []
        anchors = ev.get("anchors") or []

        evidence_node: Dict[str, Any] = {
            "@type": "rft:Evidence",
            "rft:snippetText": snippets,
            "rft:hasAnchorMatch": [],
        }

        for a in anchors:
            if isinstance(a, dict):
                span = a.get("span") or {}
                start = span.get("start_char")
                end = span.get("end_char")

                evidence_node["rft:hasAnchorMatch"].append(
                    {
                        "@type": "rft:AnchorMatch",
                        "rft:anchorId": a.get("anchor_id") or a.get("id"),
                        "rft:confidenceScore": a.get("score"),
                        "rdfs:comment": a.get("rationale"),
                        "rft:matchedText": a.get("snippet"),
                        "rft:startOffset": start,
                        "rft:endOffset": end,
                    }
                )
            else:
                evidence_node["rft:hasAnchorMatch"].append(
                    {
                        "@type": "rft:AnchorMatch",
                        "rft:matchedText": str(a),
                    }
                )

        cand_nodes.append(
            {
                "@type": "rft:ClassificationCandidate",
                "rft:rank": rank,
                "rft:predictedTaleType": {"@id": _rdf_iri("taleType", "atu", atu_norm)},
                "skos:notation": atu_raw,
                "rft:confidenceScore": float(score) if score is not None else None,
                "rft:hasEvidence": evidence_node,
            }
        )

    # --- prov:used list (model + input + optional typing source)
    used_list: List[Dict[str, Any]] = [{"@id": model_iri}, {"@id": input_iri}]
    if biblio_iri:
        used_list.append({"@id": biblio_iri})

    graph: List[Dict[str, Any]] = [
        {
            "@id": result_iri,
            "@type": ["rft:ClassificationResult", "prov:Entity"],
            "dcterms:identifier": tid,
            "rft:forTale": {"@id": tale_iri},
            "prov:wasGeneratedBy": {"@id": event_iri},
            "rft:hasCandidate": cand_nodes,
            "rft:taleStatus": tale_status,
            "rft:deltaTop12": float(delta_top12) if delta_top12 is not None else None,
            "rft:primaryATU": (
                {"@id": _rdf_iri("taleType", "atu", _atu_norm(str(primary_atu)))}
                if primary_atu
                else None
            ),

            # human-in-the-loop (explicit, even if primary_atu was overwritten)
            "rft:modelPrimaryATU": (
                {"@id": _rdf_iri("taleType", "atu", _atu_norm(str(model_primary_atu)))}
                if model_primary_atu
                else None
            ),
            "rft:finalATU": (
                {"@id": _rdf_iri("taleType", "atu", _atu_norm(str(final_atu)))}
                if final_atu
                else None
            ),
            "rft:finalDecisionSource": final_decision_source,
            "rft:finalExpertNote": final_expert_note,
            "rft:finalSavedAt": final_saved_at or None,
        },
        {
            "@id": event_iri,
            "@type": ["rft:ClassificationEvent", "prov:Activity", "crm:E7_Activity"],
            "dcterms:identifier": run_id,
            "prov:generatedAtTime": created_at,
            "rft:forTale": {"@id": tale_iri},
            "rft:sourceVersion": source_version,
            "prov:used": used_list,
            "rft:usedModel": {"@id": model_iri},
            "prov:generated": {"@id": result_iri},
            "rdfs:label": f"ATU classification for {tid}",
        },
        {
            "@id": model_iri,
            "@type": ["rft:Model", "prov:Entity"],
            "dcterms:identifier": model_key, 
            "rdfs:label": model_name,
            "rft:modelSha": model_sha or None,
            "rft:modelTag": model_version_tag,
            "rft:trainedAt": trained_at or None,
            "rft:task": task,
            "rft:textCols": text_cols,
            "dcterms:description": note,
            # typing source as model-level provenance
            "dcterms:source": {"@id": biblio_iri} if biblio_iri else None,
        },
        {
            "@id": input_iri,
            "@type": ["rft:InputText", "prov:Entity"],
            "dcterms:identifier": source_version,
            "rdfs:label": f"Input text hash for {tid}",
        },
        {
            "@id": tale_iri,
            "@type": "rft:Tale",
            "dcterms:identifier": tid,
        },
    ]

    if biblio_node:
        graph.append(biblio_node)

    jsonld: Dict[str, Any] = {
        "@context": CONTEXT,
        "@graph": graph,
    }

    def _drop_none(x: Any) -> Any:
        if isinstance(x, dict):
            return {k: _drop_none(v) for k, v in x.items() if v is not None}
        if isinstance(x, list):
            return [_drop_none(v) for v in x]
        return x

    return _drop_none(jsonld)
