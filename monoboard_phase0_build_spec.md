# Monoboard AI Agents — Phase 0 Build Spec

**Document:** Foundation specs required before Agent #1 ships
**Version:** 1.0
**Companion to:** `monoboard_agent_constitution.md` v1.2
**Owners:** Abdiel B. Escoto, Luis W. Delgado

---

## Purpose

The Constitution defines *what* the system must do. This spec defines *how* the foundation is built so the Constitution's rules are actually enforced rather than aspirational.

Three deliverables, in build order:

1. **Platform choice** — pick the runtime before writing code
2. **Observability log schema** — every agent writes here from its first run
3. **Validator chain** — no agent writes to production without passing

A checklist at the end tracks Phase 0 to completion.

---

## 1. Platform Recommendation & Decision Matrix

### Recommendation

**Power Automate + Azure OpenAI + Azure Functions**, hosted in your M365 tenant.

This is the only realistic choice that satisfies all four of: (a) native M365 integration for SharePoint, Teams, OneDrive triggers and writes; (b) flexible enough to implement the validator chain as external code; (c) maintainable by a small team without dedicated DevOps; (d) kill-switch enforceable at platform and identity layers.

### Decision matrix

| Criterion                              | Copilot Studio              | **Power Automate + Azure OpenAI** | Custom (Graph API + Azure Functions) |
|----------------------------------------|-----------------------------|-----------------------------------|--------------------------------------|
| Time to Agent #1 running               | ~2 weeks                    | **~3–4 weeks**                    | ~8–10 weeks                          |
| Handles structured JSON outputs        | Limited                     | **Strong**                        | Full control                         |
| External validator chain               | Hard — architecture fights it | **Clean — call Azure Function**  | Native                               |
| Scope enforcement granularity          | Coarse (bot-level)          | **Per-flow + per-connector**      | Per-call                             |
| Kill switch granularity                | Disable bot                 | **Disable flow + revoke account** | Full control                         |
| Logging to custom store                | Limited (Dataverse)         | **Direct to Azure Table / Log Analytics** | Full control              |
| Cost at expected volume (<500 runs/day)| Subscription-based, predictable | **~$50–200/mo total**         | ~$100–300/mo + eng time              |
| Maintainability by 2-person team       | Good                        | **Good**                          | Requires a dedicated engineer        |
| Constitution compliance (all pillars)  | Partial                     | **Full**                          | Full                                 |

### Why not Copilot Studio

The validator chain is the blocker. Copilot Studio's architecture assumes the bot owns its end-to-end flow — inserting a gate that halts a write pending external schema validation fights the platform. You'd end up writing shims that negate the low-code advantage. Good for a customer-service bot; wrong shape for what's being built here.

### Why not full custom

Overkill for the current team. Custom means managing: Azure Functions deployment, Graph API authentication, webhook registrations, retry logic, connector equivalents — all things Power Automate handles natively. Revisit if and when the system outgrows Power Automate's concurrency or connector limits (years away at current scope).

### Stack summary

- **Triggers:** Power Automate flows — SharePoint file events, Teams messages, scheduled runs
- **Reasoning:** Azure OpenAI (GPT-4-class model for RFI Router, Daily Report, Bid Assist; smaller/cheaper model for routing and classification tasks)
- **Validators:** Azure Functions (Node.js or Python) — one function app, one endpoint per validator
- **Logs:** Azure Table Storage for structured agent runs; Azure Blob for larger payloads (reports, draft documents)
- **Config (Permission Matrix, thresholds, keyword lists):** SharePoint list in `Company Intranet → Agent Governance` — editable by Principal Owners, read by all agents and validators
- **Identity:** Dedicated service account per agent, each with minimum scoped Graph API permissions per the Permission Matrix
- **Kill switch:** Power Automate flow disable (per-agent) + service account disable in Entra ID (per-agent or bulk)

### Open questions to resolve before build

- Azure subscription — new or existing?
- Azure OpenAI model region availability and deployment limits in your tenant
- Entra ID service account creation policy — who approves new accounts?
- SharePoint governance — do the project sites already exist or are they created on-demand by Bid Assist?

---

## 2. Observability Log Schema

Every agent writes one log record per run. The CEO Agent reads these records — nothing else. No operational content is logged here, only operational metadata.

### Storage

- **Primary:** Azure Table Storage, table name `agentruns`
- **Partition key:** `agent_id` (enables fast per-agent queries)
- **Row key:** `run_id` (UUID v4, reverse-timestamp prefix for recency queries: `{maxTimestamp - runTimestamp}_{uuid}`)
- **Retention:** 24 months hot, then archive to Blob cold storage. Never delete — audit trail.
- **Write path:** End of Agent Loop step 8; a single `PUT` to Azure Table. Must be fire-and-forget with a retry queue — logging failure must not fail the agent run, but missed logs must land eventually.

### Schema (JSON representation; stored as flat columns in Azure Table)

```json
{
  "run_id": "uuid-v4",
  "agent_id": "rfi_router | daily_report | change_order | safety_monitor | bid_assist | ceo_agent",
  "agent_version": "1.0.0",
  "constitution_version": "1.2",

  "timestamp_start": "2026-04-19T14:32:11Z",
  "timestamp_end": "2026-04-19T14:32:14Z",
  "latency_ms": 3142,

  "trigger": {
    "type": "file_event | message_event | schedule | event_driven",
    "source_uri": "https://{tenant}.sharepoint.com/sites/project-2401/...",
    "payload_hash": "sha256:abc123..."
  },

  "resolution_path": "schema_parse | deterministic_tool | retrieval | inference",
  "resolution_path_attempts": [
    { "step": "schema_parse", "outcome": "success | fail | skipped" },
    { "step": "deterministic_tool", "outcome": "success | fail | skipped" },
    { "step": "retrieval", "outcome": "success | fail | skipped" },
    { "step": "inference", "outcome": "success | fail | skipped" }
  ],

  "sources_cited": [
    {
      "type": "sp_file | sp_list_item | teams_message | od_path",
      "uri": "https://...",
      "last_modified": "2026-04-18T09:00:00Z"
    }
  ],

  "writes_performed": [
    {
      "target_scope": "teams_project_channel | sp_project_site | sp_finance | ...",
      "target_uri": "https://...",
      "write_type": "create | update | post | list_add",
      "validator_pass": true
    }
  ],

  "escalations_fired": [
    {
      "trigger_id": "change_order_amount_threshold",
      "destination": "teams://.../project-channel",
      "halted_write": true,
      "payload_summary": "CO amount $47,500 exceeds $25,000 threshold"
    }
  ],

  "validator_results": {
    "schema": "pass | fail | not_run",
    "scope": "pass | fail | not_run",
    "naming": "pass | fail | not_applicable",
    "escalation": "pass | fail"
  },

  "tokens": {
    "model": "gpt-4-turbo-2024-04-09 | gpt-4o-mini | ...",
    "input": 1842,
    "output": 312,
    "cost_usd_estimate": 0.0421
  },

  "outcome": "completed_with_write | completed_no_write | escalated | halted_validation | halted_error",

  "error": null
}
```

### Field notes

- **`run_id`** — generated at trigger, threaded through the whole run, also logged in Teams posts and SharePoint writes so a user can trace any artifact back to its run
- **`agent_version`** and **`constitution_version`** — together these identify the exact behavior that produced the output. Critical for post-hoc review when behavior changes.
- **`resolution_path`** — the *final* path that produced the answer. **`resolution_path_attempts`** — the full sequence tried. An agent that always lands on `inference` is a signal the schema is too loose or parse rules are wrong.
- **`sources_cited`** stores URIs only, not content. The CEO Agent can count citations and check freshness without reading any project data.
- **`payload_hash`** — SHA256 of the trigger payload. Enables dedup detection and idempotency checks without storing the payload itself.
- **`tokens.cost_usd_estimate`** — computed locally using the model's published rate card, not from Azure billing. Close enough for monthly trend reports.

### What is NOT logged here

- File contents, message contents, report drafts
- User PII beyond what's in URIs
- Contract amounts, bid pricing, cost figures (these live in the operational systems, cited by URI only)
- Model raw completions (debugging only — stored separately in a debug log with shorter retention)

### CEO Agent query patterns

The CEO Agent is the only consumer of this table. Its standard queries:

| Query                                                          | Shape                                                                    |
|----------------------------------------------------------------|--------------------------------------------------------------------------|
| Weekly throughput per agent                                    | `PartitionKey eq 'rfi_router' and timestamp_start ge {7d ago}`           |
| Validator failure rate                                         | Group by `validator_results.*`, count `fail` / total                     |
| Escalation frequency by trigger_id                             | Group by `escalations_fired[].trigger_id`                                |
| Resolution-path drift (inference rising over time)             | Count `resolution_path eq 'inference'` week-over-week per agent          |
| Cost trend                                                     | Sum `tokens.cost_usd_estimate` grouped by week and agent                 |
| Latency outliers                                               | `latency_ms ge 10000` per agent                                          |

All queries hit the partition key first. No full-table scans.

---

## 3. Validator Chain Specification

Every agent write passes through this chain. Implemented as one Azure Function app with four endpoints. Agents call the chain via a single orchestrator endpoint that invokes the four validators in order and short-circuits on first failure.

### Endpoint contract (orchestrator)

```
POST /validate
Request:
{
  "run_id": "uuid",
  "agent_id": "rfi_router",
  "agent_version": "1.0.0",
  "output": { ... agent's structured output ... },
  "proposed_writes": [
    { "target_uri": "https://...", "target_scope": "teams_project_channel", "write_type": "post" }
  ],
  "proposed_filenames": [ "2401-RFI-ElectricalLayout-v1.pdf" ]
}

Response:
{
  "pass": false,
  "first_failure": "scope",
  "results": {
    "schema":     { "pass": true },
    "scope":      { "pass": false, "violations": [...] },
    "naming":     { "pass": null, "reason": "not_run_due_to_earlier_failure" },
    "escalation": { "pass": null, "reason": "not_run_due_to_earlier_failure" }
  }
}
```

Agents do not proceed with any write if `pass` is `false`. The validator response is itself logged as part of `validator_results` in the agent run log.

### Validator 1 — Schema

**Purpose:** Agent output conforms to the JSON schema registered for that agent.

**Schema storage:** `SharePoint → Company Intranet → Agent Governance → Schemas → {agent_id}.schema.json`. Versioned with the agent.

**Logic:** Standard JSON Schema validation (Ajv for Node.js, `jsonschema` for Python).

**Output:**
```json
{ "pass": false, "errors": [
  { "field": "routing.assigned_to", "message": "required property missing" },
  { "field": "priority", "message": "value 'critical' not in enum [low, medium, high]" }
]}
```

**Test cases (minimum):** valid output → pass; missing required field → fail; wrong type → fail; extra field → fail or warn depending on schema `additionalProperties` setting.

### Validator 2 — Scope

**Purpose:** Every proposed write targets a scope the agent is granted in the Permission Matrix.

**Config source:** Permission Matrix as a SharePoint list:
```
Columns: agent_id | scope_id | access (R | W | R/W)
```

**Logic:**
1. For each `proposed_write`, resolve `target_uri` → `scope_id` using a URI-to-scope mapping table (e.g., any URI under `/sites/project-*/` → `sp_project_site`).
2. Look up `(agent_id, scope_id)` in the Permission Matrix.
3. Confirm access is `W` or `R/W` for write operations.
4. Apply conditional grants (footnotes in the Matrix — e.g., Change Order to SP Finance is gated by escalation).

**Output:**
```json
{ "pass": false, "violations": [
  { "target_uri": "https://.../sites/finance/...", "scope_id": "sp_finance",
    "access_required": "W", "access_granted": "R", 
    "conditional_gate": "change_order_amount_threshold not yet approved" }
]}
```

**Critical property:** The scope validator is the *only* place the Permission Matrix is enforced at runtime. Do not duplicate the matrix into agent prompts — always fetch fresh at validation time so Principal Owner updates propagate immediately.

### Validator 3 — Naming

**Purpose:** Any filename the agent generates conforms to the naming schema.

**Logic:** Apply regex from Constitution Pillar II:
- Project files: `^\d{4}-(DWG|RFI|SUB|CO|RPT|PHO|CON)-[A-Za-z0-9]+(?:-\d{8})?-v\d+$`
- Company files: `^(HR|FIN|SAF|OPS|EST|LEG)-(POL|RPT|FRM|TMP|LOG|CRT)-[A-Za-z0-9]+-\d{4}$`

Route selection is automatic: filenames containing a 4-digit numeric prefix use the project regex; those starting with a department code use the company regex.

**Output:**
```json
{ "pass": false, "violations": [
  { "filename": "RFI_Electrical.pdf", "reason": "no job number; spaces/underscores instead of hyphens" }
]}
```

**`not_applicable` result:** returned when the agent proposes no new filenames in this run (e.g., posting to Teams only).

### Validator 4 — Escalation

**Purpose:** No write proceeds if the output crosses an escalation threshold.

**Config source:** Escalation Matrix as a SharePoint list:
```
Columns: agent_id | trigger_id | condition_expression | destination | halts_write (bool)
```

`condition_expression` uses a small constrained DSL — e.g., `output.amount > 25000 OR output.amount > output.contract_value * 0.05`. A tiny evaluator in the Azure Function runs these against the agent output.

**Logic:**
1. Load all escalation rows for `agent_id`.
2. Evaluate each `condition_expression` against the agent output.
3. If any fires and `halts_write` is true, mark the run as escalated and fail validation.
4. If a trigger fires but `halts_write` is false (e.g., "flag in scorecard"), note it but allow the write.

**Output:**
```json
{ "pass": false, "triggers_fired": [
  { "trigger_id": "change_order_amount_threshold",
    "destination": "teams_project_channel_pm_exec",
    "halts_write": true,
    "condition_matched": "output.amount=47500 > 25000" }
]}
```

### Chain behavior

- **Order is fixed:** schema → scope → naming → escalation. Cheapest and most-structural checks first.
- **Short-circuit on fail:** subsequent validators don't run if an earlier one fails. Saves compute and makes failure attribution clear.
- **Single source of truth:** Permission Matrix, naming regex, and Escalation Matrix live in SharePoint and are read by validators at invocation time. No caching beyond a 60-second in-memory cache to handle bursts.
- **No agent-side validation.** Agents do not run their own schema checks or scope checks before calling the validator. Duplicate validation logic drifts; centralized logic doesn't.

### Implementation notes

- **Language:** Python (`jsonschema`, `simpleeval` for the escalation DSL) or Node.js (`ajv`, `expr-eval`). Either is fine — pick what your dev is fastest in.
- **Cold-start:** Azure Functions Consumption Plan works for <500 runs/day. Premium Plan only if latency becomes a Constitution issue (it won't at current scope).
- **Auth:** Validators accept calls only from known Power Automate flow identities. Managed Identity authentication preferred over shared keys.
- **Testability:** The validator chain is pure — given the same inputs and config, same outputs. Unit tests per validator, integration test for the chain, both run on every config change.

---

## 4. Phase 0 Checklist

Before Agent #1 (RFI Router) begins build, every item below must be `Done`.

### Platform setup

- [ ] Azure subscription confirmed, billing owner named
- [ ] Azure OpenAI deployment provisioned in target region, model access confirmed
- [ ] Power Automate premium licenses confirmed for service accounts
- [ ] Azure Functions app provisioned (empty, ready to deploy)
- [ ] Azure Table Storage account provisioned, `agentruns` table created

### Identity & access

- [ ] Service accounts created in Entra ID:
  - [ ] `svc-agent-rfi-router@monoboard.com`
  - [ ] `svc-agent-daily-report@monoboard.com`
  - [ ] `svc-agent-change-order@monoboard.com`
  - [ ] `svc-agent-safety-monitor@monoboard.com`
  - [ ] `svc-agent-bid-assist@monoboard.com`
  - [ ] `svc-agent-ceo@monoboard.com`
- [ ] Kill switch procedure documented and bookmarked for both Principal Owners (phone-accessible)
- [ ] Emergency break-glass process: who disables service accounts if both Principal Owners unreachable?

### Governance artifacts in SharePoint

- [ ] `Company Intranet → Agent Governance` site created
- [ ] `Permission Matrix` list created, populated from Constitution Pillar I
- [ ] `Escalation Matrix` list created, populated from Constitution §Escalation
- [ ] `Schemas` document library created (empty — populated as agents are built)
- [ ] `Incidents` document library created
- [ ] `Kill Switch Drills` list created
- [ ] `Delegation Register` list created — who holds each role (@PM, @SafetyOfficer, @Estimator, etc.)

### Thresholds & lists (require human decisions, not engineering)

- [ ] Change Order: confirm or replace the `$25k / 5% of contract value` threshold with the actual number — **Principal Owners + CFO/Controller**
- [ ] Safety Monitor: finalize critical keyword list — **Safety Officer**
- [ ] Bid Assist: confirm "draft only, no external send" — **Principal Owners + lead estimator**
- [ ] Daily Report: define field-photo and crew-hours data sources — **Operations lead**
- [ ] Freshness thresholds per agent (default 7 days) — **Principal Owners**

### Validator chain

- [ ] Language chosen (Python or Node.js)
- [ ] Orchestrator endpoint deployed and reachable from Power Automate
- [ ] Schema validator implemented; unit tests pass
- [ ] Scope validator implemented; reads Permission Matrix from SharePoint; unit tests pass
- [ ] Naming validator implemented; regex matches Constitution; unit tests pass
- [ ] Escalation validator implemented; DSL evaluator supports the required expressions; unit tests pass
- [ ] **Escalation Matrix ↔ Schema drift resolved** — see `monoboard_matrix_schema_drift.md`. 19 of 20 rules currently dead-code; cannot ship Agent #1 with silently no-op rules.
- [ ] End-to-end integration test against a sample RFI Router output
- [ ] Managed Identity auth configured

### Observability

- [ ] Log schema finalized and documented
- [ ] Sample log records written and queried successfully
- [ ] Retention policy set (24 months hot, then archive)
- [ ] CEO Agent's six standard queries verified to return in <2 seconds on sample data

### Naming enforcement

- [ ] Decision made: SharePoint content types vs. Power Automate rename flow vs. pre-check-only
- [ ] Chosen mechanism deployed on the pilot project site (the one RFI Router will run against first)
- [ ] Non-conforming files route to the triage channel as designed

### Kill switch

- [ ] Per-agent flow disable procedure tested for each service account
- [ ] Entra ID service account disable procedure tested
- [ ] Level 1 kill drill run successfully (target: Daily Report — not yet built, but the disable procedure is testable against the empty service account)
- [ ] First quarterly drill scheduled on calendar

---

## What "done with Phase 0" unlocks

When this checklist is complete, RFI Router can be built against a foundation that enforces the Constitution rather than assuming it. Specifically:

- An agent that tries to write outside scope **cannot succeed** — the scope validator rejects it.
- An agent whose output drifts from the schema **cannot write** — the schema validator rejects it.
- An agent that misbehaves **can be stopped in under 60 seconds** — the kill switch works.
- The CEO Agent will have real data to analyze from Day 1 of Agent #1 — not retrofitted later.

Phase 0 is roughly 2–3 weeks of focused work for a competent M365/Azure developer. It is the single highest-leverage investment in the entire rollout — every shortcut taken here compounds into operational pain during agent rollout.

---

## Open items for the next session

- Draft the RFI Router JSON schema (first agent to be built — defines what "Phase 1" starts with)
- Write the Permission Matrix and Escalation Matrix as SharePoint list templates (.xml or .json for import)
- Define the URI-to-scope mapping table used by the scope validator
- Kill switch implementation runbook (the platform-specific how-to, linked from the Constitution)

---

*monoboard.ai — Agent Governance · Phase 0 Build Spec · v1.0*
