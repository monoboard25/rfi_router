import os
import json
from simpleeval import EvalWithCompoundTypes, NameNotDefined, AttributeDoesNotExist

from graph_client import SharePointListFetcher

class EscalationValidator:
    def __init__(self, mocks_dir: str = None):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        self.graph_fetcher = SharePointListFetcher()
        self.escalation_matrix = self.graph_fetcher.fetch_escalation_matrix()
        
        if not self.escalation_matrix:
            self.mocks_dir = mocks_dir or os.path.join(base_dir, "shared", "mocks")
            self.escalation_matrix = self._load_json(os.path.join(self.mocks_dir, "escalation_matrix.json"), [])

    def _load_json(self, path, default):
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
        return default

    def _contains_any(self, text, keywords):
        if not text: return False
        text_lower = text.lower()
        return any(kw.lower() in text_lower for kw in keywords)

    @staticmethod
    def _deep_wrap(value):
        class AttrDict(dict):
            def __getattr__(self, item):
                if item in self: return self[item]
                return None
        if isinstance(value, dict):
            return AttrDict({k: EscalationValidator._deep_wrap(v) for k, v in value.items()})
        if isinstance(value, list):
            return [EscalationValidator._deep_wrap(v) for v in value]
        return value

    def validate(self, agent_id: str, output: dict) -> dict:
        triggers_fired = []

        functions = {
            "contains_any": self._contains_any
        }

        names = {
            "output": output,
            "SAFETY_KEYWORDS": ["fatality", "fall", "struck-by", "electrocution", "caught-in", "hospitalization"]
        }

        rules = [r for r in self.escalation_matrix if r.get("agent_id") in [agent_id, "all"]]
        pass_validation = True

        for rule in rules:
            expr = rule.get("condition_expression", "False")

            # Preprocess DSL to Python-compatible syntax
            expr_python = (
                expr.replace(" OR ", " or ")
                    .replace(" AND ", " and ")
                    .replace("== null", "== None")
                    .replace("!= null", "!= None")
            )

            try:
                names["output"] = self._deep_wrap(output)
                names["true"] = True
                names["false"] = False
                names["null"] = None
                
                evaluator = EvalWithCompoundTypes(names=names, functions=functions)
                matched = evaluator.eval(expr_python)
                
                if matched:
                    halts_write = rule.get("halts_write", False)
                    triggers_fired.append({
                        "trigger_id": rule.get("trigger_id"),
                        "destination": rule.get("destination"),
                        "halts_write": halts_write,
                        "condition_matched": expr
                    })
                    if halts_write:
                        pass_validation = False
                        
            except Exception as e:
                # Missing attributes resolve to None. E.g., None > 1 raises TypeError.
                from simpleeval import InvalidExpression
                if isinstance(e, (KeyError, AttributeError, NameError, TypeError, NameNotDefined, AttributeDoesNotExist, InvalidExpression)):
                    continue
                    
                triggers_fired.append({
                    "trigger_id": rule.get("trigger_id"),
                    "destination": "Teams -> Agent Review Queue (Error)",
                    "halts_write": True,
                    "condition_matched": f"Error evaluating: {expr}. Details: {str(e)}"
                })
                pass_validation = False
                
        if triggers_fired:
            return {"pass": pass_validation, "triggers_fired": triggers_fired}
            
        return {"pass": True}
