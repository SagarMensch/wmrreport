import json
from orchestrator import PipelineOrchestrator

orchestrator = PipelineOrchestrator()
question = "Which wells have a SCR number recorded and what is their current progress?"
result = orchestrator.process(question)

print("SUCCESS")
print(f"SQL Generated: {result.sql_query}")
print(f"Chart Recommended: {result.chart_type}")
print(f"First 5 Rows: {result.rows[:5]}")
