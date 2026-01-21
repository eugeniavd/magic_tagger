import sys
from rdf.queries import QUERIES

def main() -> int:
    qid = sys.argv[1] if len(sys.argv) > 1 else "Q1"
    q = QUERIES[qid]

    print(f"{q.id}: {q.purpose}")
    print(f"File: {q.path}")
    print("Default params:", q.default_params)
    print("\nCLI examples:")
    for line in q.cli_examples:
        print("  " + line)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
