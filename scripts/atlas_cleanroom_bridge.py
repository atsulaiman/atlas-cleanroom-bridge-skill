#!/usr/bin/env python3
"""MiniMax/MaxHermes helper for the Atlas Clean-Room API.

This script intentionally reads auth only from environment variables and never
prints the secret value.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


BASE_URL = "https://atlas-cleanroom-api.azurewebsites.net"
SECRET_ENV_NAMES = (
    "ATLAS_CLEANROOM_WEBHOOK_SECRET",
    "MAXHERMES_CLEANROOM_WEBHOOK_SECRET",
)


def cleanroom_secret() -> str:
    for name in SECRET_ENV_NAMES:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    raise RuntimeError(
        "My hosted runtime is missing the clean-room webhook secret, but the Azure endpoint exists."
    )


def post(path: str, payload: dict) -> dict:
    secret = cleanroom_secret()
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-atlas-cleanroom-secret": secret,
            "User-Agent": "MaxHermes-Atlas-Cleanroom-Bridge/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        response_text = error.read().decode("utf-8", errors="replace")
        try:
            response_body = json.loads(response_text)
        except json.JSONDecodeError:
            response_body = {"error": response_text}
        return {
            "ok": False,
            "httpStatus": error.code,
            "status": response_body.get("status", "cleanroom_http_error"),
            "response": response_body,
        }


def summarize_status(body: dict) -> dict:
    connectors = body.get("connectors", [])
    return {
        "ok": body.get("ok", False),
        "status": body.get("status"),
        "summary": body.get("summary"),
        "configuredConnectors": [
            item.get("connector") for item in connectors if item.get("ok")
        ],
        "blockedConnectors": [
            item.get("connector") for item in connectors if not item.get("ok")
        ],
        "note": body.get("note"),
    }


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] in {"-h", "--help", "help"}:
        print(
            "Usage: atlas_cleanroom_bridge.py status | query <text> | factory | control",
            file=sys.stderr,
        )
        return 2

    command = argv[1].lower().strip()
    try:
        if command == "status":
            print(
                json.dumps(
                    summarize_status(
                        post("/connectors/maxhermes/tool-status", {})
                    ),
                    indent=2,
                )
            )
            return 0

        if command == "query":
            text = " ".join(argv[2:]).strip()
            if not text:
                print("query text is required", file=sys.stderr)
                return 2
            print(
                json.dumps(
                    post(
                        "/connectors/maxhermes/knowledge-query",
                        {"text": text, "requestedBy": "MaxHermes"},
                    ),
                    indent=2,
                )
            )
            return 0

        if command == "factory":
            print(
                json.dumps(
                    post(
                        "/connectors/maxhermes/factory-maintenance-check",
                        {"requestedBy": "MaxHermes"},
                    ),
                    indent=2,
                )
            )
            return 0

        if command == "control":
            print(
                json.dumps(
                    post(
                        "/connectors/maxhermes/control-plane",
                        {"requestedBy": "MaxHermes"},
                    ),
                    indent=2,
                )
            )
            return 0

        print(f"unknown command: {command}", file=sys.stderr)
        return 2
    except RuntimeError as error:
        print(str(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

