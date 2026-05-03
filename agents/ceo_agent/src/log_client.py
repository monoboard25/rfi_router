import os
import logging
from azure.data.tables import TableServiceClient
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

class LogAnalyticsClient:
    def __init__(self, connection_string: str = None):
        self.connection_string = connection_string or os.getenv("AZURE_TABLE_CONNECTION_STRING")
        self.table_name = "agentruns"
        
    def _get_table_client(self):
        if not self.connection_string:
            return None
        service_client = TableServiceClient.from_connection_string(self.connection_string)
        return service_client.get_table_client(self.table_name)

    def get_weekly_logs(self) -> List[Dict[str, Any]]:
        client = self._get_table_client()
        if not client:
            logging.warning("Azure Table Connection String not found. Returning empty logs.")
            return []
            
        one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        # PartitionKey is often the Date or AgentID. For this query, we filter by Timestamp
        filter_str = f"Timestamp ge datetime'{one_week_ago.isoformat()}'"
        
        try:
            return list(client.query_entities(filter_str))
        except Exception as e:
            logging.error(f"Error querying agentruns table: {str(e)}")
            return []

    def compute_metrics(self, logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not logs:
            return {
                "throughput": {},
                "validator_health": {"pass": 0, "fail": 0},
                "escalation_heatmap": {},
                "resolution_drift": {"schema_parse": 0, "inference": 0},
                "total_cost": 0.0,
                "latency_avg_ms": 0,
                "total_runs": 0
            }

        metrics = {
            "throughput": {},
            "validator_health": {"pass": 0, "fail": 0},
            "escalation_heatmap": {},
            "resolution_drift": {"schema_parse": 0, "inference": 0},
            "total_cost": 0.0,
            "latency_avg_ms": 0,
            "latency_total": 0,
            "total_runs": len(logs)
        }

        for log in logs:
            # 1. Throughput
            agent_id = log.get("agent_id", "unknown")
            metrics["throughput"][agent_id] = metrics["throughput"].get(agent_id, 0) + 1
            
            # 2. Validator Health
            outcome = log.get("outcome", "")
            if outcome in ["routed", "completed_with_write"]:
                metrics["validator_health"]["pass"] += 1
            else:
                metrics["validator_health"]["fail"] += 1
                
            # 3. Escalation Heatmap
            # Assuming escalations are logged as a stringified list or similar
            escalations = log.get("escalations_fired", "[]")
            # Simplification for this logic
            if "threshold" in outcome or "escalated" in outcome:
                metrics["escalation_heatmap"][outcome] = metrics["escalation_heatmap"].get(outcome, 0) + 1
                
            # 4. Resolution Drift
            res_path = log.get("resolution_path", "")
            if res_path == "schema_parse":
                metrics["resolution_drift"]["schema_parse"] += 1
            elif res_path == "inference":
                metrics["resolution_drift"]["inference"] += 1
                
            # 5. Cost
            metrics["total_cost"] += float(log.get("total_cost", 0.0))
            
            # 6. Latency
            metrics["latency_total"] += int(log.get("duration_ms", 0))

        if metrics["total_runs"] > 0:
            metrics["latency_avg_ms"] = metrics["latency_total"] // metrics["total_runs"]

        return metrics
