from validators.schema_validator import SchemaValidator
from validators.scope_validator import ScopeValidator
from validators.naming_validator import NamingValidator
from validators.escalation_validator import EscalationValidator

class ValidatorOrchestrator:
    def __init__(self):
        self.schema_validator = SchemaValidator()
        self.scope_validator = ScopeValidator()
        self.naming_validator = NamingValidator()
        self.escalation_validator = EscalationValidator()
        
    def execute_chain(self, run_id: str, agent_id: str, output: dict, proposed_writes: list, proposed_filenames: list) -> dict:
        results = {}
        
        # 1. Schema Validation
        results["schema"] = self.schema_validator.validate(agent_id, output)
        if not results["schema"].get("pass", False):
            return {"pass": False, "first_failure": "schema", "results": results}
            
        # 2. Scope Validation
        results["scope"] = self.scope_validator.validate(agent_id, proposed_writes)
        if not results["scope"].get("pass", False):
            return {"pass": False, "first_failure": "scope", "results": results}
            
        # 3. Naming Validation
        results["naming"] = self.naming_validator.validate(proposed_filenames)
        if results["naming"].get("pass") is False:
            return {"pass": False, "first_failure": "naming", "results": results}
            
        # 4. Escalation Validation
        results["escalation"] = self.escalation_validator.validate(agent_id, output)
        if not results["escalation"].get("pass", False):
            return {"pass": False, "first_failure": "escalation", "results": results}
            
        return {"pass": True, "results": results}
