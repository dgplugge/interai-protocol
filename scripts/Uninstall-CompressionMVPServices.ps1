param(
    [string]$ReceiverServiceName = "InterAICompressionReceiver",
    [string]$GatewayServiceName = "InterAICompressionGateway",
    [string]$InstallDir = "C:\Program Files\InterAI\CompressionMVP"
)

$ErrorActionPreference = "Stop"

function Assert-Admin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Run this script from an elevated PowerShell session."
    }
}

function Remove-ServiceIfPresent([string]$Name) {
    $service = Get-Service -Name $Name -ErrorAction SilentlyContinue
    if ($null -eq $service) {
        return
    }
    if ($service.Status -ne "Stopped") {
        Stop-Service -Name $Name -Force -ErrorAction SilentlyContinue
        $service.WaitForStatus("Stopped", "00:00:20")
    }
    sc.exe delete $Name | Out-Null
}

Assert-Admin
Remove-ServiceIfPresent $GatewayServiceName
Remove-ServiceIfPresent $ReceiverServiceName

if (Test-Path -LiteralPath $InstallDir) {
    Remove-Item -LiteralPath $InstallDir -Recurse -Force
}

Write-Host "Removed InterAI compression MVP services."

