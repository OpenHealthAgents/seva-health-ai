<#
.SYNOPSIS
    SevaHealth AI Development & Evaluation Runner
.DESCRIPTION
    Convenience script to run SevaHealth AI services, test suites, and data seeding on Windows.
#>

param(
    [ValidateSet("dev", "test", "seed", "lint", "e2e", "help")]
    [string]$Command = "dev"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Ensure PYTHONPATH includes root
$env:PYTHONPATH = "$ScriptDir;$env:PYTHONPATH"

switch ($Command) {
    "dev" {
        Write-Host "Starting SevaHealth AI Backend Gateway on http://localhost:8000..." -ForegroundColor Cyan
        Write-Host "OpenAPI documentation available at http://localhost:8000/docs" -ForegroundColor Green
        python -m uvicorn services.api.main:app --reload --port 8000 --host 0.0.0.0
    }
    "test" {
        Write-Host "Running SevaHealth AI Automated Test Suite..." -ForegroundColor Cyan
        python -m pytest tests -v --tb=short
    }
    "seed" {
        Write-Host "Seeding synthetic patient personas and 1,200 regional screening records..." -ForegroundColor Cyan
        python scripts/seed_data.py
    }
    "e2e" {
        Write-Host "Executing end-to-end 8-stage verification pipeline..." -ForegroundColor Cyan
        python scripts/test_e2e.py
    }
    "lint" {
        Write-Host "Checking code syntax and types..." -ForegroundColor Cyan
        python -m ruff check .
    }
    default {
        Write-Host "Usage: .\run.ps1 [dev | test | seed | e2e | lint]" -ForegroundColor Yellow
    }
}
