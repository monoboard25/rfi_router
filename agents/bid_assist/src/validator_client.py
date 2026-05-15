import os
import requests
import logging

class ValidatorClient:
    def __init__(self):
        self.api_url = os.getenv("GOVERNANCE_AGENT_URL", "http://localhost:3000/validate")
        
    def validate(self, agent_name: str, prompt: str, response_text: str) -> dict:
        payload = {
            "agentName": agent_name,
            "prompt": prompt,
            "response": response_text
        }
        
        try:
            response = requests.post(self.api_url, json=payload, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                logging.error(f"Governance Agent returned HTTP {response.status_code}")
                return {"isValid": False, "violations": ["http_error"], "score": 0}
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to reach Governance Agent at {self.api_url}: {str(e)}")
            return {"isValid": False, "violations": ["unreachable"], "score": 0}
