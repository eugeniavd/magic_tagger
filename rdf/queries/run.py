from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Iterable, List

import pandas as pd
from rdflib import Graph

from rdf.queries import QUERIES


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _expand_data_inputs(data_args: List[str]) -> List[Path]:
    """
    Accepts repeated --data arguments.
    Each item can be:
      - a TTL file path
      - a directory (we load all *.ttl recursively)
      - a glob pattern (e.g., rdf/rdf_serialization/**/*.ttl)
    Returns a unique, sorted list of existing files.
    """
    files: List[Path] = []
    for raw in data_args:
        p = Path(raw)

        # Glob pattern
        if any(ch in raw for ch in ["*", "?", "["]):
            matches = [Path(x) for x in sorted(Path().glob(raw))]
            files.extend(matches)
            continue

        # Directory: load all TTL recursively
        if p.exists() and p.is_dir():
            files.extend(sorted(p.rglob("*.ttl")))
            continue

        # File
        files.append(p)

    # Normalize + filter
    norm: List[Path] = []
    seen = set()
    for f in files:
        f = f.resolve()
        if f in seen:
            continue
        seen.add(f)
        norm.append(f)

    # Keep only existing files
    existing = [f for f in norm if f.exists() and f.is_file()]
    return existing


def run_query_to_df(data_ttls: Iterable[Path], query_rq: Path) -> pd.DataFrame:
    g = Graph()

    # parse multiple TTLs into one graph
    parsed = 0
    for ttl in data_ttls:
        g.parse(str(ttl), format="turtle")
        parsed += 1

    if parsed == 0:
        raise SystemExit("No TTL files were loaded. Check --data arguments.")

    sparql = _read_text(query_rq)
    res = g.query(sparql)

    cols = [str(v) for v in res.vars]
    rows = []
    for row in res:
        # row is a tuple aligned with vars
        rows.append([("" if v is None else str(v)) for v in row])

    return pd.DataFrame(rows, columns=cols)


def main() -> int:
    p = argparse.ArgumentParser(description="Run SPARQL (.rq) against local TTL(s) and export CSV.")
    p.add_argument("qid", help="Query id, e.g. Q1")

    # NEW: --data is repeatable; can be file, dir, or glob
    p.add_argument(
        "--data",
        action="append",
        default=[],
        help=(
            "Path to TTL file OR directory OR glob. "
            "Repeatable. Example: --data rdf/rdf_serialization/agents.ttl --data rdf/rdf_serialization/tales.ttl "
            "or --data rdf/rdf_serialization (loads all *.ttl recursively)."
        ),
    )

    p.add_argument("--out", default="rdf/queries/query_results", help="Output directory for CSV")
    p.add_argument("--preview", type=int, default=10, help="How many rows to preview in stdout")
    args = p.parse_args()

    qid = args.qid.upper()
    if qid not in QUERIES:
        known = ", ".join(sorted(QUERIES))
        raise SystemExit(f"Unknown query id: {qid}. Known: {known}")

    spec = QUERIES[qid]
    if not spec.path.exists():
        raise SystemExit(f"Query file not found: {spec.path}")

    # If user didn't pass --data, provide a sensible default for your repo layout
    # (adjust if your canonical TTL bundle is elsewhere)
    data_args = args.data or ["rdf/rdf_serialization"]

    ttl_files = _expand_data_inputs(data_args)
    if not ttl_files:
        raise SystemExit(
            "No TTL files found for --data inputs:\n"
            + "\n".join(f"  - {x}" for x in data_args)
        )

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / f"{qid}.csv"

    print(f"[run] {qid}: {spec.purpose}", file=sys.stderr)
    print(f"[run] query: {spec.path}", file=sys.stderr)
    print(f"[run] ttl files ({len(ttl_files)}):", file=sys.stderr)
    for f in ttl_files[:30]:
        print(f"  - {f}", file=sys.stderr)
    if len(ttl_files) > 30:
        print(f"  ... +{len(ttl_files) - 30} more", file=sys.stderr)

    df = run_query_to_df(ttl_files, spec.path)
    df.to_csv(out_csv, index=False, encoding="utf-8")

    print(f"[ok] rows={len(df)} cols={len(df.columns)}", file=sys.stderr)
    print(f"[ok] wrote: {out_csv}", file=sys.stderr)

    if args.preview > 0:
        print("\n=== CSV preview (head) ===")
        print(df.head(args.preview).to_string(index=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
