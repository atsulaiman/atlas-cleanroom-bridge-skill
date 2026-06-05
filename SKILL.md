---
name: atlas-cleanroom-bridge
description: Use this skill when Ahmad or MaxHermes asks to check Atlas clean-room tool status, query Atlas knowledge through Notion/Onyx, run a Factory AI maintenance readiness check, or sync the MaxHermes control plane. Triggers include "what tools are connected", "check clean-room status", "query Atlas knowledge", "ask Onyx", "check Notion", "settlements", "cases", "revenue", "intake", "projects", "commitments", "meetings", "run Factory maintenance", and "control-plane sync". Do not use this skill for generic web research or local file edits that do not need Atlas clean-room state.
---

# Atlas Clean-Room Bridge

Use this skill to let MaxHermes/Mavis call the Atlas Clean-Room API directly instead of asking Ahmad to relay status between Codex, Notion, Onyx, Factory AI, and MiniMax.

## Boundary

Primary production control-plane URL:

`https://atlas-maxhermes-control-plane.azurewebsites.net`

Clean-room API URL:

`https://atlas-cleanroom-api.azurewebsites.net`

Never use:

- old Cloudflare routes
- `command.atlaslaw.ai`
- old Hermes Workspace
- old Hermes Dashboard
- old Factory droids or sessions
- old Notion database IDs
- old Onyx connector IDs
- old Mem0, Zep, Pinecone, Box, Obsidian, or wiki memory exports

Never print, store, summarize, or ask Ahmad to paste the clean-room webhook secret. The API secret must come from a secure MiniMax runtime secret or environment variable.

Do not populate the MiniMax secret store by asking an agent to call `secret({ command: "create", args: "--name=... --value=PLAINTEXT" })` in chat. As verified on June 4, 2026, that agent-facing path passes the plaintext value through tool-call arguments and can place the secret in transcripts. It is acceptable only for non-secret placeholders or if MiniMax later provides a confirmed masked-entry surface.

If MiniMax does not expose a secure UI, API, CLI, OAuth, masked-input, or platform secret-mount flow, fail closed and tell Ahmad that MaxHermes needs a transcript-free runtime secret injection path before direct API calls can run.

Forbidden response pattern:

- Do not say "You provide the secret", "paste it here", "send me the webhook secret", or any variant.
- Do not offer "read-only, ephemeral" chat pasting for `ATLAS_CLEANROOM_WEBHOOK_SECRET`, `MAXHERMES_CLEANROOM_WEBHOOK_SECRET`, or `MAXHERMES_CONTROL_PLANE_CLIENT_SECRET`.
- Do not ask Ahmad for a Notion internal integration token such as a `secret_...` value.
- Do not say "Do you have a Notion integration token I can use?"
- Do not say Matrix needs a Notion MCP before Atlas Notion is connected.
- Do not present pasting a secret into chat as one of the routes forward.
- If private auth is missing, use public status for status-only questions, use pairing flow for temporary private work, or ask Codex/operator to run the query through the Azure control plane.

Accepted environment variable names:

For the Azure MaxHermes control plane:

1. `MAXHERMES_CONTROL_PLANE_CLIENT_SECRET`
2. `ATLAS_MAXHERMES_CONTROL_PLANE_CLIENT_SECRET`

For the lower-level clean-room API fallback:

1. `ATLAS_CLEANROOM_WEBHOOK_SECRET`
2. `MAXHERMES_CLEANROOM_WEBHOOK_SECRET`

Temporary pairing token names:

1. `ATLAS_CLEANROOM_PAIRING_TOKEN`
2. `MAXHERMES_CLEANROOM_PAIRING_TOKEN`

If neither exists, fail closed with exactly:

`My hosted runtime is missing the clean-room webhook secret or short-lived pairing token, but the Azure endpoint exists.`

If the control-plane secret is missing, fail closed with exactly:

`My hosted runtime can reach the Azure MaxHermes control plane, but it does not have private control-plane authentication mounted.`

## Short-Lived Pairing

If MiniMax has no secure permanent secret mount, use a short-lived pairing token.

Start pairing:

```bash
python3 scripts/atlas_cleanroom_bridge.py pairing-start
```

Give Codex/operator the returned `pairingId` and `verificationCode`. After Codex approves it, exchange it:

```bash
python3 scripts/atlas_cleanroom_bridge.py pairing-exchange <pairingId> <verificationCode>
```

Then set the returned token only for the current session:

```bash
export ATLAS_CLEANROOM_PAIRING_TOKEN='<short-lived-token>'
```

Pairing tokens are temporary, scoped, and not replacements for a proper MiniMax hosted secret manager.

## Available Actions

Run the helper script from the skill root.

### Codex Operator Status

Use this when Ahmad asks whether MaxHermes is connected to Codex.

```bash
python3 scripts/atlas_cleanroom_bridge.py codex-operator-status
```

Correct interpretation:

- Codex is connected as the local engineering/operator surface through the Azure MaxHermes control plane.
- There is no clean-room Codex MCP server exposed through Matrix, claw-server, `/codex`, or `/invoke`.
- Do not probe Matrix MCP or claw-server routes to decide whether Codex is connected.
- If Matrix reports no `/codex` or `/invoke` route, that does not mean the Codex operator bridge is broken. It means Matrix is not the Codex bridge.
- The approved path is Codex/operator in `/Users/ahmadsulaiman/atlas-cleanroom` calling `https://atlas-maxhermes-control-plane.azurewebsites.net`, which forwards to `https://atlas-cleanroom-api.azurewebsites.net`.

### Codex Operator Request

Use this when Ahmad asks MaxHermes to send work to Codex/operator.

```bash
python3 scripts/atlas_cleanroom_bridge.py codex-request "tell Codex what needs to be done"
```

This sends an authenticated request to:

`POST https://atlas-maxhermes-control-plane.azurewebsites.net/codex/operator-request`

The control plane forwards it to the clean-room API, which writes a draft Notion ledger record for Codex/operator. This is a request handoff, not automatic local shell execution. Codex still decides and executes work only inside `/Users/ahmadsulaiman/atlas-cleanroom`.

### Control Plane Health

Use to verify hosted MaxHermes can reach the Azure-owned production control plane.

```bash
python3 scripts/atlas_cleanroom_bridge.py control-health
python3 scripts/atlas_cleanroom_bridge.py control-status
```

These calls are public read-only and do not require a secret.

### Control Plane Tool Status

Use this as the preferred production status path when `MAXHERMES_CONTROL_PLANE_CLIENT_SECRET` is mounted.

```bash
python3 scripts/atlas_cleanroom_bridge.py control-tool-status
```

If this returns `401` or the missing-auth message, say the hosted runtime can reach the Azure control plane but does not have private control-plane authentication mounted.

### Control Plane Knowledge Query

Use this as the preferred production knowledge path when `MAXHERMES_CONTROL_PLANE_CLIENT_SECRET` is mounted.

```bash
python3 scripts/atlas_cleanroom_bridge.py control-query "test clean-room knowledge connection"
```

This routes through the Azure MaxHermes control plane, then the clean-room API, then Notion/Onyx as allowed by the clean-room boundary.

### Tool Status

Use this lower-level clean-room API path before claiming that any tool is connected if the production control-plane secret is not mounted but a clean-room webhook secret or pairing token exists.

```bash
python3 scripts/atlas_cleanroom_bridge.py status
```

If the hosted runtime does not have `ATLAS_CLEANROOM_WEBHOOK_SECRET`, use the public read-only status fallback:

```bash
python3 scripts/atlas_cleanroom_bridge.py public-status
```

`public-status` never sends a secret and never returns missing secret/config names, source records, Notion content, Onyx results, or private data. It returns only sanitized connector counts plus configured/blocked connector IDs. Use it only for answering "what is connected?" or "what is blocked?" Private knowledge queries, Factory checks, control-plane sync, writes, and source retrieval still require the authenticated bridge.

Expected canonical status as of June 5, 2026:

- 24 total clean-room connectors
- 21 configured at the readiness layer
- 3 blocked pending fresh Key Vault values and smoke tests

Configured/readiness connectors:

`notion`, `mavis`, `maxhermes`, `maxclaw`, `factoryai`, `openrouter`, `openclaw`, `onyx`, `firecrawl`, `brave`, `outlook`, `slack`, `mem0`, `zep`, `pinecone`, `obsidian`, `wiki`, `screenpipe`, `box`, `filevine`, `memory`

Blocked connectors:

`leaddocket`, `domo`, `qbo`

### Notion Status

Use this when Ahmad asks whether Notion is connected or when the Matrix MCP server says it has no Notion tool.

```bash
python3 scripts/atlas_cleanroom_bridge.py notion-status
```

Correct interpretation:

- Notion is connected through the Atlas clean-room API, not through Matrix MCP.
- Matrix MCP does not need to have a Notion tool for Atlas Notion to be connected.
- Do not install a local Notion MCP to solve Atlas clean-room Notion.
- Do not ask Ahmad for a Notion `secret_...` token.
- Do not ask Ahmad for `ATLAS_CLEANROOM_WEBHOOK_SECRET`.
- For status-only answers, `notion-status` or `public-status` is enough.
- For Notion writes or Onyx-backed Notion ledger records, use `control-query`, `query`, or `codex-request` depending on which authenticated bridge is mounted.

Correct response when private auth is missing but Notion status is requested:

`Notion is configured in the Atlas clean-room. Matrix MCP does not expose Notion, but that is not the Atlas Notion bridge. Private Notion writes still require the authenticated Azure control-plane bridge or Codex/operator; I will not ask you to paste a Notion token or webhook secret in chat.`

### Knowledge Query

Use for questions that need Notion/Onyx memory or source-linked Atlas knowledge.

```bash
python3 scripts/atlas_cleanroom_bridge.py query "What tools are connected?"
```

For settlement, revenue, case, intake, finance, or dashboard questions:

1. Run `status` first.
2. If Filevine, LeadDocket, Domo, or QBO are blocked, say the relevant business source is not connected/indexed yet.
3. Do not imply Notion or Onyx are broken when the missing source system is actually Filevine, LeadDocket, Domo, or QBO.

### Factory Maintenance Check

Use for read-only Factory AI maintenance readiness.

```bash
python3 scripts/atlas_cleanroom_bridge.py factory
```

Factory AI remains a maintenance checker through the clean-room API. Do not give it raw Key Vault access or autonomous repair authority unless a later approval workflow exists.

### Control Plane Sync

Use when asked whether MaxHermes, Factory AI, OpenRouter, memory layers, or control routes are wired.

```bash
python3 scripts/atlas_cleanroom_bridge.py control
```

### Screenpipe Context Gate

Use when asked whether Screenpipe live context is wired. This command verifies the clean-room context gate only. It must not return screenshots, OCR text, transcripts, audio text, or memory writes.

```bash
python3 scripts/atlas_cleanroom_bridge.py screenpipe
```

## Response Rules

- State whether a tool is `configured`, `blocked`, or `not smoke-tested`.
- For Notion, first run `notion-status` or `public-status`; do not inspect Matrix MCP capability lists as the source of truth.
- Do not say a tool is fully connected unless the clean-room API returns a successful smoke test and a ledger write when applicable.
- Never expose secrets or raw authorization headers.
- Prefer concise operational answers with the next missing connector named clearly.
- If the script reports missing runtime secret, say that MiniMax needs a transcript-free mounted runtime secret or a short-lived pairing token; do not name secret values as something Ahmad should provide, and do not ask Ahmad to paste any secret into chat.
- If the runtime secret is missing and Ahmad only asks for connector status, run `public-status` and clearly say that private actions still require authenticated bridge access.
- If MiniMax offers only the agent-facing `secret` function with a plaintext `--value` argument, do not use it for this webhook secret. Recommend a platform secret mount, human-entered masked secret UI, or a future short-lived pairing flow instead.

Correct response when MaxHermes lacks private auth for a business question:

`I can reach the Azure MaxHermes control plane, but this hosted runtime does not have private control-plane authentication mounted. I will not ask you to paste secrets in chat. For this query, ask Codex/operator to run it through the Azure control plane, or start a short-lived pairing flow.`
