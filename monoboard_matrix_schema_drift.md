# Escalation Matrix ↔ Schema Drift — Tracked Backlog

**Status:** Open
**Created:** 2026-05-04
**Owner:** TBD (Principal Owners + per-agent author)
**Related:** `validator/shared/mocks/escalation_matrix.json`, `schemas/*.schema.json`, `monoboard_phase0_build_spec.md` §3

---

## Background

The Phase 0 escalation validator (`validator/src/validators/escalation_validator.py`) evaluates rules in `escalation_matrix.json` against agent output. Rules use a DSL like `output.field > threshold`. Many rules currently reference fields that the corresponding agent's schema does **not** define — meaning the rule silently no-ops (missing attributes resolve to `None`, conditions evaluate falsy and never fire).

This is brittle: rules that look enforced are dead code, and audit logs claim escalation coverage that doesn't exist. Each row below must be resolved before that agent ships.

## Triage categories

- **A — Path-only fix.** The data exists in the schema; the rule expression just points at the wrong path. Cheap, no schema change.
- **B — Derivable.** Rule can be rewritten to compute the value from existing schema fields (often via a helper).
- **C — Schema gap.** The agent doesn't currently emit this field. Either add to schema (and agent code) or remove the rule.

## Drift table

| Agent | Trigger ID | Current expression refs | Schema reality | Category | Proposed fix |
|---|---|---|---|---|---|
| rfi_router | `rfi_unclassifiable_trade` | `output.classification.trade` | ✅ in schema | — | **Resolved 2026-05-04** |
| rfi_router | `rfi_no_response_48h` | `output.status`, `output.days_open` | `tracking_row.status` exists; `days_open` absent | A + C | Rewrite to `output.tracking_row.status`; add `tracking_row.days_open` (computed at agent runtime from `received_at`) |
| daily_report | `daily_missing_photos` | `output.logged_crew_hours`, `output.photo_count` | `crew_hours[].hours`, `field_evidence[]` | B | Helper `sum_crew_hours(output.crew_hours) > 0 AND len(output.field_evidence) == 0` |
| daily_report | `daily_safety_keywords` | `output.notes` | `narrative.summary`, `narrative.roadblocks` | A | `contains_any(output.narrative.summary, SAFETY_KEYWORDS) OR contains_any(output.narrative.roadblocks, SAFETY_KEYWORDS)` |
| change_order | `co_amount_threshold` | `output.amount`, `output.contract_value` | `financials.amount`, `financials.contract_value` | A | `output.financials.amount > 25000 OR output.financials.amount > (output.financials.contract_value * 0.05)` |
| change_order | `co_new_scope` | `output.is_new_scope` | absent; `financials.reason_code` exists | B or C | B: derive from `output.financials.reason_code == 'unforeseen_condition'` (decision needed: is reason_code the right proxy?). C if Principal Owners want explicit boolean. |
| change_order | `co_over_contingency` | `output.current_spend`, `output.budget_contingency` | absent | C | Add `financials.current_spend`, `financials.budget_contingency` to schema **and** to the change_order agent's output extraction logic |
| safety_monitor | `safety_critical_incident` | `output.incident_text` | `safety_signals[].observation`, `safety_signals[].severity` | B | Helper `signals_match_keywords(output.safety_signals, SAFETY_KEYWORDS)` OR severity-based: `any_severity(output.safety_signals, ['high', 'critical'])` — **decide: keyword match vs severity-driven** |
| safety_monitor | `safety_osha_recordable` | `output.is_potential_osha_recordable` | absent | B or C | B if derivable from `severity == 'critical' AND signal_type IN ('FALL_HAZARD','ELECTRICAL_HAZARD')`. C if Safety Officer wants explicit boolean per OSHA criteria. |
| safety_monitor | `safety_repeat_finding` | `output.is_repeat_finding_30d` | absent; requires history lookup | C | Schema gap. Agent must query past 30 days of `agentruns` for matching `signal_type` at same project. Either add field at agent or move rule to CEO Agent (which already reads logs). |
| bid_assist | `bid_outbound_comm` | `output.is_outbound_comm` | absent | C | Constitution forbids outbound. Field should always be `false`; rule is a tripwire. Either add field or rewrite as scope check (`writes_proposed[].target_scope` must not include external). |
| bid_assist | `bid_firm_commitment` | `output.contains_pricing_commitment`, `contains_schedule_commitment`, `contains_bond_amount` | absent | C | Add three boolean fields populated by agent's content classifier. Without them, rule cannot fire — bid drafts could leak commitments unnoticed. |
| bid_assist | `bid_deadline_approaching` | `output.hours_to_deadline`, `output.is_complete` | absent | C | Add both. `hours_to_deadline` from bid metadata, `is_complete` from checklist completeness ratio. |
| ceo_agent | `ceo_scope_violation_alert` | `output.event_type` | TBD — verify against `ceo_agent.schema.json` (not yet authored?) | C | Confirm CEO schema exists and includes `event_type`. If missing schema, **schema gap is structural**: CEO Agent has no output schema yet. |
| ceo_agent | `ceo_safety_trigger_change` | `output.recommendation_type`, `output.target_agent` | TBD | C | Same as above |
| ceo_agent | `ceo_insufficient_data` | `output.days_of_logs_available`, `output.has_log_gap` | TBD | C | Same as above |
| ceo_agent | `ceo_agent_disagreement` | `output.event_type` | TBD | C | Same as above |
| all (general) | `general_stale_data` | `output.source_artifact_age_days`, `output.freshness_threshold_days` | `sources_cited[].freshness_ok` exists (boolean) | B | Rewrite to `any_stale(output.sources_cited)` helper checking `freshness_ok == false` |
| all (general) | `general_conflicting_sources` | `output.has_conflicting_sources` | absent | C | Add boolean OR derive from agent during retrieval phase |
| all (general) | `general_tool_failure` | `output.tool_failure_count` | `resolution_path_attempts[].outcome` exists | B | Helper `count_failed_attempts(output.resolution_path_attempts) > 1` |

## Summary by agent

- **rfi_router:** 1 of 2 rules aligned. 1 path+gap (days_open).
- **daily_report:** 0 of 2 aligned. Both fixable as B (helpers + path).
- **change_order:** 0 of 3 aligned. 1 path-only (amount/contract_value), 2 schema gaps.
- **safety_monitor:** 0 of 3 aligned. 1 derivable (B), 2 require Safety Officer input (B vs C).
- **bid_assist:** 0 of 3 aligned. All three are schema gaps requiring agent-side classification fields.
- **ceo_agent:** 0 of 4 aligned. **Blocked on whether CEO schema exists at all.**
- **general (all):** 0 of 3 aligned. 2 derivable, 1 schema gap.

**Total:** 17 of 20 escalation rules currently dead. 1 fixed. Remaining 16: ~6 are path-only or simple derivations; ~10 require schema changes or human decisions.

## Required helpers (if Category B fixes adopted)

To support the proposed expressions, the escalation validator's `functions` dict needs:

- `sum_crew_hours(crew_hours)` → `sum(h.hours for h in crew_hours)`
- `any_severity(signals, levels)` → `any(s.severity in levels for s in signals)`
- `signals_match_keywords(signals, keywords)` → checks all `observation` strings
- `any_stale(sources_cited)` → `any(s.freshness_ok == false for s in sources_cited)`
- `count_failed_attempts(attempts)` → `sum(1 for a in attempts if a.outcome == 'fail')`

These belong in `validator/src/validators/escalation_validator.py` — registered alongside the existing `contains_any`.

## Decision queue (human)

> Each decision is broken out with options and a recommended default in `monoboard_drift_decisions.md`. Owners initial that doc directly.

1. **Change Order `co_new_scope`:** Use `reason_code == 'unforeseen_condition'` as proxy, or add explicit `is_new_scope` boolean? — Principal Owners + CFO
2. **Change Order `co_over_contingency`:** Where do `current_spend` and `budget_contingency` come from at agent runtime? Project's accounting system, ERP, manual? — CFO/Controller
3. **Safety Monitor `safety_critical_incident`:** Keyword scan over observations vs severity-driven? Constitution implies keyword (preserves OSHA-aligned terms), but severity is more deterministic. — Safety Officer
4. **Safety Monitor `safety_osha_recordable`:** Derive from severity+type or require explicit OSHA-criteria boolean? — Safety Officer
5. **Safety Monitor `safety_repeat_finding`:** Move to CEO Agent (history-aware) or have Safety Monitor query its own log? — Both leads
6. **Bid Assist commitments:** Who owns the content classifier that populates the three booleans? — Lead Estimator
7. **CEO Agent schema:** Does it exist? If not, this is a structural Phase 0 gap. — Both leads

## Resolution workflow

For each row:
1. Decide category (A/B/C) and assign owner.
2. If A: PR updates `escalation_matrix.json` only. No schema/agent change.
3. If B: PR adds helper to `escalation_validator.py` + updates matrix expression. Add unit test that fires the rule against a fixture.
4. If C: PR adds field to schema, agent code populates it, fixtures updated, matrix expression updated, unit test added.

Each row closed by linking the resolving PR + a smoke test result showing the rule now fires when expected.

## Acceptance for closing this doc

- 0 of N rules silently no-op against a representative valid fixture for each agent.
- Each rule has at least one fixture (valid + invalid pair) demonstrating fire vs not-fire.
- `monoboard_phase0_build_spec.md` §3 escalation checklist references this doc as resolved.

---

*Owner reviews this monthly until empty. Each closed row migrates to a CHANGELOG entry.*
