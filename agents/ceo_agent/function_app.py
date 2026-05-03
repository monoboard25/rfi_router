import logging
import azure.functions as func
import json
from src.log_client import LogAnalyticsClient
from src.scorecard.scorecard import ScorecardGenerator # Fixed import path if needed, but I used src.scorecard

# Correcting import based on structure
from src.scorecard import ScorecardGenerator

app = func.FunctionApp()

@app.schedule(schedule="0 0 8 * * 1", arg_name="timer", run_on_startup=False, use_monitor=True) 
def weekly_governance_timer(timer: func.TimerRequest) -> None:
    logging.info('CEO Governance Agent Timer Trigger started.')
    run_governance_cycle()

@app.route(route="manual_governance_report")
def manual_governance_report(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('CEO Governance Agent Manual Trigger started.')
    scorecard = run_governance_cycle()
    return func.HttpResponse(scorecard, mimetype="text/markdown")

def run_governance_cycle():
    # 1. Fetch Logs
    log_client = LogAnalyticsClient()
    logs = log_client.get_weekly_logs()
    
    # 2. Compute Metrics
    metrics = log_client.compute_metrics(logs)
    
    # 3. Generate Scorecard
    generator = ScorecardGenerator()
    scorecard_md = generator.generate_markdown(metrics)
    
    # 4. Delivery (Mocked for now, would use MS Graph to post to Teams/SP)
    logging.info("CEO Scorecard Generated Successfully.")
    logging.info(f"Summary metrics: {metrics['total_runs']} runs, ${metrics['total_cost']} cost.")
    
    return scorecard_md
