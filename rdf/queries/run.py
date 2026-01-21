from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd
from rdflib import Graph

from rdf.queries import QUERIES


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def run_query_to_df(data_ttl: Path, query_rq: Path) -> pd.DataFrame:
    g = Graph()
    # format="turtle" 
    g.parse(str(data_ttl), format="turtle")

    sparql = _read_text(query_rq)
    res = g.query(sparql)

    cols = [str(v) for v in res.vars]
    rows = []
    for row in res:
        # row is a tuple aligned with vars
        rows.append([("" if v is None else str(v)) for v in row])

    return pd.DataFrame(rows, columns=cols)


def main() -> int:
    p = argparse.ArgumentParser(description="Run SPARQL (.rq) against a local TTL and export CSV.")
    p.add_argument("qid", help="Query id, e.g. Q1")
    p.add_argument("--data", default="kg/export/corpus.ttl", help="Path to TTL data")
    p.add_argument("--out", default="artifacts/query_results", help="Output directory for CSV")
    p.add_argument("--preview", type=int, default=10, help="How many rows to preview in stdout")
    args = p.parse_args()

    qid = args.qid.upper()
    if qid not in QUERIES:
        known = ", ".join(sorted(QUERIES))
        raise SystemExit(f"Unknown query id: {qid}. Known: {known}")

    data_path = Path(args.data)
    if not data_path.exists():
        raise SystemExit(f"Data file not found: {data_path}")

    spec = QUERIES[qid]
    if not spec.path.exists():
        raise SystemExit(f"Query file not found: {spec.path}")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / f"{qid}.csv"

    print(f"[run] {qid}: {spec.purpose}", file=sys.stderr)
    print(f"[run] data:  {data_path}", file=sys.stderr)
    print(f"[run] query: {spec.path}", file=sys.stderr)

    df = run_query_to_df(data_path, spec.path)
    df.to_csv(out_csv, index=False, encoding="utf-8")

    print(f"[ok] rows={len(df)} cols={len(df.columns)}", file=sys.stderr)
    print(f"[ok] wrote: {out_csv}", file=sys.stderr)

    # Human-friendly preview for the evaluator
    if args.preview > 0:
        print("\n=== CSV preview (head) ===")
        print(df.head(args.preview).to_string(index=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
