import os
import json
import jsonschema
import logging

class SchemaValidator:
    def __init__(self, schemas_dir: str = None):
        if schemas_dir is not None:
            self.schemas_dir = schemas_dir
            return

        env_dir = os.getenv("SCHEMAS_DIR")
        if env_dir:
            self.schemas_dir = env_dir
            return

        # Try (in order): <validator>/schemas (deployed layout),
        # <repo>/schemas (local dev layout).
        validator_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        candidates = [
            os.path.join(validator_dir, "schemas"),
            os.path.join(os.path.dirname(validator_dir), "schemas"),
        ]
        for c in candidates:
            if os.path.isdir(c):
                self.schemas_dir = c
                return
        self.schemas_dir = candidates[0]
            
    def validate(self, agent_id: str, output: dict) -> dict:
        schema_path = os.path.join(self.schemas_dir, f"{agent_id}.schema.json")
        
        if not os.path.exists(schema_path):
            return {
                "pass": False,
                "reason": f"Schema file not found for agent: {agent_id}"
            }
            
        try:
            with open(schema_path, "r") as f:
                schema = json.load(f)
                
            jsonschema.validate(instance=output, schema=schema)
            return {"pass": True}
        except jsonschema.exceptions.ValidationError as e:
            return {
                "pass": False,
                "errors": [
                    {"field": ".".join(map(str, e.path)) or "root", "message": e.message}
                ]
            }
        except Exception as e:
            logging.error(f"Schema validation error: {e}")
            return {"pass": False, "reason": str(e)}
