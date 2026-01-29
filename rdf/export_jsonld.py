

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import argparse
import json
from typing import Any, Dict, List, Optional, Sequence, Union

from rdflib import Graph


def load_context(context_path: Path) -> Any:
    """
    Accepts either:
      - {"@context": {...}} or {"@context": [...]}
      - or a raw context object {...} / [...]
    Returns the value to use under @context.
    """
    ctx_obj = json.loads(context_path.read_text(encoding="utf-8"))
    if isinstance(ctx_obj, dict) and "@context" in ctx_obj:
        return ctx_obj["@context"]
    return ctx_obj


def iter_ttl_inputs(
    ttl: Optional[str],
    ttl_dir: Optional[str],
    ttl_list: Optional[Sequence[str]],
    glob_pat: str,
) -> List[Path]:
    paths: List[Path] = []

    if ttl:
        paths.append(Path(ttl))
    if ttl_dir:
        d = Path(ttl_dir)
        paths.extend(sorted(d.glob(glob_pat)))
    if ttl_list:
        paths.extend(Path(p) for p in ttl_list)

    # normalize, validate, de-dup while keeping order
    seen = set()
    out: List[Path] = []
    for p in paths:
        rp = p.expanduser().resolve()
        if rp in seen:
            continue
        seen.add(rp)
        out.append(rp)

    if not out:
        raise ValueError("No inputs. Use --ttl or --ttl-dir or --ttl-list.")
    return out


def wrap_with_context(
    data: Union[Dict[str, Any], List[Any]],
    ctx: Any,
    as_graph: bool,
) -> Dict[str, Any]:
    """
    Ensure top-level JSON-LD is a dict with @context.
    If input is list, wrap into {"@context":..., "@graph":[...]}.
    If as_graph=True, always output {"@context":..., "@graph":[...]}.
    """
    if as_graph:
        if isinstance(data, dict):
            # if rdflib returns dict with @graph, keep it; else wrap dict in @graph
            if "@graph" in data and isinstance(data["@graph"], list):
                graph_items = data["@graph"]
            else:
                graph_items = [data]
        elif isinstance(data, list):
            graph_items = data
        else:
            raise TypeError(f"Unexpected JSON-LD top-level type: {type(data)}")

        return {"@context": ctx, "@graph": graph_items}

    # not forced graph mode
    if isinstance(data, dict):
        data["@context"] = ctx
        return data
    if isinstance(data, list):
        return {"@context": ctx, "@graph": data}
    raise TypeError(f"Unexpected JSON-LD top-level type: {type(data)}")


def export_one(
    ttl_path: Path,
    ctx: Any,
    out_path: Path,
    compact: bool,
    as_graph: bool,
) -> None:
    g = Graph()
    g.parse(str(ttl_path), format="turtle")

    raw = g.serialize(format="json-ld", auto_compact=compact)
    data = json.loads(raw)

    wrapped = wrap_with_context(data, ctx=ctx, as_graph=as_graph)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(wrapped, ensure_ascii=False, indent=2), encoding="utf-8")


def default_out_path(out_dir: Path, ttl_path: Path) -> Path:
    return out_dir / (ttl_path.stem + ".jsonld")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Serialize TTL to JSON-LD and inject a single canonical @context. Supports batch export."
    )

    src = ap.add_argument_group("Input")
    src.add_argument("--ttl", help="Single input TTL file.")
    src.add_argument("--ttl-dir", help="Directory with TTL files.")
    src.add_argument(
        "--ttl-list",
        nargs="+",
        help="One or more TTL paths (space-separated).",
    )
    src.add_argument(
        "--glob",
        default="*.ttl",
        help="Glob pattern for --ttl-dir (default: *.ttl).",
    )

    ap.add_argument("--context", required=True, help="JSON-LD context file path.")
    ap.add_argument("--compact", action="store_true", help="Try to compact output (best-effort).")
    ap.add_argument(
        "--as-graph",
        action="store_true",
        help="Always output as {'@context':..., '@graph':[...]} for stable top-level structure.",
    )

    out = ap.add_argument_group("Output")
    out.add_argument("--out", help="Output JSON-LD file path (only for single --ttl).")
    out.add_argument("--out-dir", help="Output directory (for batch or single; default: alongside TTL).")

    args = ap.parse_args()

    ctx_path = Path(args.context).expanduser().resolve()
    if not ctx_path.exists():
        raise FileNotFoundError(f"Context file not found: {ctx_path}")

    ctx = load_context(ctx_path)

    inputs = iter_ttl_inputs(args.ttl, args.ttl_dir, args.ttl_list, args.glob)

    # output mode resolution
    if args.out and len(inputs) != 1:
        raise ValueError("--out can only be used with a single input. Use --out-dir for batch.")

    if args.out:
        out_path = Path(args.out).expanduser().resolve()
        export_one(inputs[0], ctx=ctx, out_path=out_path, compact=args.compact, as_graph=args.as_graph)
        print(f"Wrote: {out_path}")
        return 0

    # out-dir mode (batch or single)
    for ttl_path in inputs:
        if not ttl_path.exists():
            raise FileNotFoundError(f"TTL not found: {ttl_path}")

        out_dir = (
            Path(args.out_dir).expanduser().resolve()
            if args.out_dir
            else ttl_path.parent
        )
        out_path = default_out_path(out_dir, ttl_path)
        export_one(ttl_path, ctx=ctx, out_path=out_path, compact=args.compact, as_graph=args.as_graph)
        print(f"Wrote: {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
