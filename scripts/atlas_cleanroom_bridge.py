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
CONTROL_PLANE_URL = "https://atlas-maxhermes-control-plane.azurewebsites.net"
SECRET_ENV_NAMES = (
    "ATLAS_CLEANROOM_WEBHOOK_SECRET",
    "MAXHERMES_CLEANROOM_WEBHOOK_SECRET",
)
CONTROL_PLANE_SECRET_ENV_NAMES = (
    "MAXHERMES_CONTROL_PLANE_CLIENT_SECRET",
    "ATLAS_MAXHERMES_CONTROL_PLANE_CLIENT_SECRET",
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


def control_plane_auth_headers() -> dict:
    for name in CONTROL_PLANE_SECRET_ENV_NAMES:
        value = os.environ.get(name, "").strip()
        if value:
            return {"x-atlas-maxhermes-control-secret": value}

    raise RuntimeError(
        "My hosted runtime can reach the Azure MaxHermes control plane, but it does not have private control-plane authentication mounted."
    )


def post(path: str, payload: dict, base_url: str = BASE_URL, headers: dict | None = None) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request_headers = {
        "Content-Type": "application/json",
        "User-Agent": "MaxHermes-Atlas-Cleanroom-Bridge/1.0",
    }
    request_headers.update(headers or cleanroom_auth_headers())
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=body,
        method="POST",
        headers=request_headers,
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


def get_public(path: str, base_url: str = BASE_URL) -> dict:
    request = urllib.request.Request(
        f"{base_url}{path}",
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


def print_json(body: dict) -> None:
    print(json.dumps(body, indent=2))


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] in {"-h", "--help", "help"}:
        print(
            "Usage: atlas_cleanroom_bridge.py status | public-status | pairing-start | pairing-exchange <pairingId> <verificationCode> | query <text> | factory | control | control-health | control-status | control-tool-status | control-query <text>",
            file=sys.stderr,
        )
        return 2

    command = argv[1].lower().strip()
    try:
        if command == "status":
            print_json(
                summarize_status(
                    post("/connectors/maxhermes/tool-status", {})
                )
            )
            return 0

        if command == "public-status":
            print_json(get_public("/public/maxhermes/tool-status"))
            return 0

        if command == "control-health":
            print_json(get_public("/health", base_url=CONTROL_PLANE_URL))
            return 0

        if command == "control-status":
            print_json(get_public("/status", base_url=CONTROL_PLANE_URL))
            return 0

        if command == "control-tool-status":
            print_json(
                summarize_status(
                    post(
                        "/tool-status",
                        {},
                        base_url=CONTROL_PLANE_URL,
                        headers=control_plane_auth_headers(),
                    )
                )
            )
            return 0

        if command == "control-query":
            text = " ".join(argv[2:]).strip()
            if not text:
                print("query text is required", file=sys.stderr)
                return 2
            print_json(
                post(
                    "/knowledge-query",
                    {"query": text, "limit": 3},
                    base_url=CONTROL_PLANE_URL,
                    headers=control_plane_auth_headers(),
                )
            )
            return 0

        if command == "pairing-start":
            print_json(
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
                )
            )
            return 0

        if command == "pairing-exchange":
            if len(argv) < 4:
                print("pairingId and verificationCode are required", file=sys.stderr)
                return 2
            print_json(
                post_public(
                    "/public/maxhermes/pairing/exchange",
                    {
                        "pairingId": argv[2].strip(),
                        "verificationCode": argv[3].strip(),
                    },
                )
            )
            return 0

        if command == "query":
            text = " ".join(argv[2:]).strip()
            if not text:
                print("query text is required", file=sys.stderr)
                return 2
            print_json(
                post(
                    "/connectors/maxhermes/knowledge-query",
                    {"text": text, "requestedBy": "MaxHermes"},
                )
            )
            return 0

        if command == "factory":
            print_json(
                post(
                    "/connectors/maxhermes/factory-maintenance-check",
                    {"requestedBy": "MaxHermes"},
                )
            )
            return 0

        if command == "control":
            print_json(
                post(
                    "/connectors/maxhermes/control-plane",
                    {"requestedBy": "MaxHermes"},
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
