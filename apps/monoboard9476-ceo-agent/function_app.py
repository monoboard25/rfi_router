import json
import logging
import os

import azure.functions as func
import requests

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

VALIDATOR_API_URL = os.getenv("VALIDATOR_API_URL")
PEER_ENDPOINTS = {
    "rfi-router": os.getenv("RFI_ROUTER_URL"),
    "change-order": os.getenv("CHANGE_ORDER_URL"),
    "daily-report": os.getenv("DAILY_REPORT_URL"),
}


def _validate(action: str, payload: dict) -> dict:
    if not VALIDATOR_API_URL:
        return {"decision": "allow", "reasons": ["validator not configured"]}
    try:
        resp = requests.post(
            VALIDATOR_API_URL,
            json={"agent": "ceo-agent", "action": action, **payload},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        logging.exception("validator call failed")
        return {"decision": "error"}


@app.route(route="manual_governance_report", methods=["GET", "POST"])
def manual_governance_report(req: func.HttpRequest) -> func.HttpResponse:
    health = {}
    for name, url in PEER_ENDPOINTS.items():
        if not url:
            health[name] = "unconfigured"
            continue
        try:
            r = requests.get(url, timeout=5)
            health[name] = f"{r.status_code}"
        except Exception as exc:
            health[name] = f"error: {exc}"

    decision = _validate("governance_report", {"peers": list(PEER_ENDPOINTS.keys())})
    return func.HttpResponse(
        json.dumps({"status": "ok", "peers": health, "validator": decision}),
        mimetype="application/json",
    )
