$ErrorActionPreference = "Stop"

Write-Host "=== Running simulation batch ==="
uv run --package ev-factory-simulation python -m ev_sim.batch

Write-Host ""
Write-Host "=== Running benchmark evaluation ==="
uv run --package ev-twin-evaluation python -m ev_evaluation.benchmark

Write-Host ""
Write-Host "=== Evaluation completed ==="
Write-Host "Dataset: evaluation/datasets/simulation_results.csv"
Write-Host "Report:  evaluation/reports/benchmark_summary.csv"