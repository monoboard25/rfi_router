# ⚖️ A-Governance-Agent (CEO Agent)

This directory contains the Node.js implementation of the **Governance Agent** (also known as the CEO Agent or Constitutional Auditor) for the Monoboard AI ecosystem.

## 🎯 Purpose

As defined in the Monoboard Phase 0 Build Spec, the Governance Agent is the central oversight mechanism for the decentralized agent fleet. While operational agents (like `rfi_router`, `bid_assist`) execute specific tasks, the Governance Agent ensures they operate within the bounds of the **Monoboard Agent Constitution**.

It is designed to use the `@azure/ai-projects` SDK to review agent outputs, analyze the observability logs, and flag behavioral drift.

## 🏗️ Architecture

- **Runtime:** Node.js
- **Orchestration:** Azure AI Project SDK (`@azure/ai-projects`)
- **Model:** `gpt-4o` (or designated Azure OpenAI deployment)
- **Role:** Read-only analysis. The Governance Agent reads the `agentruns` Azure Table and outputs markdown reports. It does not perform operational writes.

### Key Responsibilities

1. **Drift Detection:** Identifies when an agent's `resolution_path` begins relying too heavily on LLM inference instead of deterministic schema parsing.
2. **Escalation Monitoring:** Tracks escalation frequencies across the fleet (e.g., how often `bid_assist` flags $10k+ thresholds).
3. **Validator Analytics:** Summarizes validator failure rates to highlight poorly performing agents or overly strict rules.
4. **Constitution Compliance:** Ensures no agent is proposing writes outside its configured scope in the Permission Matrix.

## ⚙️ Setup & Configuration

### Prerequisites
- Node.js v18+
- Access to the Azure AI Project and Azure Table Storage containing the `agentruns` logs.

### Installation
```bash
cd A-Governance-Agent
npm install
```

### Environment Variables
Copy `.env.sample` to `.env` (or set these in your deployment environment):

```env
# Azure AI Studio configuration
AZURE_AI_PROJECT_CONNECTION_STRING="<your_project_connection_string>"
AZURE_OPENAI_DEPLOYMENT="gpt-4o" # Model deployment name

# Azure Table Storage (for reading agentruns)
AZURE_STORAGE_CONNECTION_STRING="<your_storage_connection_string>"
```

## 🚀 Running the Agent

To execute a manual audit run:
```bash
node index.js
```

### CI/CD Deployment
In production, the Governance Agent should be scheduled to run weekly via GitHub Actions or an Azure Logic App. It outputs a `scorecard.generate_markdown(metrics)` report that is posted to the Principal Owners for review.

## 🔗 Related Documentation
- `monoboard_phase0_build_spec.md` - Technical foundation for the validator and observability schema.
- `monoboard_agent_constitution.md` - The rules this agent is auditing against.
- `PROJECT_HANDOVER.md` - System architecture overview.
