#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Extract environment variables from all running containers across all servers.

.DESCRIPTION
    This script SSHs to each Portainer LXC and extracts environment variables
    from running containers using docker inspect.

    Output is saved to secrets.env (or specified file) in KEY=VALUE format.
    Sensitive values are included - DELETE FILE AFTER USE.

.PARAMETER OutputFile
    Path to output file (default: secrets.env)

.PARAMETER Server
    Extract from specific server only (infra, media-gpu, frigate-gpu, frigate, omada)

.PARAMETER Raw
    Output raw env vars without filtering common non-secrets

.EXAMPLE
    ./extract-secrets.ps1

.EXAMPLE
    ./extract-secrets.ps1 -Server infra -OutputFile infra-secrets.env
#>

param(
    [string]$OutputFile = "secrets.env",
    [ValidateSet("infra", "media-gpu", "frigate-gpu", "frigate", "omada")]
    [string]$Server,
    [switch]$Raw
)

# Server definitions
$Servers = @{
    "infra"       = "192.168.0.112"
    "media-gpu"   = "192.168.0.212"
    "frigate-gpu" = "192.168.0.115"
    "frigate"     = "192.168.0.235"
    "omada"       = "192.168.0.238"
}

# Common env vars to filter out (not secrets)
$FilterPatterns = @(
    '^PATH=',
    '^HOME=',
    '^HOSTNAME=',
    '^LANG=',
    '^LC_',
    '^TERM=',
    '^SHLVL=',
    '^PWD=',
    '^_=',
    '^container=',
    '^NVIDIA_',
    '^CUDA_',
    '^LD_LIBRARY_PATH=',
    '^PUID=',
    '^PGID=',
    '^TZ=',
    '^UMASK='
)

function Get-ContainerEnvVars {
    param(
        [string]$ServerName,
        [string]$ServerIP
    )

    Write-Host "Extracting from $ServerName ($ServerIP)..." -ForegroundColor Cyan

    $remoteScript = @'
for container in $(docker ps --format '{{.Names}}'); do
    stack=$(docker inspect --format='{{index .Config.Labels "com.docker.compose.project"}}' "$container" 2>/dev/null || echo "standalone")
    echo "CONTAINER:$container:$stack"
    docker inspect --format='{{range .Config.Env}}{{println .}}{{end}}' "$container" 2>/dev/null
    echo "END_CONTAINER"
done
'@

    try {
        $result = ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no "root@$ServerIP" $remoteScript 2>$null
        return $result
    }
    catch {
        Write-Warning "Failed to connect to $ServerName ($ServerIP): $_"
        return $null
    }
}

function Format-Output {
    param(
        [string]$ServerName,
        [string]$ServerIP,
        [string[]]$RawOutput
    )

    $output = @()
    $output += "# ============================================="
    $output += "# Server: $ServerName ($ServerIP)"
    $output += "# ============================================="
    $output += ""

    $currentContainer = ""
    $currentStack = ""

    foreach ($line in $RawOutput) {
        if ($line -match '^CONTAINER:(.+):(.*)$') {
            $currentContainer = $Matches[1]
            $currentStack = $Matches[2]
            if ([string]::IsNullOrEmpty($currentStack)) { $currentStack = "standalone" }
            $output += "# --- Container: $currentContainer (Stack: $currentStack) ---"
        }
        elseif ($line -eq "END_CONTAINER") {
            $output += ""
            $currentContainer = ""
        }
        elseif (-not [string]::IsNullOrWhiteSpace($line) -and $currentContainer) {
            # Filter out common non-secret env vars unless -Raw
            if ($Raw) {
                $output += $line
            }
            else {
                $shouldFilter = $false
                foreach ($pattern in $FilterPatterns) {
                    if ($line -match $pattern) {
                        $shouldFilter = $true
                        break
                    }
                }
                if (-not $shouldFilter) {
                    $output += $line
                }
            }
        }
    }

    return $output
}

# Main execution
$allOutput = @()
$allOutput += "# Komodo Migration - Extracted Environment Variables"
$allOutput += "# Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
$allOutput += "# WARNING: Contains sensitive data - DELETE AFTER USE"
$allOutput += ""

$serversToProcess = if ($Server) {
    @{ $Server = $Servers[$Server] }
} else {
    $Servers
}

foreach ($serverName in $serversToProcess.Keys) {
    $serverIP = $serversToProcess[$serverName]

    $rawOutput = Get-ContainerEnvVars -ServerName $serverName -ServerIP $serverIP

    if ($rawOutput) {
        $formatted = Format-Output -ServerName $serverName -ServerIP $serverIP -RawOutput $rawOutput
        $allOutput += $formatted
        $allOutput += ""
    }
}

# Write to file
$allOutput | Out-File -FilePath $OutputFile -Encoding UTF8

Write-Host ""
Write-Host "Secrets extracted to: $OutputFile" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Review $OutputFile and identify secrets needed for Komodo"
Write-Host "2. Add secrets to core.config.toml [secrets] section"
Write-Host "3. DELETE $OutputFile when done (contains sensitive data)"
Write-Host ""

# Summary of what was found
$secretsFound = (Get-Content $OutputFile | Where-Object { $_ -match '=' -and $_ -notmatch '^#' }).Count
Write-Host "Found approximately $secretsFound environment variables" -ForegroundColor Cyan
