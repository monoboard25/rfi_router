"""Durable orchestrator — one instance per escalation run_id.

State machine:

    Start
      |
      v
   check_idempotency  ----- already-decided -----> exit
      |
      v
   load_constitution
      |
      v
   classify_tier
      |
      v
   send_telegram_message
      |
      v
   WaitForExternalEvent("OperatorDecision")  ---- 24h timeout ----> escalate_to_email
      |
      v
   post_approval_to_validator
      |
      v
   done

Durable state survives function restarts. RaiseEvent calls from the
Telegram callback (or magic-link Weekend-2 path) resume the orchestrator.
"""

from datetime import timedelta

import azure.durable_functions as df


def approval_orchestrator(context: df.DurableOrchestrationContext):
    msg = context.get_input()
    run_id = msg["run_id"]

    already = yield context.call_activity("check_idempotency", run_id)
    if already and already.get("decided"):
        return {"status": "skipped_already_decided", "run_id": run_id}

    constitution = yield context.call_activity("load_constitution", msg)
    classified = yield context.call_activity(
        "classify_tier",
        {"message": msg, "constitution": constitution},
    )

    send_result = yield context.call_activity(
        "send_telegram_message",
        {"message": msg, "classified": classified, "constitution": constitution},
    )

    deadline = context.current_utc_datetime + timedelta(hours=24)
    timeout_task = context.create_timer(deadline)
    decision_task = context.wait_for_external_event("OperatorDecision")

    winner = yield context.task_any([decision_task, timeout_task])

    if winner == timeout_task:
        return (
            yield context.call_activity(
                "escalate_to_email",
                {"message": msg, "send_result": send_result},
            )
        )

    timeout_task.cancel()
    decision = winner.result

    return (
        yield context.call_activity(
            "post_approval_to_validator",
            {
                "message": msg,
                "decision": decision,
            },
        )
    )
