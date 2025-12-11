# Project Cleanup Script
# Removes generated files, logs, and temporary data

param(
    [switch]$All,
    [switch]$OutputOnly,
    [switch]$LogsOnly,
    [switch]$DryRun
)

function Write-Info { param($msg) Write-Host $msg -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host $msg -ForegroundColor Green }
function Write-Warning { param($msg) Write-Host $msg -ForegroundColor Yellow }

Write-Info "=== Azure Landing Zone Discovery Workshop - Cleanup ==="
Write-Info ""

$itemsToClean = @()

# Output files
if ($All -or $OutputOnly) {
    Write-Info "Checking output directory..."
    if (Test-Path "output") {
        $outputFiles = Get-ChildItem "output\*.json"
        if ($outputFiles) {
            $itemsToClean += $outputFiles
            Write-Warning "Found $($outputFiles.Count) output files"
        }
    }
}

# Log files
if ($All -or $LogsOnly) {
    Write-Info "Checking for log files..."
    $logFiles = Get-ChildItem "*.log" -ErrorAction SilentlyContinue
    if ($logFiles) {
        $itemsToClean += $logFiles
        Write-Warning "Found $($logFiles.Count) log files"
    }
}

# Discovery results
if ($All -or $OutputOnly) {
    Write-Info "Checking for discovery results..."
    $discoveryFiles = Get-ChildItem "discovery_results_*.json" -ErrorAction SilentlyContinue
    if ($discoveryFiles) {
        $itemsToClean += $discoveryFiles
        Write-Warning "Found $($discoveryFiles.Count) discovery result files"
    }
    
    $contextFiles = Get-ChildItem "context_package_*.json" -ErrorAction SilentlyContinue
    if ($contextFiles) {
        $itemsToClean += $contextFiles
        Write-Warning "Found $($contextFiles.Count) context package files"
    }
}

# Python cache
if ($All) {
    Write-Info "Checking for Python cache..."
    $pycacheDirectories = Get-ChildItem -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notlike "*\.venv\*" }
    if ($pycacheDirectories) {
        $itemsToClean += $pycacheDirectories
        Write-Warning "Found $($pycacheDirectories.Count) __pycache__ directories"
    }
    
    $pycFiles = Get-ChildItem -Recurse -Filter "*.pyc" -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notlike "*\.venv\*" }
    if ($pycFiles) {
        $itemsToClean += $pycFiles
        Write-Warning "Found $($pycFiles.Count) .pyc files"
    }
}

# Summary
Write-Info ""
if ($itemsToClean.Count -eq 0) {
    Write-Success "✓ No files to clean!"
    exit 0
}

Write-Warning "Files to be cleaned:"
foreach ($item in $itemsToClean) {
    Write-Host "  - $($item.FullName)" -ForegroundColor DarkGray
}

Write-Info ""
Write-Info "Total items: $($itemsToClean.Count)"

if ($DryRun) {
    Write-Info ""
    Write-Info "DRY RUN - No files were deleted"
    exit 0
}

# Confirm deletion
Write-Info ""
$confirm = Read-Host "Proceed with deletion? (y/N)"

if ($confirm -ne 'y' -and $confirm -ne 'Y') {
    Write-Warning "Cleanup cancelled"
    exit 0
}

# Delete files
Write-Info ""
Write-Info "Cleaning up..."
$deletedCount = 0
foreach ($item in $itemsToClean) {
    try {
        if ($item -is [System.IO.DirectoryInfo]) {
            Remove-Item $item.FullName -Recurse -Force
        }
        else {
            Remove-Item $item.FullName -Force
        }
        $deletedCount++
    }
    catch {
        Write-Host "  Failed to delete: $($item.Name)" -ForegroundColor Red
    }
}

Write-Success ""
Write-Success "✓ Cleanup complete! Deleted $deletedCount items."

# Usage examples
<#
.SYNOPSIS
    Cleans up generated files, logs, and temporary data from the project.

.DESCRIPTION
    This script removes various generated files to keep the project clean:
    - Output JSON files (context packages, discovery results)
    - Log files
    - Python cache files and directories

.PARAMETER All
    Clean everything (outputs, logs, Python cache)

.PARAMETER OutputOnly
    Clean only output files (JSON results)

.PARAMETER LogsOnly
    Clean only log files

.PARAMETER DryRun
    Show what would be deleted without actually deleting

.EXAMPLE
    .\cleanup.ps1 -All
    Removes all generated files, logs, and cache

.EXAMPLE
    .\cleanup.ps1 -OutputOnly
    Removes only output JSON files

.EXAMPLE
    .\cleanup.ps1 -DryRun -All
    Shows what would be deleted without actually deleting

.EXAMPLE
    .\cleanup.ps1 -LogsOnly
    Removes only log files
#>
