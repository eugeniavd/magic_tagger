#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path

import pandas as pd

# -----------------------------
# Defaults (repo)
# -----------------------------
REPO_ROOT = Path("/Users/eugenia/Desktop/thesis/magic_tagger")
DEFAULT_INPUT = REPO_ROOT / "data" / "processed" / "corpus_a_for_kg.csv"
DEFAULT_OUT = REPO_ROOT / "data" / "processed" / "volume_kivike_map.csv"

ENV_INPUT = "CORPUS_CANONICAL_CSV"
ENV_OUT = "VOLUME_KIVIKE_MAP_CSV"


# -----------------------------
# Robust delimiter + encoding
# -----------------------------
def read_sample_text(path: Path, n: int = 5000) -> str:
    raw = path.read_bytes()[: n * 4]
    for enc in ("utf-8-sig", "utf-8", "cp1251", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def detect_delimiter(path: Path) -> str:
    sample = read_sample_text(path, n=5000)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t", "|"])
        return dialect.delimiter
    except Exception:
        header = sample.splitlines()[0] if sample.splitlines() else ""
        return max([",", ";", "\t", "|"], key=lambda d: header.count(d))


def read_csv_fallback(path: Path, sep: str) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "cp1251", "cp1252", "latin-1"):
        try:
            return pd.read_csv(path, sep=sep, dtype=str, keep_default_na=False, encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(
        path, sep=sep, dtype=str, keep_default_na=False,
        encoding="utf-8", encoding_errors="replace"
    )


def clean_ws(x: object) -> str:
    return " ".join(str(x).split()).strip() if x is not None else ""


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Extract unique volumes from canonical corpus table and create a Kivike mapping template."
    )
    ap.add_argument("--csv", default=None, help="Input corpus CSV (canonical table).")
    ap.add_argument("--out", default=None, help="Output mapping CSV path.")
    ap.add_argument("--collection", default=None, help="Optional filter, e.g. 'era_vene'.")
    args = ap.parse_args()

    in_path = Path(
        args.csv
        or os.environ.get(ENV_INPUT, "")
        or str(DEFAULT_INPUT)
    ).expanduser().resolve()

    out_path = Path(
        args.out
        or os.environ.get(ENV_OUT, "")
        or str(DEFAULT_OUT)
    ).expanduser().resolve()

    if not in_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {in_path}")

    sep = detect_delimiter(in_path)
    df = read_csv_fallback(in_path, sep=sep)

    required = ["volume_id", "collection"]
    for c in required:
        if c not in df.columns:
            raise KeyError(f"Missing required column: {c}")

    df["volume_id"] = df["volume_id"].map(clean_ws)
    df["collection"] = df["collection"].map(clean_ws)

    if args.collection:
        df = df[df["collection"] == clean_ws(args.collection)]

    # Unique per volume_id; keep collection too
    vdf = (
        df[df["volume_id"].ne("") & df["collection"].ne("")]
        .drop_duplicates(subset=["volume_id"], keep="first")
        .loc[:, ["volume_id", "collection"]]
        .sort_values(["collection", "volume_id"], kind="mergesort")
        .reset_index(drop=True)
    )

    # Add empty columns for manual fill
    vdf["kivike_pid"] = ""   # e.g. ERA-17310-43411-19198
    vdf["kivike_url"] = ""   # full URL
    vdf["notes"] = ""        # optional comment (coverage, uncertainty, etc.)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    vdf.to_csv(out_path, index=False, encoding="utf-8")

    print(f"Wrote: {out_path}")
    print(f"Volumes: {len(vdf)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
