# Starts the AICP Journal API server (api/server.py) via uvicorn in a
# detached console window so PowerShell's stderr-as-error wrapping does not
# mangle the startup logs. The detached window keeps running until you close
# it or the server crashes.
#
# Port 8080 by default. Pass a different port as the first argument if you
# need to avoid the viewer's port conflict (viewer/server.py is hardcoded
# to 8080). Example: .\Start-JournalAPI.ps1 8200

param(
    [int]$Port = 8080,
    [string]$BindHost = '127.0.0.1'
)

$repoRoot = 'H:\Code\interai-protocol'

Write-Host "Starting Journal API on http://${BindHost}:${Port} ..." -ForegroundColor Cyan

Start-Process python `
    -ArgumentList '-m', 'uvicorn', 'api.server:app', '--host', $BindHost, '--port', $Port `
    -WorkingDirectory $repoRoot

Start-Sleep -Seconds 2

try {
    $r = Invoke-RestMethod "http://${BindHost}:${Port}/" -Method GET -TimeoutSec 3
    Write-Host 'Server is responding.' -ForegroundColor Green
    Write-Host "  Title:   $($r.title)"
    Write-Host "  Version: $($r.version)"
} catch {
    Write-Host 'Server did not respond after 2s — may still be starting, or may have failed.' -ForegroundColor Yellow
    Write-Host 'Check the detached window for startup logs.'
}
