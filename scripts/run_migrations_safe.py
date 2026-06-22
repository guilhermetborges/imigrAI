from __future__ import annotations

import argparse
import os
import subprocess
import sys


def _run(cmd: list[str], *, env: dict[str, str], capture_output: bool = False) -> str:
    result = subprocess.run(
        cmd,
        env=env,
        text=True,
        capture_output=capture_output,
        check=False,
    )
    if result.returncode != 0:
        if capture_output:
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(cmd)}")
    return result.stdout if capture_output else ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run alembic migrations with safety checks.")
    parser.add_argument("--database-url", required=True, help="Database URL used by application")
    parser.add_argument("--alembic-database-url", required=True, help="Database URL for Alembic")
    parser.add_argument("--label", default="target", help="target label for logs")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    env = os.environ.copy()
    env["DATABASE_URL"] = args.database_url
    env["ALEMBIC_DATABASE_URL"] = args.alembic_database_url

    print(f"[{args.label}] running alembic upgrade head")
    _run([sys.executable, "-m", "alembic", "upgrade", "head"], env=env)

    current = _run([sys.executable, "-m", "alembic", "current"], env=env, capture_output=True)
    heads = _run([sys.executable, "-m", "alembic", "heads"], env=env, capture_output=True)

    if not current.strip():
        raise RuntimeError("alembic current returned empty output")
    if not heads.strip():
        raise RuntimeError("alembic heads returned empty output")

    current_revision = current.strip().split()[0]
    head_revision = heads.strip().split()[0]
    if current_revision != head_revision:
        raise RuntimeError(
            f"database not at head revision: current={current_revision} head={head_revision}"
        )

    print(f"[{args.label}] migration validated at revision={head_revision}")


if __name__ == "__main__":
    main()
