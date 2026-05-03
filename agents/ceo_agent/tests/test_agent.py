import pytest
from src.log_client import LogAnalyticsClient

def test_compute_metrics_basic():
    mock_logs = [
        {"agent_id": "rfi_router", "outcome": "routed", "resolution_path": "schema_parse", "total_cost": "0.01", "duration_ms": "500"},
        {"agent_id": "rfi_router", "outcome": "halted_validation", "resolution_path": "inference", "total_cost": "0.05", "duration_ms": "2000"},
        {"agent_id": "change_order", "outcome": "routed", "resolution_path": "schema_parse", "total_cost": "0.01", "duration_ms": "600"}
    ]
    
    client = LogAnalyticsClient(connection_string="dummy")
    metrics = client.compute_metrics(mock_logs)
    
    assert metrics["total_runs"] == 3
    assert metrics["throughput"]["rfi_router"] == 2
    assert metrics["throughput"]["change_order"] == 1
    assert metrics["validator_health"]["pass"] == 2
    assert metrics["validator_health"]["fail"] == 1
    assert metrics["resolution_drift"]["schema_parse"] == 2
    assert metrics["resolution_drift"]["inference"] == 1
    assert metrics["total_cost"] == 0.07
    assert metrics["latency_avg_ms"] == (500 + 2000 + 600) // 3

def test_compute_metrics_empty():
    client = LogAnalyticsClient(connection_string="dummy")
    metrics = client.compute_metrics([])
    assert metrics["total_runs"] == 0
    assert metrics["total_cost"] == 0.0
