import os
import json
import logging
from openai import AzureOpenAI
from typing import Dict, Any

class ScorecardGenerator:
    def __init__(self):
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.key = os.getenv("AZURE_OPENAI_KEY")
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

    def generate_markdown(self, metrics: Dict[str, Any]) -> str:
        # Use LLM to provide the narrative "CEO Recommendation"
        recommendation = self._get_llm_recommendation(metrics)
        
        md = f"""# 🏛 Monoboard Agent Ecosystem: Weekly Governance Scorecard
**Date**: {os.popen('date "+%Y-%m-%d"').read().strip()}

## 📊 Performance Overview
| Metric | Value |
| --- | --- |
| **Total Runs** | {metrics.get('total_runs', 0)} |
| **Validator Success Rate** | {self._calc_rate(metrics['validator_health']['pass'], metrics.get('total_runs', 0))}% |
| **Avg Latency** | {metrics.get('latency_avg_ms', 0)} ms |
| **Total Ecosystem Cost** | ${metrics.get('total_cost', 0.0):.2f} |

## 🧠 Resolution Drift (Parse vs. Infer)
We track how often agents rely on expensive LLM inference vs. deterministic schema parsing.
- **Deterministic (Schema Parse)**: {metrics['resolution_drift']['schema_parse']} runs
- **Inference (Azure OpenAI)**: {metrics['resolution_drift']['inference']} runs

## 🚨 Active Governance Alerts
{self._format_alerts(metrics.get('alerts', []))}

## 🚀 Throughput by Agent
{self._format_dict(metrics['throughput'])}

## ⚠️ Escalation & Failure Heatmap
{self._format_dict(metrics['escalation_heatmap'])}

## 🤖 CEO Recommendation
{recommendation}
"""
        return md

    def _calc_rate(self, count, total):
        if total == 0: return 0
        return round((count / total) * 100, 1)

    def _format_dict(self, d):
        if not d: return "None recorded."
        return "\n".join([f"- **{k}**: {v}" for k, v in d.items()])

    def _format_alerts(self, alerts):
        if not alerts: return "✅ No critical anomalies detected."
        return "\n".join([f"- **[{a['type']}]** ({a['severity'].upper()}): {a['message']}" for a in alerts])

    def _get_llm_recommendation(self, metrics: Dict[str, Any]) -> str:
        if not all([self.endpoint, self.key, self.deployment]):
            return "Note: Azure OpenAI credentials not found. Manual governance review required."

        try:
            client = AzureOpenAI(
                azure_endpoint=self.endpoint,
                api_key=self.key,
                api_version="2024-02-01"
            )
            
            prompt = f"Analyze these agent governance metrics and provide a 3-sentence recommendation for the project owner. Focus on cost, drift, or validation failures: {json.dumps(metrics)}"
            
            response = client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": "You are the CEO Governance Agent. Your job is to monitor a fleet of AI agents and ensure they stay within governance boundaries."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"Error generating recommendation: {str(e)}")
            return "Error generating AI recommendation. Check logs."
