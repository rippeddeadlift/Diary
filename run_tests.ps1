# PowerShell script to run server tests
# Usage: .\run_tests.ps1

Write-Host "Setting up test environment..." -ForegroundColor Cyan

# Check if virtual environment exists
if (-not (Test-Path "server\.venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv server\.venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Cyan
& "server\.venv\Scripts\Activate.ps1"

# Install/update dependencies
Write-Host "Installing dependencies..." -ForegroundColor Cyan
pip install -q -r server\requirements.txt

# Run tests
Write-Host "`nRunning tests..." -ForegroundColor Green
python -m pytest -v

Write-Host "`nDone!" -ForegroundColor Green
