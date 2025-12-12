#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Deploy stacks directly to Komodo (dev workflow - bypasses git).

.DESCRIPTION
    During development, deploy stacks directly via Komodo API instead of
    waiting for git push + ResourceSync. This allows rapid iteration.

    Production workflow: git push → ResourceSync → deploy
    Development workflow: ./deploy.ps1 <stack> → direct API deploy

.PARAMETER Stack
    Name of the stack to deploy (as defined in komodo.toml)

.PARAMETER All
    Deploy all stacks (optionally filtered by -Server)

.PARAMETER Server
    Filter stacks by server name (infra, media-gpu, frigate-gpu, frigate, omada)

.PARAMETER DryRun
    Show what would be deployed without actually deploying

.PARAMETER List
    List available stacks

.PARAMETER Status
    Show status of all stacks

.EXAMPLE
    ./deploy.ps1 surveillance-testing
    Deploy a single stack

.EXAMPLE
    ./deploy.ps1 -All -Server frigate-gpu
    Deploy all stacks on frigate-gpu server

.EXAMPLE
    ./deploy.ps1 -List
    List all available stacks
#>

param(
    [Parameter(Position = 0)]
    [string]$Stack,

    [switch]$All,

    [ValidateSet("infra", "media-gpu", "frigate-gpu", "frigate", "omada")]
    [string]$Server,

    [switch]$DryRun,
    [switch]$List,
    [switch]$Status,
    [switch]$Help
)

# Configuration
$KOMODO_URL = $env:KOMODO_URL ?? "http://192.168.0.112:9120"
$KOMODO_API_KEY = $env:KOMODO_API_KEY
$KOMODO_API_SECRET = $env:KOMODO_API_SECRET

# Path to komodo.toml (relative to script location)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$KomodoTomlPath = Join-Path (Split-Path -Parent $ScriptDir) "komodo.toml"

function Show-Help {
    Get-Help $MyInvocation.PSCommandPath -Detailed
}

function Test-Credentials {
    if (-not $KOMODO_API_KEY -or -not $KOMODO_API_SECRET) {
        Write-Host "Error: KOMODO_API_KEY and KOMODO_API_SECRET must be set" -ForegroundColor Red
        Write-Host ""
        Write-Host "Get these from Komodo UI: Settings → Users → API Keys"
        exit 1
    }
}

function Invoke-KomodoAPI {
    param(
        [string]$Method,
        [string]$Endpoint,
        [object]$Body
    )

    $headers = @{
        "Content-Type"   = "application/json"
        "X-API-KEY"      = $KOMODO_API_KEY
        "X-API-SECRET"   = $KOMODO_API_SECRET
    }

    $uri = "$KOMODO_URL/$Endpoint"

    try {
        if ($Body) {
            $jsonBody = $Body | ConvertTo-Json -Depth 10
            $response = Invoke-RestMethod -Uri $uri -Method $Method -Headers $headers -Body $jsonBody
        }
        else {
            $response = Invoke-RestMethod -Uri $uri -Method $Method -Headers $headers
        }
        return $response
    }
    catch {
        Write-Host "API Error: $_" -ForegroundColor Red
        return $null
    }
}

function Get-StacksFromToml {
    if (-not (Test-Path $KomodoTomlPath)) {
        Write-Host "Error: komodo.toml not found at $KomodoTomlPath" -ForegroundColor Red
        exit 1
    }

    $content = Get-Content $KomodoTomlPath -Raw
    $stacks = @()

    # Simple TOML parsing for [[stack]] sections
    $stackMatches = [regex]::Matches($content, '\[\[stack\]\]([^\[]+)')

    foreach ($match in $stackMatches) {
        $section = $match.Groups[1].Value

        $name = if ($section -match 'name\s*=\s*"([^"]+)"') { $Matches[1] } else { "" }
        $serverId = if ($section -match 'server_id\s*=\s*"([^"]+)"') { $Matches[1] } else { "" }
        $tags = @()
        if ($section -match 'tags\s*=\s*\[([^\]]+)\]') {
            $tags = $Matches[1] -split ',' | ForEach-Object { $_.Trim().Trim('"') }
        }

        if ($name) {
            $stacks += [PSCustomObject]@{
                Name     = $name
                Server   = $serverId
                Tags     = $tags -join ", "
            }
        }
    }

    return $stacks
}

function Show-StackList {
    $stacks = Get-StacksFromToml

    Write-Host "Available Stacks in komodo.toml:" -ForegroundColor Cyan
    Write-Host ""

    $grouped = $stacks | Group-Object Server

    foreach ($group in $grouped | Sort-Object Name) {
        Write-Host "═══ $($group.Name) ═══" -ForegroundColor Yellow
        foreach ($stack in $group.Group | Sort-Object Name) {
            Write-Host "  $($stack.Name)" -ForegroundColor White
            if ($stack.Tags) {
                Write-Host "    Tags: $($stack.Tags)" -ForegroundColor DarkGray
            }
        }
        Write-Host ""
    }

    Write-Host "Total: $($stacks.Count) stacks" -ForegroundColor Green
}

function Deploy-Stack {
    param([string]$StackName)

    Write-Host "Deploying $StackName..." -ForegroundColor Cyan

    if ($DryRun) {
        Write-Host "[DRY RUN] Would deploy: $StackName" -ForegroundColor Yellow
        return $true
    }

    # Deploy via Komodo API
    $body = @{ stack = $StackName }
    $response = Invoke-KomodoAPI -Method "POST" -Endpoint "execute/DeployStack" -Body $body

    if ($response) {
        Write-Host "  ✓ Deployed: $StackName" -ForegroundColor Green
        return $true
    }
    else {
        Write-Host "  ✗ Failed: $StackName" -ForegroundColor Red
        return $false
    }
}

function Get-StackStatus {
    Write-Host "Fetching stack status from Komodo..." -ForegroundColor Cyan

    # List all stacks via API
    $response = Invoke-KomodoAPI -Method "POST" -Endpoint "read/ListStacks" -Body @{}

    if ($response) {
        Write-Host ""
        foreach ($stack in $response | Sort-Object { $_.config.server_id }, name) {
            $status = if ($stack.info.state -eq "Running") {
                Write-Host "  ✓ " -NoNewline -ForegroundColor Green
                "Running"
            }
            elseif ($stack.info.state -eq "Stopped") {
                Write-Host "  ○ " -NoNewline -ForegroundColor Yellow
                "Stopped"
            }
            else {
                Write-Host "  ? " -NoNewline -ForegroundColor Gray
                $stack.info.state ?? "Unknown"
            }
            Write-Host "$($stack.name) " -NoNewline -ForegroundColor White
            Write-Host "($($stack.config.server_id))" -ForegroundColor DarkGray
        }
    }
}

# Main
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor DarkCyan
Write-Host " Komodo Stack Deployer (Dev Workflow)" -ForegroundColor White
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor DarkCyan
Write-Host "URL: $KOMODO_URL" -ForegroundColor DarkGray
if ($DryRun) { Write-Host "MODE: DRY RUN" -ForegroundColor Yellow }
Write-Host ""

if ($Help) {
    Show-Help
    exit 0
}

if ($List) {
    Show-StackList
    exit 0
}

if ($Status) {
    Test-Credentials
    Get-StackStatus
    exit 0
}

if ($All) {
    Test-Credentials
    $stacks = Get-StacksFromToml

    if ($Server) {
        $stacks = $stacks | Where-Object { $_.Server -eq $Server }
        Write-Host "Deploying all stacks on $Server..." -ForegroundColor Cyan
    }
    else {
        Write-Host "Deploying ALL stacks..." -ForegroundColor Cyan
    }

    Write-Host ""

    $success = 0
    $failed = 0

    foreach ($stack in $stacks) {
        if (Deploy-Stack -StackName $stack.Name) {
            $success++
        }
        else {
            $failed++
        }
    }

    Write-Host ""
    Write-Host "Results: $success succeeded, $failed failed" -ForegroundColor $(if ($failed -eq 0) { "Green" } else { "Yellow" })
}
elseif ($Stack) {
    Test-Credentials
    Deploy-Stack -StackName $Stack
}
else {
    Write-Host "Usage: ./deploy.ps1 <stack-name> | -All [-Server <server>] | -List | -Status" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Gray
    Write-Host "  ./deploy.ps1 surveillance-testing      # Deploy single stack"
    Write-Host "  ./deploy.ps1 -All -Server frigate-gpu  # Deploy all on server"
    Write-Host "  ./deploy.ps1 -List                     # List available stacks"
    Write-Host "  ./deploy.ps1 -Status                   # Show stack status"
    Write-Host "  ./deploy.ps1 -All -DryRun              # Preview without deploying"
}
