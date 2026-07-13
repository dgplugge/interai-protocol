param(
    [string]$InstallDir = "C:\Program Files\InterAI\CompressionMVP",
    [string]$ReceiverListen = "127.0.0.1:9091",
    [string]$GatewayListen = "127.0.0.1:9090",
    [string]$ReceiverServiceName = "InterAICompressionReceiver",
    [string]$GatewayServiceName = "InterAICompressionGateway"
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
    Start-Sleep -Seconds 2
}

function Resolve-Go {
    $command = Get-Command go -ErrorAction SilentlyContinue
    if ($null -ne $command) {
        return $command.Source
    }
    $defaultPath = "C:\Program Files\Go\bin\go.exe"
    if (Test-Path -LiteralPath $defaultPath) {
        return $defaultPath
    }
    throw "Go was not found on PATH or at $defaultPath."
}

function Invoke-ScChecked([string[]]$Arguments) {
    $output = & sc.exe @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "sc.exe $($Arguments -join ' ') failed with exit code $LASTEXITCODE.`n$output"
    }
}

Assert-Admin
$go = Resolve-Go

$repoRoot = Split-Path -Parent $PSScriptRoot
$exeName = "interai-compression-gateway.exe"
$buildPath = Join-Path $repoRoot "bin\$exeName"
$installPath = Join-Path $InstallDir $exeName

New-Item -ItemType Directory -Path (Split-Path -Parent $buildPath) -Force | Out-Null
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

Push-Location $repoRoot
try {
    & $go build -o $buildPath .\cmd\compression-gateway
}
finally {
    Pop-Location
}

Copy-Item -LiteralPath $buildPath -Destination $installPath -Force

Remove-ServiceIfPresent $GatewayServiceName
Remove-ServiceIfPresent $ReceiverServiceName

$receiverBinPath = "`"$installPath`" -mode receiver -listen $ReceiverListen -service-name $ReceiverServiceName"
$gatewayBinPath = "`"$installPath`" -mode gateway -listen $GatewayListen -receiver $ReceiverListen -service-name $GatewayServiceName"

New-Service `
    -Name $ReceiverServiceName `
    -BinaryPathName $receiverBinPath `
    -DisplayName "InterAI Compression Receiver" `
    -StartupType Automatic | Out-Null

New-Service `
    -Name $GatewayServiceName `
    -BinaryPathName $gatewayBinPath `
    -DisplayName "InterAI Compression Gateway" `
    -StartupType Automatic `
    -DependsOn $ReceiverServiceName | Out-Null

Invoke-ScChecked @("failure", $ReceiverServiceName, "reset=", "60", "actions=", "restart/5000/restart/5000/`"`"/5000")
Invoke-ScChecked @("failure", $GatewayServiceName, "reset=", "60", "actions=", "restart/5000/restart/5000/`"`"/5000")

Start-Service -Name $ReceiverServiceName
Start-Service -Name $GatewayServiceName

Get-Service -Name $ReceiverServiceName, $GatewayServiceName |
    Select-Object Name, Status, StartType
