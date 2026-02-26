from __future__ import annotations

import argparse
import json
import random
import string
import sys
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass
class HttpResponse:
    status: int
    body: dict | list | str


def request_json(
    method: str,
    url: str,
    *,
    payload: dict | None = None,
    headers: dict[str, str] | None = None,
) -> HttpResponse:
    raw_data = None
    request_headers = {"Content-Type": "application/json", **(headers or {})}
    if payload is not None:
        raw_data = json.dumps(payload).encode("utf-8")

    req = Request(url=url, method=method.upper(), data=raw_data, headers=request_headers)
    try:
        with urlopen(req, timeout=20) as resp:
            raw_body = resp.read().decode("utf-8")
            body = json.loads(raw_body) if raw_body else {}
            return HttpResponse(status=resp.status, body=body)
    except HTTPError as exc:
        raw_body = exc.read().decode("utf-8")
        body = json.loads(raw_body) if raw_body else {}
        return HttpResponse(status=exc.code, body=body)
    except URLError as exc:
        raise RuntimeError(f"request failed for {url}: {exc}") from exc


def random_email(prefix: str) -> str:
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"{prefix}-{suffix}@example.com"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke test post-deploy.")
    parser.add_argument(
        "--base-url", required=True, help="Base API URL, e.g. https://api.example.com"
    )
    parser.add_argument(
        "--run-auth-flow",
        action="store_true",
        help="Run register/login/me smoke flow",
    )
    parser.add_argument(
        "--email-prefix",
        default="smoke",
        help="Email prefix used when --run-auth-flow is enabled",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base_url = args.base_url.rstrip("/")

    live = request_json("GET", f"{base_url}/health/live")
    ready = request_json("GET", f"{base_url}/health/ready")
    openapi = request_json("GET", f"{base_url}/openapi.json")

    if live.status != 200:
        raise RuntimeError(f"/health/live failed status={live.status}")
    if ready.status != 200:
        raise RuntimeError(f"/health/ready failed status={ready.status}")
    if openapi.status != 200:
        raise RuntimeError(f"/openapi.json failed status={openapi.status}")

    print("health/openapi smoke checks passed")

    if not args.run_auth_flow:
        return

    email = random_email(args.email_prefix)
    password = "SmokePass123!"

    register = request_json(
        "POST",
        f"{base_url}/api/v1/auth/register",
        payload={"email": email, "password": password},
    )
    if register.status not in {200, 201}:
        raise RuntimeError(f"register failed status={register.status} body={register.body}")

    login = request_json(
        "POST",
        f"{base_url}/api/v1/auth/login",
        payload={"email": email, "password": password},
    )
    if login.status != 200:
        raise RuntimeError(f"login failed status={login.status} body={login.body}")

    access_token = str((login.body or {}).get("access_token", ""))
    if not access_token:
        raise RuntimeError("login did not return access_token")

    me = request_json(
        "GET",
        f"{base_url}/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if me.status != 200:
        raise RuntimeError(f"auth/me failed status={me.status} body={me.body}")

    print("auth smoke flow passed")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise
