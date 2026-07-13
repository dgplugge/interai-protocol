param(
    [string]$Gateway = "127.0.0.1:9090",
    [string]$Sender = "Forge",
    [string]$Receiver = "Pharos",
    [switch]$IncludeServiceFailureTests,
    [string]$ReceiverServiceName = "InterAICompressionReceiver",
    [string]$GatewayServiceName = "InterAICompressionGateway"
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

function Test-IsAdmin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function New-JsonPayloadFile {
    param(
        [string]$Path,
        [int]$TargetBytes
    )

    $prefix = '{"sender":"Forge","receiver":"Pharos","data":"'
    $suffix = '"}'
    $fillerBytes = $TargetBytes - $prefix.Length - $suffix.Length
    if ($fillerBytes -lt 0) {
        throw "TargetBytes is too small for JSON wrapper."
    }
    $payload = $prefix + ("x" * $fillerBytes) + $suffix
    [System.IO.File]::WriteAllText($Path, $payload, [System.Text.UTF8Encoding]::new($false))
}

function Invoke-Smoke {
    param(
        [string]$PayloadPath = ""
    )

    $args = @(
        "run", ".\cmd\compression-smoke",
        "-gateway", $Gateway,
        "-sender", $Sender,
        "-receiver", $Receiver
    )
    if ($PayloadPath) {
        $args += @("-payload", $PayloadPath)
    }

    $output = & $script:Go @args 2>&1
    return [pscustomobject]@{
        ExitCode = $LASTEXITCODE
        Output = ($output -join [Environment]::NewLine)
    }
}

function Add-Result {
    param(
        [string]$Name,
        [bool]$Passed,
        [string]$Detail
    )
    $script:Results += [pscustomobject]@{
        Name = $Name
        Passed = $Passed
        Detail = $Detail
    }
}

function Assert-SmokePass {
    param(
        [string]$Name,
        [string]$PayloadPath = ""
    )

    $result = Invoke-Smoke -PayloadPath $PayloadPath
    if ($result.ExitCode -ne 0) {
        Add-Result $Name $false $result.Output
        return
    }
    try {
        $json = $result.Output | ConvertFrom-Json
        $passed = (
            $json.status -eq "PASS" -and
            $json.accepted -eq $true -and
            [double]$json.fidelity_percent -ge 95.0 -and
            [int64]$json.latency_micros -le 100000
        )
        $detail = "status=$($json.status); bytes=$($json.original_bytes); compressed=$($json.compressed_bytes); fidelity=$($json.fidelity_percent); latency_us=$($json.latency_micros)"
        Add-Result $Name $passed $detail
    }
    catch {
        Add-Result $Name $false "Could not parse smoke output: $($result.Output)"
    }
}

function Assert-SmokeFail {
    param(
        [string]$Name,
        [string]$PayloadPath = "",
        [string]$ExpectedText = ""
    )

    $result = Invoke-Smoke -PayloadPath $PayloadPath
    $passed = $result.ExitCode -ne 0
    if ($ExpectedText) {
        $passed = $passed -and $result.Output.Contains($ExpectedText)
    }
    Add-Result $Name $passed $result.Output
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$script:Go = Resolve-Go
$script:Results = @()
$tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("interai-compression-edge-" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

Push-Location $repoRoot
try {
    $smallPayload = Join-Path $tempDir "small.json"
    $nearLimitPayload = Join-Path $tempDir "near-limit.json"
    $overLimitPayload = Join-Path $tempDir "over-limit.json"
    $invalidPayload = Join-Path $tempDir "invalid.json"

    [System.IO.File]::WriteAllText($smallPayload, '{"ping":true}', [System.Text.UTF8Encoding]::new($false))
    New-JsonPayloadFile -Path $nearLimitPayload -TargetBytes (10 * 1024 * 1024 - 1)
    New-JsonPayloadFile -Path $overLimitPayload -TargetBytes (10 * 1024 * 1024 + 1)
    [System.IO.File]::WriteAllText($invalidPayload, '{"broken":', [System.Text.UTF8Encoding]::new($false))

    Assert-SmokePass -Name "generated-10mb"
    Assert-SmokePass -Name "small-json" -PayloadPath $smallPayload
    Assert-SmokePass -Name "near-limit-json" -PayloadPath $nearLimitPayload
    Assert-SmokeFail -Name "over-limit-json" -PayloadPath $overLimitPayload -ExpectedText "payload exceeds"
    Assert-SmokeFail -Name "invalid-json-file" -PayloadPath $invalidPayload -ExpectedText "not valid JSON"

    if ($IncludeServiceFailureTests) {
        if (-not (Test-IsAdmin)) {
            Add-Result "service-failure-tests" $false "Run as Administrator to stop/start Windows services."
        }
        else {
            try {
                Stop-Service -Name $ReceiverServiceName -Force
                Start-Sleep -Seconds 2
                Assert-SmokeFail -Name "receiver-down" -ExpectedText "transmit failed"
            }
            finally {
                Start-Service -Name $ReceiverServiceName
                Start-Sleep -Seconds 2
            }

            try {
                Stop-Service -Name $GatewayServiceName -Force
                Start-Sleep -Seconds 2
                Assert-SmokeFail -Name "gateway-down" -ExpectedText "transmit failed"
            }
            finally {
                Start-Service -Name $GatewayServiceName
                Start-Sleep -Seconds 2
            }

            Assert-SmokePass -Name "restart-recovery"
        }
    }
}
finally {
    Pop-Location
    Remove-Item -LiteralPath $tempDir -Recurse -Force -ErrorAction SilentlyContinue
}

$Results | Format-Table -AutoSize

$failed = @($Results | Where-Object { -not $_.Passed })
if ($failed.Count -gt 0) {
    throw "$($failed.Count) compression MVP edge case(s) failed."
}

Write-Host "All compression MVP edge cases passed."

