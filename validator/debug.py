from validators.escalation_validator import EscalationValidator
validator = EscalationValidator()
output = {"amount": 10000, "contract_value": 500000, "is_new_scope": False, "current_spend": 10000, "budget_contingency": 50000, "source_artifact_age_days": 1, "freshness_threshold_days": 7}
res = validator.validate("change_order", output)
print(res)
