import os
import requests
import logging

class ValidatorClient:
    def __init__(self):
        self.api_url = os.getenv("VALIDATOR_API_URL", "http://localhost:7071/api/validate")
        
    def validate(self, run_id: str, agent_id: str, agent_version: str, output: dict, proposed_writes: list, proposed_filenames: list) -> dict:
        payload = {
            "run_id": run_id,
            "agent_id": agent_id,
            "agent_version": agent_version,
            "output": output,
            "proposed_writes": proposed_writes,
            "proposed_filenames": proposed_filenames
        }
        
        try:
            response = requests.post(self.api_url, json=payload, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                logging.error(f"Validator API returned HTTP {response.status_code}")
                return {"pass": False, "first_failure": "http_error", "results": {}}
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to reach Validator Chain at {self.api_url}: {str(e)}")
            return {"pass": False, "first_failure": "unreachable", "results": {}}
