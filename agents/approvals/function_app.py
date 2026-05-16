import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import azure.functions as func
import azure.durable_functions as df

from queue_trigger import on_escalation_event
from approval_orchestrator import approval_orchestrator
from telegram_callback import telegram_callback
from activities import (
    activity_send_telegram_message,
    activity_post_approval_to_validator,
    activity_check_idempotency,
    activity_load_constitution,
    activity_classify_tier,
    activity_escalate_to_email,
)

app = df.DFApp(http_auth_level=func.AuthLevel.FUNCTION)


@app.queue_trigger(
    arg_name="msg",
    queue_name="%ESCALATION_QUEUE_NAME%",
    connection="AzureWebJobsStorage",
)
@app.durable_client_input(client_name="client")
async def escalation_queue_trigger(msg: func.QueueMessage, client):
    await on_escalation_event(msg, client)


@app.orchestration_trigger(context_name="context")
def approval_orchestrator_function(context: df.DurableOrchestrationContext):
    return approval_orchestrator(context)


@app.activity_trigger(input_name="payload")
def send_telegram_message(payload: dict) -> dict:
    return activity_send_telegram_message(payload)


@app.activity_trigger(input_name="payload")
def post_approval_to_validator(payload: dict) -> dict:
    return activity_post_approval_to_validator(payload)


@app.activity_trigger(input_name="run_id")
def check_idempotency(run_id: str) -> dict:
    return activity_check_idempotency(run_id)


@app.activity_trigger(input_name="payload")
def load_constitution(payload: dict) -> dict:
    return activity_load_constitution(payload)


@app.activity_trigger(input_name="payload")
def classify_tier(payload: dict) -> dict:
    return activity_classify_tier(payload)


@app.activity_trigger(input_name="payload")
def escalate_to_email(payload: dict) -> dict:
    return activity_escalate_to_email(payload)


@app.route(route="telegram/callback", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
@app.durable_client_input(client_name="client")
async def telegram_callback_route(req: func.HttpRequest, client) -> func.HttpResponse:
    return await telegram_callback(req, client)


@app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def health(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse('{"status":"ok"}', mimetype="application/json")
