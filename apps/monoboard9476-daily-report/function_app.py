import json
import logging
import os
from datetime import datetime, timezone

import azure.functions as func
import requests

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

VALIDATOR_API_URL = os.getenv("VALIDATOR_API_URL")


def _build_report() -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": "Daily project status placeholder. Wire to Monoboard data source.",
        "open_rfis": 0,
        "pending_change_orders": 0,
    }


def _log(action: str, payload: dict) -> dict:
    if not VALIDATOR_API_URL:
        return {"decision": "allow", "reasons": ["validator not configured"]}
    try:
        resp = requests.post(
            VALIDATOR_API_URL,
            json={"agent": "daily-report", "action": action, **payload},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        logging.exception("validator call failed")
        return {"decision": "error"}


@app.schedule(schedule="0 0 13 * * *", arg_name="timer", run_on_startup=False)
def daily_run(timer: func.TimerRequest) -> None:
    report = _build_report()
    _log("emit_daily_report", {"report_keys": list(report.keys())})
    logging.info("daily report: %s", json.dumps(report))


@app.route(route="manual_daily_report", methods=["GET", "POST"])
def manual_daily_report(req: func.HttpRequest) -> func.HttpResponse:
    report = _build_report()
    decision = _log("manual_daily_report", {"trigger": "http"})
    return func.HttpResponse(
        json.dumps({"report": report, "validator": decision}),
        mimetype="application/json",
    )


@app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def health(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse('{"status":"ok"}', mimetype="application/json")
