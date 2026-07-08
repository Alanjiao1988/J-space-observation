# Script: 00_check_prereqs.ps1
# Purpose: Azure-first readiness check for Windows. This script does not create resources.

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..\..\..")

Write-Host "================================"
Write-Host "Azure readiness check"
Write-Host "================================"
Write-Host ""

if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Host "[FAIL] Azure CLI is not installed or not on PATH."
    Write-Host "Run: az login after installing Azure CLI."
    exit 1
}

Write-Host "[OK] Azure CLI found"
az version --query '"azure-cli"' -o tsv
Write-Host ""

Write-Host "Checking Azure login..."
$null = az account show 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] Azure CLI is not logged in."
    Write-Host "Run: az login"
    exit 1
}

$SubscriptionName = az account show --query name -o tsv
$SubscriptionId = az account show --query id -o tsv
$SubscriptionState = az account show --query state -o tsv
Write-Host "[OK] Logged in"
Write-Host "Subscription name: $SubscriptionName"
Write-Host "Subscription id: $SubscriptionId"
Write-Host "Subscription state: $SubscriptionState"
Write-Host ""

Write-Host "Checking provider registrations..."
$AppState = az provider show -n Microsoft.App --query registrationState -o tsv
$AcrState = az provider show -n Microsoft.ContainerRegistry --query registrationState -o tsv
Write-Host "Microsoft.App: $AppState"
Write-Host "Microsoft.ContainerRegistry: $AcrState"
if ($AppState -ne "Registered") {
    Write-Host "[FAIL] Microsoft.App is not Registered. Do not create Container Apps resources yet."
    exit 1
}
if ($AcrState -ne "Registered") {
    Write-Host "[FAIL] Microsoft.ContainerRegistry is not Registered. Do not create ACR resources yet."
    exit 1
}
Write-Host ""

Write-Host "Checking Container Apps extension..."
$null = az extension show --name containerapp 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] containerapp extension is not installed."
    Write-Host "Run: az extension add --name containerapp --upgrade"
    exit 1
}
$ContainerAppVersion = az extension show --name containerapp --query version -o tsv
Write-Host "[OK] containerapp extension installed: $ContainerAppVersion"
Write-Host ""

Write-Host "GPU quota check instructions:"
Write-Host "1. Confirm region and workload profile from infra\azure\variables.env."
Write-Host "2. In Azure Portal: Subscription -> Usage + quotas -> filter by provider Microsoft.App and region."
Write-Host "3. Verify quota for Container Apps GPU T4 workload profile, e.g. Consumption-GPU-NC8as-T4."
Write-Host "4. If quota is missing or zero, stop and request quota before running jobs."
Write-Host "5. Do not fall back to local model inference."
Write-Host ""

Write-Host "No Azure resources were created by this readiness check."

$LogFile = Join-Path $ProjectRoot "docs\run_log.md"
if (Test-Path $LogFile) {
    Add-Content -Path $LogFile -Value ""
    Add-Content -Path $LogFile -Value "## Azure readiness script check - $(Get-Date -AsUTC -Format 'yyyy-MM-ddTHH:mm:ssZ')"
    Add-Content -Path $LogFile -Value ""
    Add-Content -Path $LogFile -Value "- Command: ``.\infra\azure\scripts\00_check_prereqs.ps1``"
    Add-Content -Path $LogFile -Value "- Subscription: $SubscriptionName ($SubscriptionId)"
    Add-Content -Path $LogFile -Value "- Microsoft.App registration: $AppState"
    Add-Content -Path $LogFile -Value "- Microsoft.ContainerRegistry registration: $AcrState"
    Add-Content -Path $LogFile -Value "- containerapp extension: installed ($ContainerAppVersion)"
    Add-Content -Path $LogFile -Value "- Azure resources created: none"
}

Write-Host "================================"
Write-Host "[OK] Azure readiness check completed"
Write-Host "================================"
