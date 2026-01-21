from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass(frozen=True)
class QuerySpec:
    id: str
    path: Path
    purpose: str
    cli_examples: List[str]


BASE_DIR = Path(__file__).resolve().parent

QUERIES: Dict[str, QuerySpec] = {
    "Q1": QuerySpec(
        id="Q1",
        path=BASE_DIR / "Q1_tales_by_atu_type.rq",
        purpose="Tales by ATU type (baseline snapshot)",
        cli_examples=[
            "python -m rdf.queries.run Q1 --data kg/export/corpus.ttl --out artifacts/query_results",
        ],
    ),
    "Q2": QuerySpec(
        id="Q2",
        path=BASE_DIR / "Q2_top_atu_types.rq",
        purpose="Distribution of ATU types (Top 20)",
        cli_examples=[
            "python -m rdf.queries.run Q2 --data kg/export/corpus.ttl --out artifacts/query_results",
        ],
    ),
    "Q3": QuerySpec(
    id="Q3",
    path=BASE_DIR / "Q3_top_narrators.rq",
    purpose="Top narrators by number of tales",
    cli_examples=[
        "python -m rdf.queries.run Q3 --data kg/export/corpus.ttl --out artifacts/query_results",
    ],
),
"Q4": QuerySpec(
    id="Q4",
    path=BASE_DIR / "Q4_top_collectors_time_coverage.rq",
    purpose="Top collectors via volumes + time coverage (min/max volume date)",
    cli_examples=[
        "python -m rdf.queries.run Q4 --data kg/export/corpus.ttl --out artifacts/query_results",
    ],
),
"Q5": QuerySpec(
    id="Q5",
    path=BASE_DIR / "Q5_coverage_sanity_checks.rq",
    purpose="Coverage sanity checks: missing volume / missing subject / missing place",
    cli_examples=[
        "python -m rdf.queries.run Q5 --data kg/export/corpus.ttl --out artifacts/query_results",
    ],
),

}
