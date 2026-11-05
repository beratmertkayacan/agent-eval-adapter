"""Export stored runs as a dataset: python export.py --format jsonl"""

import argparse
from pathlib import Path

from adapter.export import export_runs
from adapter.main import get_service

EXPORTS_DIR = Path(__file__).resolve().parent / "exports"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export stored runs for evaluation tools.")
    parser.add_argument("--format", choices=["json", "jsonl"], default="json")
    parser.add_argument(
        "--output", type=Path, help="File to write (default: exports/dataset.<format>)"
    )
    args = parser.parse_args(argv)

    output = args.output or EXPORTS_DIR / f"dataset.{args.format}"
    runs = get_service().list_runs()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(export_runs(runs, args.format), encoding="utf-8")
    print(f"Exported {len(runs)} runs to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
