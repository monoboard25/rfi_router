# Drift Resolution — Pending Decisions

**Status:** Open
**Created:** 2026-05-05
**Source:** `monoboard_matrix_schema_drift.md` §Decision queue
**Blocks:** Agent #1 (RFI Router) ship

Each decision below has a recommended default (engineering view) and the alternative options. Owners pick one and initial. Decisions take ~5 min each — engineering will implement the chosen path.

---

## D1 — Change Order: how to detect "new scope"?

**Owner:** Principal Owners (Abdiel B. Escoto, Luis W. Delgado) + CFO/Controller
**Trigger ID:** `co_new_scope`
**Today:** Rule references `output.is_new_scope` — field doesn't exist in `change_order.schema.json`. Rule never fires.

**Options:**
- **A.** Derive from existing `financials.reason_code == 'unforeseen_condition'`. Cheap. No schema change. Risk: conflates *unforeseen* with *new scope* — they aren't always the same (a discovered foundation issue is unforeseen but may be in original scope).
- **B.** Add explicit boolean `financials.is_new_scope` to schema. Agent's content extractor sets it. Most accurate, but adds an LLM-classification step and a new failure mode.

**Recommendation:** B. Scope creep is a financial control point worth its own field.

**Decision:** [ ] A   [ ] B   Initial: ________  Date: ________

---

## D2 — Change Order: where do `current_spend` and `budget_contingency` come from?

**Owner:** CFO/Controller
**Trigger ID:** `co_over_contingency`
**Today:** Rule references `output.current_spend + output.amount > output.budget_contingency`. Neither `current_spend` nor `budget_contingency` exists in any data source the agent currently reads.

**Options:**
- **A.** Pull from accounting/ERP system at agent runtime. Requires integration (Sage 100? QuickBooks? Procore? — name the system).
- **B.** Pull from a project-specific SharePoint list maintained manually by the PM. Lower fidelity, no integration, drift risk.
- **C.** Drop the rule. Rely on `co_amount_threshold` ($25k / 5%) only.

**Recommendation:** B for Phase 0 (manual list at `/sites/project-NNNN/Lists/BudgetTracker`); A for Phase 1 once an integration target is named.

**Decision:** [ ] A — system: ________   [ ] B   [ ] C   Initial: ________  Date: ________

---

## D3 — Safety Monitor: keyword scan vs severity-driven for critical incident?

**Owner:** Safety Officer
**Trigger ID:** `safety_critical_incident`
**Today:** Rule scans non-existent `output.incident_text` for OSHA-aligned keywords (fatality, fall, struck-by, electrocution, caught-in, hospitalization). Never fires.

**Options:**
- **A.** Keyword scan — concatenate `safety_signals[].observation` strings, check for OSHA keywords. Matches constitution intent. Risk: brittle — agent's narrative phrasing matters; "fell from ladder" matches, "tumbled off" doesn't.
- **B.** Severity-driven — fire when any `safety_signals[i].severity in ['high', 'critical']`. Deterministic. Risk: depends on the agent's severity assignment being well-calibrated.
- **C.** Both — fire on either condition.

**Recommendation:** C. Severity catches well-calibrated cases, keywords catch the cases where the agent under-rated severity. Defense in depth on a high-stakes rule.

**Decision:** [ ] A   [ ] B   [ ] C   Initial: ________  Date: ________

---

## D4 — Safety Monitor: how to flag OSHA-recordable?

**Owner:** Safety Officer
**Trigger ID:** `safety_osha_recordable`
**Today:** Rule references `output.is_potential_osha_recordable`. Field doesn't exist.

**Options:**
- **A.** Derive from `severity == 'critical' AND signal_type IN ('FALL_HAZARD', 'ELECTRICAL_HAZARD', 'PPE_VIOLATION')`. Engineering-cheap. Approximate.
- **B.** Add explicit boolean `safety_signals[i].is_potential_osha_recordable`. Agent applies OSHA criteria (29 CFR 1904) per signal. Most accurate, but requires the agent to encode OSHA's recordability test.

**Recommendation:** B. OSHA recordability has specific legal criteria (medical treatment beyond first aid, days away, restricted duty, etc.). Approximation by signal_type misses the medical-treatment leg entirely.

**Decision:** [ ] A   [ ] B   Initial: ________  Date: ________

---

## D5 — Safety Monitor: where does "repeat finding" detection live?

**Owner:** Principal Owners + Safety Officer
**Trigger ID:** `safety_repeat_finding`
**Today:** Rule references `output.is_repeat_finding_30d`. Field doesn't exist. Detection requires querying the past 30 days of `agentruns` for matching signal at the same project.

**Options:**
- **A.** Safety Monitor agent queries its own log on each run, sets the boolean. Adds latency and `agentruns` read scope to Safety Monitor's permission grants.
- **B.** Move the rule to CEO Agent (which already reads `agentruns` per Phase 0 spec). Safety Monitor stops emitting the field. CEO Agent flags trends weekly, not per-run.

**Recommendation:** B. Repeat-finding is a trend pattern, not a per-incident classification. CEO Agent is the right home for cross-run analysis.

**Decision:** [ ] A   [ ] B   Initial: ________  Date: ________

---

## D6 — Bid Assist: who owns the commitment classifier?

**Owner:** Lead Estimator
**Trigger IDs:** `bid_outbound_comm`, `bid_firm_commitment`, `bid_deadline_approaching`
**Today:** Rules reference `is_outbound_comm`, `contains_pricing_commitment`, `contains_schedule_commitment`, `contains_bond_amount`, `hours_to_deadline`, `is_complete`. None exist in `bid_assist.schema.json`.

**Options:**
- **A.** Bid Assist agent's content extractor populates all six fields per draft. Engineering builds + maintains the classifier (LLM prompt + regex hybrid).
- **B.** Estimating team manually flags via a SharePoint list field on each bid. Agent reads and copies. Lower automation, higher accuracy.
- **C.** Mix — `hours_to_deadline` + `is_complete` from bid metadata (deterministic); the four `contains_*` booleans from LLM extractor.

**Recommendation:** C. Deadline/completeness are structured facts. Commitment detection requires content reading, which is what LLMs are for.

**Decision:** [ ] A   [ ] B   [ ] C   Initial: ________  Date: ________

---

## D7 — CEO Agent: structural schema gap

**Owner:** Principal Owners (Abdiel B. Escoto, Luis W. Delgado)
**Trigger IDs (all CEO-scoped):** `ceo_scope_violation_alert`, `ceo_safety_trigger_change`, `ceo_insufficient_data`, `ceo_agent_disagreement`
**Today:** **Confirmed:** no `schemas/ceo_agent.schema.json` exists. CEO Agent outputs markdown via `scorecard.generate_markdown(metrics)`, not structured JSON. All four CEO escalation rules are dead.

**Options:**
- **A.** Author a CEO Agent schema. CEO joins the structured-output regime: emits both markdown (for humans) and JSON (for the validator chain). Brings CEO under same governance enforcement as the six operational agents.
- **B.** Exempt CEO from the validator chain. CEO is read-only over logs and writes only to the Agent Governance area. Constitution-level decision: do read-only agents need schema enforcement?
- **C.** Schema for the CEO's *recommendations only* (the writes that affect other agents — rule adjustments, Constitution changes). Markdown stays unstructured for the human-facing scorecard.

**Recommendation:** C. The dangerous CEO writes are recommendations to change other agents' behavior — those need schema-enforced governance. The scorecard markdown is observation, not action; doesn't need a schema.

**Decision:** [ ] A   [ ] B   [ ] C   Initial: ________  Date: ________

---

## Tracking

| # | Owner | Decided? | Decided value | Date |
|---|---|---|---|---|
| D1 | Principal Owners + CFO | ☐ | | |
| D2 | CFO/Controller | ☐ | | |
| D3 | Safety Officer | ☐ | | |
| D4 | Safety Officer | ☐ | | |
| D5 | Principal Owners + Safety Officer | ☐ | | |
| D6 | Lead Estimator | ☐ | | |
| D7 | Principal Owners | ☐ | | |

Once all 7 decided, engineering implements per `monoboard_matrix_schema_drift.md` resolution workflow. Each implementation PR closes one or more rows of the drift table and references back to the decision row here.

---

## Distribution

- **Principal Owners:** owns D1, D2 (jointly), D5, D7 — read whole doc
- **CFO/Controller:** D1, D2 — sections only
- **Safety Officer:** D3, D4, D5 — sections only
- **Lead Estimator:** D6 — section only

Suggested channel: post in `Teams → Agent Governance → Decisions` with `@` tag per row.
