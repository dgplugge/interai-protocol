param(
    [string]$Gateway = "127.0.0.1:9090",
    [string]$Payload = "",
    [string]$Sender = "Forge",
    [string]$Receiver = "Pharos"
)

$ErrorActionPreference = "Stop"

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

$repoRoot = Split-Path -Parent $PSScriptRoot
$go = Resolve-Go

$args = @("run", ".\cmd\compression-smoke", "-gateway", $Gateway, "-sender", $Sender, "-receiver", $Receiver)
if ($Payload) {
    $args += @("-payload", $Payload)
}

Push-Location $repoRoot
try {
    & $go @args
}
finally {
    Pop-Location
}

