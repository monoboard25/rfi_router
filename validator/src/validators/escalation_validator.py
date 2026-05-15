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

    def _sum_crew_hours(self, crew_hours):
        if not crew_hours: return 0
        return sum((h.hours or 0) for h in crew_hours)

    def _any_severity(self, signals, levels):
        if not signals: return False
        return any(s.severity in levels for s in signals if s.severity)

    def _signals_match_keywords(self, signals, keywords):
        if not signals: return False
        return any(self._contains_any(s.observation, keywords) for s in signals if s.observation)

    def _any_stale(self, sources_cited):
        if not sources_cited: return False
        return any(s.freshness_ok is False for s in sources_cited)

    def _count_failed_attempts(self, attempts):
        if not attempts: return 0
        return sum(1 for a in attempts if a.outcome == 'fail')

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
            "contains_any": self._contains_any,
            "sum_crew_hours": self._sum_crew_hours,
            "any_severity": self._any_severity,
            "signals_match_keywords": self._signals_match_keywords,
            "any_stale": self._any_stale,
            "count_failed_attempts": self._count_failed_attempts
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
