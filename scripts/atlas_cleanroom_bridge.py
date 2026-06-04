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
PAIRING_TOKEN_ENV_NAMES = (
    "ATLAS_CLEANROOM_PAIRING_TOKEN",
    "MAXHERMES_CLEANROOM_PAIRING_TOKEN",
)


def cleanroom_auth_headers() -> dict:
    for name in SECRET_ENV_NAMES:
        value = os.environ.get(name, "").strip()
        if value:
            return {"x-atlas-cleanroom-secret": value}

    for name in PAIRING_TOKEN_ENV_NAMES:
        value = os.environ.get(name, "").strip()
        if value:
            return {"Authorization": f"Bearer {value}"}

    raise RuntimeError(
        "My hosted runtime is missing the clean-room webhook secret or short-lived pairing token, but the Azure endpoint exists."
    )


def post(path: str, payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "MaxHermes-Atlas-Cleanroom-Bridge/1.0",
    }
    headers.update(cleanroom_auth_headers())
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body,
        method="POST",
        headers=headers,
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


def post_public(path: str, payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
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


def get_public(path: str) -> dict:
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        method="GET",
        headers={
            "Accept": "application/json",
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
            "Usage: atlas_cleanroom_bridge.py status | public-status | pairing-start | pairing-exchange <pairingId> <verificationCode> | query <text> | factory | control",
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

        if command == "public-status":
            print(
                json.dumps(
                    get_public("/public/maxhermes/tool-status"),
                    indent=2,
                )
            )
            return 0

        if command == "pairing-start":
            print(
                json.dumps(
                    post_public(
                        "/public/maxhermes/pairing/start",
                        {
                            "requestedBy": "MaxHermes",
                            "scopes": [
                                "status",
                                "connection-plan",
                                "knowledge:read",
                                "factory:check",
                                "control-plane",
                            ],
                        },
                    ),
                    indent=2,
                )
            )
            return 0

        if command == "pairing-exchange":
            if len(argv) < 4:
                print("pairingId and verificationCode are required", file=sys.stderr)
                return 2
            print(
                json.dumps(
                    post_public(
                        "/public/maxhermes/pairing/exchange",
                        {
                            "pairingId": argv[2].strip(),
                            "verificationCode": argv[3].strip(),
                        },
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
