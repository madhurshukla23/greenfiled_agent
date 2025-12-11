# Project Health Check
# Validates project setup and configuration

param(
    [switch]$Verbose
)

function Write-Info { param($msg) Write-Host $msg -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "✓ $msg" -ForegroundColor Green }
function Write-Error { param($msg) Write-Host "✗ $msg" -ForegroundColor Red }
function Write-Warning { param($msg) Write-Host "⚠ $msg" -ForegroundColor Yellow }

$script:errorCount = 0
$script:warningCount = 0

Write-Info "=== Azure Landing Zone Discovery Workshop - Health Check ==="
Write-Info ""

# Check Python
Write-Info "Checking Python installation..."
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python (\d+)\.(\d+)") {
        $major = [int]$matches[1]
        $minor = [int]$matches[2]
        if ($major -ge 3 -and $minor -ge 11) {
            Write-Success "Python $pythonVersion"
        }
        else {
            Write-Error "Python 3.11+ required, found $pythonVersion"
            $script:errorCount++
        }
    }
}
catch {
    Write-Error "Python not found"
    $script:errorCount++
}

# Check virtual environment
Write-Info "`nChecking virtual environment..."
if (Test-Path ".venv") {
    Write-Success "Virtual environment exists"
}
else {
    Write-Warning "Virtual environment not found (.venv)"
    Write-Info "  Run: python -m venv venv"
    $script:warningCount++
}

# Check .env file
Write-Info "`nChecking environment configuration..."
if (Test-Path ".env") {
    Write-Success ".env file exists"
    
    # Validate required variables
    $requiredVars = @(
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_DEPLOYMENT_NAME",
        "AZURE_STORAGE_CONNECTION_STRING",
        "AZURE_STORAGE_CONTAINER_NAME",
        "AZURE_SEARCH_ENDPOINT",
        "AZURE_SEARCH_API_KEY",
        "AZURE_SEARCH_INDEX_NAME"
    )
    
    $envContent = Get-Content ".env" -Raw
    foreach ($var in $requiredVars) {
        if ($envContent -match "$var=.+") {
            if ($Verbose) {
                Write-Success "  $var configured"
            }
        }
        else {
            Write-Warning "  $var not configured"
            $script:warningCount++
        }
    }
}
else {
    Write-Error ".env file not found"
    Write-Info "  Copy .env.template to .env and configure"
    $script:errorCount++
}

# Check Python modules
Write-Info "`nChecking Python modules..."
try {
    $modules = @(
        "src.config",
        "src.models",
        "src.discovery_framework",
        "src.discovery_agent",
        "src.discovery_workshop"
    )
    
    $moduleCheck = python -c @"
import sys
modules = $($modules | ForEach-Object { "'$_'" } | Join-String -Separator ', ' -OutputPrefix '[' -OutputSuffix ']')
all_ok = True
for module in modules:
    try:
        __import__(module)
    except Exception as e:
        print(f'ERROR: {module}: {e}')
        all_ok = False
if all_ok:
    print('OK')
else:
    sys.exit(1)
"@
    
    if ($moduleCheck -eq 'OK') {
        Write-Success "All Python modules load correctly"
    }
    else {
        Write-Error "Some Python modules failed to load"
        Write-Info $moduleCheck
        $script:errorCount++
    }
}
catch {
    Write-Error "Failed to check Python modules"
    $script:errorCount++
}

# Check dependencies
Write-Info "`nChecking dependencies..."
if (Test-Path "requirements.txt") {
    Write-Success "requirements.txt exists"
    
    try {
        $pipCheck = pip check 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "No dependency conflicts"
        }
        else {
            Write-Warning "Dependency conflicts detected"
            if ($Verbose) {
                Write-Info $pipCheck
            }
            $script:warningCount++
        }
    }
    catch {
        Write-Warning "Could not verify dependencies"
        $script:warningCount++
    }
}
else {
    Write-Error "requirements.txt not found"
    $script:errorCount++
}

# Check project structure
Write-Info "`nChecking project structure..."
$requiredDirs = @("src", "scripts", "sample-artifacts", "docs")
$requiredFiles = @("README.md", "DISCOVERY_GUIDE.md", "QUICK_REFERENCE.md")

foreach ($dir in $requiredDirs) {
    if (Test-Path $dir) {
        if ($Verbose) {
            Write-Success "  Directory: $dir/"
        }
    }
    else {
        Write-Warning "  Missing directory: $dir/"
        $script:warningCount++
    }
}

foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        if ($Verbose) {
            Write-Success "  File: $file"
        }
    }
    else {
        Write-Warning "  Missing file: $file"
        $script:warningCount++
    }
}

if (-not $Verbose) {
    Write-Success "Project structure OK"
}

# Check sample artifacts
Write-Info "`nChecking sample artifacts..."
$sampleFiles = Get-ChildItem "sample-artifacts\*" -File -ErrorAction SilentlyContinue
if ($sampleFiles) {
    Write-Success "Found $($sampleFiles.Count) sample artifact(s)"
}
else {
    Write-Warning "No sample artifacts found"
    $script:warningCount++
}

# Summary
Write-Info ""
Write-Info "=========================================="
if ($script:errorCount -eq 0 -and $script:warningCount -eq 0) {
    Write-Success "Project health check PASSED"
    Write-Info ""
    Write-Info "Ready to run:"
    Write-Info "  python -m src.discovery_workshop"
}
elseif ($script:errorCount -eq 0) {
    Write-Warning "Project health check PASSED with $script:warningCount warning(s)"
    Write-Info ""
    Write-Info "Project is functional but has some warnings."
    Write-Info "Run with -Verbose for details."
}
else {
    Write-Error "Project health check FAILED"
    Write-Info ""
    Write-Info "Errors: $script:errorCount"
    Write-Info "Warnings: $script:warningCount"
    Write-Info ""
    Write-Info "Please fix errors before running the workshop."
    exit 1
}

<#
.SYNOPSIS
    Validates the project setup and configuration

.DESCRIPTION
    Performs comprehensive health check including:
    - Python version and virtual environment
    - Environment variables configuration
    - Python module imports
    - Dependencies and conflicts
    - Project structure
    - Sample artifacts

.PARAMETER Verbose
    Show detailed check results

.EXAMPLE
    .\health-check.ps1
    Run basic health check

.EXAMPLE
    .\health-check.ps1 -Verbose
    Run detailed health check with all validations shown
#>
