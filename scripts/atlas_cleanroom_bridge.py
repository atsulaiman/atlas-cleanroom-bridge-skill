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
SCREENPIPE_SECRET_ENV_NAMES = (
    "SCREENPIPE_CLEANROOM_API_KEY",
    "ATLAS_SCREENPIPE_CLEANROOM_API_KEY",
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


def screenpipe_auth_headers() -> dict:
    for name in SCREENPIPE_SECRET_ENV_NAMES:
        value = os.environ.get(name, "").strip()
        if value:
            return {"x-atlas-screenpipe-secret": value}

    raise RuntimeError(
        "My hosted runtime can reach the clean-room API, but it does not have Screenpipe context auth mounted."
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


def summarize_notion_status(body: dict) -> dict:
    configured = body.get("configuredConnectors", [])
    blocked = body.get("blockedConnectors", [])
    notion_configured = "notion" in configured
    return {
        "ok": bool(body.get("ok") and notion_configured),
        "status": "notion_cleanroom_configured"
        if notion_configured
        else "notion_cleanroom_not_configured",
        "connector": "notion",
        "mode": "cleanroom_ledger_via_atlas_api",
        "configured": notion_configured,
        "blocked": "notion" in blocked,
        "summary": body.get("summary"),
        "privateActionsRequireAuthenticatedBridge": True,
        "matrixMcpRequired": False,
        "localNotionMcpRequired": False,
        "notionTokenFromUserRequired": False,
        "note": (
            "Notion is connected through the Atlas clean-room API and Azure control plane. "
            "Do not ask Ahmad for a Notion integration token or Atlas webhook secret in chat."
        ),
    }


def print_json(body: dict) -> None:
    print(json.dumps(body, indent=2))


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] in {"-h", "--help", "help"}:
        print(
            "Usage: atlas_cleanroom_bridge.py status | public-status | notion-status | codex-operator-status | codex-request <text> | pairing-start | pairing-exchange <pairingId> <verificationCode> | query <text> | factory | control | screenpipe | control-health | control-status | control-tool-status | control-query <text>",
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

        if command == "notion-status":
            print_json(summarize_notion_status(get_public("/public/maxhermes/tool-status")))
            return 0

        if command == "codex-operator-status":
            health = get_public("/health", base_url=CONTROL_PLANE_URL)
            status = get_public("/status", base_url=CONTROL_PLANE_URL)
            print_json(
                {
                    "ok": bool(health.get("ok") and status.get("ok")),
                    "status": "codex_operator_bridge_ready"
                    if health.get("ok") and status.get("ok")
                    else "codex_operator_bridge_unready",
                    "connectionType": "codex_operator_to_azure_control_plane",
                    "codexDirectMcpServer": False,
                    "matrixOrClawServerRequired": False,
                    "controlPlane": {
                        "url": CONTROL_PLANE_URL,
                        "health": health.get("status"),
                        "status": status.get("status"),
                        "clientAuthConfigured": health.get("clientAuthConfigured"),
                    },
                    "note": (
                        "Codex is connected as the local engineering/operator surface through the Azure MaxHermes control plane. "
                        "There is no clean-room Codex MCP route named /codex or /invoke on Matrix or claw-server."
                    ),
                }
            )
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

        if command == "codex-request":
            text = " ".join(argv[2:]).strip()
            if not text:
                print("request text is required", file=sys.stderr)
                return 2
            print_json(
                post(
                    "/codex/operator-request",
                    {"text": text, "requestedBy": "MaxHermes", "priority": "normal"},
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
                    {
                        "requestedBy": "MaxHermes",
                        "requestedConnectors": [
                            "factoryai",
                            "openrouter",
                            "mem0",
                            "zep",
                            "obsidian",
                            "screenpipe",
                        ],
                    },
                )
            )
            return 0

        if command == "screenpipe":
            print_json(
                post(
                    "/connectors/screenpipe/context-test",
                    {"source": "minimax-bridge", "health": {}},
                    headers=screenpipe_auth_headers(),
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
