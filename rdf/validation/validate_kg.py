#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
from pathlib import Path

from pyshacl import validate


def main() -> int:
    # This file: <repo>/rdf/validation/validate_kg.py
    # Repo root: 3 levels up
    repo_root = Path(__file__).resolve().parents[2]

    ap = argparse.ArgumentParser(
        description=(
            "Validate KG TTL against SHACL shapes using pySHACL. "
            "Writes a SHACL report and returns CI-friendly exit code."
        )
    )
    ap.add_argument(
        "--data",
        default=str(repo_root / "rdf" / "rdf_serialization" / "corpus.ttl"),
        help="Path to data graph TTL",
    )
    ap.add_argument(
        "--shapes",
        default=str(repo_root / "rdf" / "shacl" / "shapes.ttl"),
        help="Path to shapes TTL",
    )
    ap.add_argument(
        "--report",
        default=str(repo_root / "rdf" / "validation" / "report.ttl"),
        help="Path to report TTL",
    )
    ap.add_argument(
        "--report-text",
        default=str(repo_root / "rdf" / "validation" / "report.txt"),
        help="Path to human-readable report text",
    )
    ap.add_argument("--data-format", default="turtle", help="RDF format for data (default: turtle).")
    ap.add_argument("--shapes-format", default="turtle", help="RDF format for shapes (default: turtle).")
    ap.add_argument(
        "--inference",
        default="none",
        choices=["none", "rdfs", "owlrl", "both"],
        help="Inference mode (default: none).",
    )
    ap.add_argument("--abort-on-first", action="store_true", help="Stop on first violation (faster, less informative).")
    ap.add_argument("--meta-shacl", action="store_true", help="Validate the SHACL shapes graph itself.")
    ap.add_argument("--advanced", action="store_true", help="Enable SHACL Advanced Features.")
    ap.add_argument("--debug", action="store_true", help="Enable pySHACL debug output.")
    args = ap.parse_args()

    data_path = Path(args.data).expanduser().resolve()
    shapes_path = Path(args.shapes).expanduser().resolve()
    report_path = Path(args.report).expanduser().resolve()
    report_text_path = Path(args.report_text).expanduser().resolve()

    if not data_path.exists():
        raise FileNotFoundError(f"Data graph not found: {data_path}")
    if not shapes_path.exists():
        raise FileNotFoundError(f"Shapes graph not found: {shapes_path}")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_text_path.parent.mkdir(parents=True, exist_ok=True)

    conforms, report_graph, report_text = validate(
        data_graph=str(data_path),
        data_graph_format=args.data_format,
        shacl_graph=str(shapes_path),
        shacl_graph_format=args.shapes_format,
        inference=args.inference,
        abort_on_first=args.abort_on_first,
        meta_shacl=args.meta_shacl,
        advanced=args.advanced,
        debug=args.debug,
    )

    # Machine-readable RDF report
    report_graph.serialize(destination=str(report_path), format="turtle")

    # Human-readable text report
    report_text_path.write_text(report_text, encoding="utf-8")

    print(f"Conforms: {conforms}")
    print(f"Wrote: {report_path}")
    print(f"Wrote: {report_text_path}")

    return 0 if conforms else 1


if __name__ == "__main__":
    raise SystemExit(main())
