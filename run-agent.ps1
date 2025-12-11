# Quick launcher for Discovery Workshop Agent
# Usage: .\run-agent.ps1

$ErrorActionPreference = "Stop"

# Get script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "Starting Azure Landing Zone Discovery Workshop..." -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment exists
if (Test-Path ".\.venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Green
    & .\.venv\Scripts\Activate.ps1
}

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "WARNING: .env file not found!" -ForegroundColor Yellow
    Write-Host "Please ensure Azure resources are configured." -ForegroundColor Yellow
    Write-Host ""
}

# Run the agent
python -m src.discovery_workshop

# Deactivate virtual environment if it was activated
if ($env:VIRTUAL_ENV) {
    deactivate
}
