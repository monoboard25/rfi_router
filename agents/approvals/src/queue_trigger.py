"""Queue trigger entrypoint.

Reads a message from `escalation-events`, parses + validates the
EscalationQueueMessage envelope, and starts a Durable orchestrator
keyed on `run_id`.

Idempotency: orchestrator instance ID == run_id. Starting an instance
that already exists is a no-op in Durable Functions, so duplicate queue
deliveries do not spawn parallel orchestrators.
"""

import json
import logging

import azure.functions as func
import azure.durable_functions as df

from models import EscalationQueueMessage


async def on_escalation_event(
    msg: func.QueueMessage,
    client: df.DurableOrchestrationClient,
) -> None:
    raw = msg.get_body().decode("utf-8")
    try:
        parsed = EscalationQueueMessage.model_validate_json(raw)
    except Exception as e:
        logging.exception("Malformed queue message; routing to poison")
        raise

    instance_id = parsed.run_id

    existing = await client.get_status(instance_id)
    if existing and existing.runtime_status not in (
        df.OrchestrationRuntimeStatus.Pending,
        df.OrchestrationRuntimeStatus.Failed,
        df.OrchestrationRuntimeStatus.Terminated,
        df.OrchestrationRuntimeStatus.Canceled,
    ):
        logging.info(
            "Orchestrator %s already running (%s); skip duplicate enqueue",
            instance_id,
            existing.runtime_status,
        )
        return

    await client.start_new(
        "approval_orchestrator_function",
        instance_id=instance_id,
        client_input=parsed.model_dump(mode="json"),
    )
    logging.info("Started orchestrator instance %s", instance_id)
