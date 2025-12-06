# Quick test script to check vratnik stream status (PowerShell version)

# Prompt for IP address
Write-Host "Enter the IP address to test (default: localhost for frigate-test):" -ForegroundColor Yellow
$ipAddress = Read-Host "IP Address"
if ([string]::IsNullOrWhiteSpace($ipAddress)) {
    $ipAddress = "localhost"
}

# Determine ports based on IP
if ($ipAddress -eq "localhost" -or $ipAddress -eq "127.0.0.1") {
    $frigatePort = "5011"
    $go2rtcPort = "1984"
    $containerName = "frigate-test"
} else {
    $frigatePort = "5000"
    $go2rtcPort = "1984"
    $containerName = "frigate"
}

Write-Host ""
Write-Host "=== Testing Frigate at $ipAddress ===" -ForegroundColor Cyan
Write-Host ""

# Check if container is running (only for local testing)
if ($ipAddress -eq "localhost" -or $ipAddress -eq "127.0.0.1") {
    $container = docker ps --filter "name=$containerName" --format "{{.Names}}"
    if (-not $container) {
        Write-Host "❌ Container '$containerName' is not running" -ForegroundColor Red
        Write-Host "   Run: docker-compose up -d"
        exit 1
    }
    Write-Host "✅ Container is running" -ForegroundColor Green
    Write-Host ""
}

# Check go2rtc API
Write-Host "=== go2rtc Stream Status ===" -ForegroundColor Cyan
try {
    $response = Invoke-RestMethod -Uri "http://${ipAddress}:${go2rtcPort}/api/streams" -ErrorAction Stop

    $connectedProducers = @()
    $configuredProducers = @()

    foreach ($producer in $response.vratnik.producers) {
        if ($producer.id) {
            $medias = $producer.medias -join ", "
            $connectedProducers += $producer
            Write-Host "✅ Producer $($producer.id): $($producer.format_name) - Connected" -ForegroundColor Green
            Write-Host "   Remote: $($producer.remote_addr)" -ForegroundColor Gray
            Write-Host "   Media: $medias" -ForegroundColor Gray
        } else {
            $configuredProducers += $producer
        }
    }

    Write-Host ""
    Write-Host "Summary: $($connectedProducers.Count) active / $($response.vratnik.producers.Count) configured" -ForegroundColor Cyan

    # Check for backchannel
    $hasBackchannel = $false
    foreach ($producer in $connectedProducers) {
        if ($producer.medias -match "sendonly") {
            $hasBackchannel = $true
            break
        }
    }

    if ($hasBackchannel) {
        Write-Host "✅ Backchannel: ACTIVE (two-way audio enabled)" -ForegroundColor Green
    } else {
        Write-Host "❌ Backchannel: INACTIVE (no sendonly audio)" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Failed to connect to go2rtc API: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== Detailed vratnik Stream Info ===" -ForegroundColor Cyan
try {
    $vratnik = (Invoke-RestMethod -Uri "http://${ipAddress}:${go2rtcPort}/api/streams").vratnik
    $vratnik | ConvertTo-Json -Depth 10
} catch {
    Write-Host "❌ Failed to get stream info: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== Access Points ===" -ForegroundColor Cyan
Write-Host "Frigate UI:     http://${ipAddress}:${frigatePort}"
Write-Host "go2rtc Web UI:  http://${ipAddress}:${go2rtcPort}"
Write-Host "go2rtc API:     http://${ipAddress}:${go2rtcPort}/api/streams"

Write-Host ""
if ($ipAddress -eq "localhost" -or $ipAddress -eq "127.0.0.1") {
    Write-Host "=== Recent Logs (last 20 lines) ===" -ForegroundColor Cyan
    docker-compose logs --tail=20 $containerName
}
