# Wingman Copilot - Windows Setup Script
# This script automates the setup process for the Wingman Copilot project

Write-Host "================================" -ForegroundColor Cyan
Write-Host "Wingman Copilot - Setup Script" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
Write-Host "Checking Python..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "Python found: $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "Python not found. Please install Python 3.10+" -ForegroundColor Red
    exit 1
}

# Check Node.js
Write-Host "Checking Node.js..." -ForegroundColor Yellow
$nodeVersion = node --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "Node.js found: $nodeVersion" -ForegroundColor Green
} else {
    Write-Host "Node.js not found. Please install Node.js 16+" -ForegroundColor Red
    exit 1
}

# Backend Setup
Write-Host ""
Write-Host "=== Backend Setup ===" -ForegroundColor Cyan

if (-Not (Test-Path "backend")) {
    Write-Host "Creating backend folder..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Name "backend" -Force | Out-Null
}

Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
cd backend

if (-Not (Test-Path "venv")) {
    python -m venv venv
    Write-Host "Virtual environment created" -ForegroundColor Green
}

Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"
Write-Host "Virtual environment activated" -ForegroundColor Green

Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
if (Test-Path "backend_requirements.txt") {
    pip install -r backend_requirements.txt
    Write-Host "Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "backend_requirements.txt not found" -ForegroundColor Red
}

Write-Host "Creating .env file..." -ForegroundColor Yellow
if (-Not (Test-Path ".env")) {
    if (Test-Path ".env.template") {
        Copy-Item ".env.template" -Destination ".env"
        Write-Host ".env file created from template" -ForegroundColor Green
        Write-Host "Please edit .env with your Azure credentials" -ForegroundColor Yellow
    } else {
        Write-Host ".env.template not found" -ForegroundColor Red
    }
}

cd ..

# Frontend Setup
Write-Host ""
Write-Host "=== Frontend Setup ===" -ForegroundColor Cyan

if (-Not (Test-Path "frontend")) {
    Write-Host "Creating frontend folder..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Name "frontend" -Force | Out-Null
}

cd frontend

Write-Host "Installing Node.js dependencies..." -ForegroundColor Yellow
if (Test-Path "package.json") {
    npm install
    Write-Host "Frontend dependencies installed" -ForegroundColor Green
} else {
    Write-Host "package.json not found" -ForegroundColor Red
}

cd ..

# Summary
Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Edit backend\.env with your Azure credentials"
Write-Host "2. Start backend: cd backend && .\venv\Scripts\Activate.ps1 && python main.py"
Write-Host "3. Start frontend (new terminal): cd frontend && npm run dev"
Write-Host "4. Open http://localhost:3000 in your browser"
Write-Host ""
Write-Host "For more details, see QUICK_START.md" -ForegroundColor Yellow
Write-Host ""
