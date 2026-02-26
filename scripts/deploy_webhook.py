from __future__ import annotations

import argparse
import json
import os
from urllib.request import Request, urlopen


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Trigger deployment webhook.")
    parser.add_argument("--url", required=True, help="Webhook URL")
    parser.add_argument("--environment", required=True, choices=["staging", "production"])
    parser.add_argument("--sha", default=os.getenv("GITHUB_SHA", "unknown"))
    parser.add_argument("--ref", default=os.getenv("GITHUB_REF_NAME", "unknown"))
    parser.add_argument("--token", default=os.getenv("DEPLOY_WEBHOOK_TOKEN", ""))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    body = {
        "environment": args.environment,
        "sha": args.sha,
        "ref": args.ref,
    }
    headers = {"Content-Type": "application/json"}
    if args.token:
        headers["Authorization"] = f"Bearer {args.token}"

    request = Request(
        url=args.url,
        method="POST",
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
    )
    with urlopen(request, timeout=20) as response:
        if response.status >= 300:
            raise RuntimeError(f"deploy webhook failed: status={response.status}")

    print(f"deploy webhook triggered for {args.environment}")


if __name__ == "__main__":
    main()
