# 🏗️ Monoboard Agent Governance: Project Handover Documentation

This document serves as the master guide for the Monoboard AI agent ecosystem. It provides the technical context, architecture, and maintenance procedures for the platform.

## 1. System Architecture

The Monoboard ecosystem follows a **Centralized Validator / Decentralized Agent** architecture.

### The Validator Chain (`/validator`)
The "Constitution" of the system. Every agent must call this chain before performing any external "write" operation.
- **Stage 1: Schema**: Validates the agent's output JSON against a strict schema.
- **Stage 2: Scope**: Verifies the agent has permission to write to the target SharePoint/Teams URI.
- **Stage 3: Naming**: Enforces naming conventions (e.g., `YYYY-MM-DD-RPT-...`).
- **Stage 4: Escalation**: Halts writes and reroutes to human review if thresholds (like $10k) are exceeded.

### The Agent Fleet (`/agents`)
Six specialized agents implemented as Python Azure Functions:
1. **RFI Router**: Routes RFIs to trade-specific folders.
2. **Change Order**: Extracts financial impacts and enforces $10k thresholds.
3. **Daily Report**: Synthesizes field data into narrative reports.
4. **Safety Monitor**: Scans for OSHA hazards and PPE violations.
5. **Bid Assist**: Drafts takeoff checklists from bid packages.
6. **Onboarding Agent**: Initializes new project sites with governance files.

## 2. Governance Logic

### The Permission Matrix
Located at: `/sites/<job_number>/governance/permission_matrix.json`
Maps trade prefixes (ELEC, PLUM) to target folder URIs.

### The Escalation Matrix
Located at: `/sites/<job_number>/governance/escalation_matrix.json`
Defines financial and safety triggers that halt automated writes.

### Observability
All agent runs are logged to the `agentruns` Azure Table.
- **Resolution Path**: `schema_parse` (deterministic) vs `inference` (LLM).
- **CEO Agent**: Monitors these logs to detect "drift" and anomalies.

## 3. Operations & Maintenance

### Adding a New Agent
1. Create a new directory in `agents/`.
2. Draft a structured output schema in `schemas/`.
3. Integrate the `ValidatorClient`.
4. Add the agent to the matrix in `.github/workflows/agents-ci-cd.yml`.

### Updating the Constitution
To update global rules:
1. Modify the `monoboard_agent_constitution.md`.
2. Update the `validator` logic in `/validator/src/validators/`.
3. Increment the `constitution_version` in all agents.

### Deployment (CI/CD)
The system uses **GitHub Actions with OIDC**. No passwords or client secrets are stored in GitHub.
- **Validator CI/CD**: Deploys the governance brain.
- **Agents CI/CD**: Deploys the entire fleet in parallel.

## 4. Open Tracked Backlog

- **Escalation Matrix ↔ Schema drift** — `monoboard_matrix_schema_drift.md`. 19 of 20 escalation rules reference fields that don't exist in the corresponding agent schemas; rules silently no-op. Must be resolved before Agent #1 (RFI Router) ships. Includes 7 human decisions queued for CFO, Safety Officer, Lead Estimator, Principal Owners.

## 5. Emergency Procedures

### The Kill Switch
If an agent behaves unexpectedly:
1. Trigger the manual **Kill Switch** (setting the `KILL_SWITCH_ACTIVE` flag in Azure App Configuration).
2. All agents will immediately halt all "writes" and reroute to the `Review Queue`.
3. Follow the instructions in `monoboard_kill_switch_runbook.md`.

---
**Status**: Production Ready
**Version**: 1.2.0
**Maintainer**: Monoboard AI Team
