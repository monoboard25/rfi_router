import json
import logging

import azure.functions as func

from src.agent import run_onboarding_agent

app = func.FunctionApp()


@app.route(route="onboarding_agent", methods=["POST"])
def onboarding_agent(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Onboarding Agent HTTP trigger invoked.")
    try:
        payload = req.get_json()
    except ValueError:
        return func.HttpResponse("Invalid JSON payload.", status_code=400)

    try:
        result = run_onboarding_agent(payload)
        return func.HttpResponse(
            body=json.dumps(result),
            mimetype="application/json",
            status_code=200,
        )
    except Exception as exc:
        logging.exception("Onboarding Agent failure")
        return func.HttpResponse(f"Internal Server Error: {exc}", status_code=500)


@app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def health(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse('{"status":"ok"}', mimetype="application/json")
