from __future__ import annotations

import argparse
import asyncio
import json

from scripts.check_mvp_seed import check_seed
from scripts.seed_initial_data import run_seed


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="imigrAI application CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("seed-mvp", help="Seed MVP country/program/source baseline")
    subparsers.add_parser("check-mvp-seed", help="Validate MVP seed counts and idempotency")

    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    if args.command == "seed-mvp":
        output = asyncio.run(run_seed())
    elif args.command == "check-mvp-seed":
        output = asyncio.run(check_seed())
    else:
        raise ValueError(f"Unsupported command: {args.command}")

    print(json.dumps(output, ensure_ascii=True))


if __name__ == "__main__":
    main()
