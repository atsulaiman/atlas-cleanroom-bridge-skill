---
name: atlas-cleanroom-bridge
description: Use this skill when Ahmad or MaxHermes asks to check Atlas clean-room tool status, query Atlas knowledge through Notion/Onyx, run a Factory AI maintenance readiness check, or sync the MaxHermes control plane. Triggers include "what tools are connected", "check clean-room status", "query Atlas knowledge", "ask Onyx", "check Notion", "settlements", "cases", "revenue", "intake", "projects", "commitments", "meetings", "run Factory maintenance", and "control-plane sync". Do not use this skill for generic web research or local file edits that do not need Atlas clean-room state.
---

# Atlas Clean-Room Bridge

Use this skill to let MaxHermes/Mavis call the Atlas Clean-Room API directly instead of asking Ahmad to relay status between Codex, Notion, Onyx, Factory AI, and MiniMax.

## Boundary

Only use this base URL:

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

Accepted environment variable names:

1. `ATLAS_CLEANROOM_WEBHOOK_SECRET`
2. `MAXHERMES_CLEANROOM_WEBHOOK_SECRET`

If neither exists, fail closed with exactly:

`My hosted runtime is missing the clean-room webhook secret, but the Azure endpoint exists.`

## Available Actions

Run the helper script from the skill root.

### Tool Status

Use before claiming that any tool is connected.

```bash
python3 scripts/atlas_cleanroom_bridge.py status
```

Expected canonical status as of June 4, 2026:

- 23 total clean-room connectors
- 9 configured at the readiness layer
- 14 blocked pending fresh Key Vault values and smoke tests

Configured/readiness connectors:

`notion`, `mavis`, `maxhermes`, `maxclaw`, `factoryai`, `onyx`, `obsidian`, `wiki`, `memory`

Blocked connectors:

`openrouter`, `openclaw`, `firecrawl`, `brave`, `outlook`, `slack`, `mem0`, `zep`, `pinecone`, `box`, `filevine`, `leaddocket`, `domo`, `qbo`

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

## Response Rules

- State whether a tool is `configured`, `blocked`, or `not smoke-tested`.
- Do not say a tool is fully connected unless the clean-room API returns a successful smoke test and a ledger write when applicable.
- Never expose secrets or raw authorization headers.
- Prefer concise operational answers with the next missing connector named clearly.
- If the script reports missing runtime secret, say that MiniMax needs a secure secret/environment variable for `ATLAS_CLEANROOM_WEBHOOK_SECRET`; do not ask Ahmad to paste it into chat.
- If MiniMax offers only the agent-facing `secret` function with a plaintext `--value` argument, do not use it for this webhook secret. Recommend a platform secret mount, human-entered masked secret UI, or a future short-lived pairing flow instead.
