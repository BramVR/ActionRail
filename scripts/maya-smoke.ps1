[CmdletBinding()]
param(
    [string[]] $Script = @("actionrail_phase0_smoke.py"),
    [string] $StateDir = ".gg-maya-sessiond",
    [int] $Port = 7217,
    [int] $Timeout = 180,
    [string] $SessiondPython = "",
    [string] $MayaExe = "",
    [switch] $NoStart,
    [switch] $SkipDoctor,
    [switch] $StopAfter
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$SmokeDir = (Resolve-Path (Join-Path $RepoRoot "tests/maya_smoke")).Path
$CleanupScript = Join-Path $SmokeDir "actionrail_cleanup_state.py"

if (-not $SessiondPython) {
    $SessiondPython = Join-Path $RepoRoot "../GG_MayaSessiond/.venv/Scripts/python.exe"
}
$SessiondPython = [System.IO.Path]::GetFullPath($SessiondPython)

function Resolve-RepoRelativePath {
    param([Parameter(Mandatory = $true)][string] $Path)

    if ([System.IO.Path]::IsPathRooted($Path)) {
        return [System.IO.Path]::GetFullPath($Path)
    }

    return [System.IO.Path]::GetFullPath((Join-Path $RepoRoot $Path))
}

$StateDir = Resolve-RepoRelativePath $StateDir

if (-not (Test-Path -LiteralPath $SessiondPython -PathType Leaf)) {
    throw "Sessiond Python was not found: $SessiondPython"
}

function Invoke-SessiondJson {
    param(
        [Parameter(Mandatory = $true)][string[]] $Arguments,
        [switch] $AllowNonZeroExit
    )

    $output = & $SessiondPython -m gg_maya_sessiond.cli @Arguments 2>&1
    $exitCode = $LASTEXITCODE
    $text = ($output | Out-String).Trim()

    if (-not $text) {
        if ($exitCode -ne 0 -and -not $AllowNonZeroExit) {
            throw "Sessiond command failed with exit code ${exitCode}: $($Arguments -join ' ')"
        }
        return $null
    }

    try {
        $payload = $text | ConvertFrom-Json
    }
    catch {
        throw "Sessiond command returned non-JSON output for '$($Arguments -join ' ')':`n$text"
    }

    if ($exitCode -ne 0 -and -not $AllowNonZeroExit) {
        throw "Sessiond command failed with exit code ${exitCode}: $($Arguments -join ' ')`n$text"
    }

    return $payload
}

function Resolve-SmokeScripts {
    $resolved = New-Object System.Collections.Generic.List[string]

    foreach ($entry in $Script) {
        if ($entry -eq "all") {
            Get-ChildItem -LiteralPath $SmokeDir -Filter "*_smoke.py" |
                Sort-Object Name |
                ForEach-Object { $resolved.Add($_.FullName) }
            continue
        }

        $candidate = $entry
        if (-not [System.IO.Path]::HasExtension($candidate)) {
            $candidate = "$candidate.py"
        }

        if ([System.IO.Path]::IsPathRooted($candidate)) {
            $path = [System.IO.Path]::GetFullPath($candidate)
        }
        elseif ($candidate.Contains("/") -or $candidate.Contains("\")) {
            $path = [System.IO.Path]::GetFullPath((Join-Path $RepoRoot $candidate))
        }
        else {
            $path = [System.IO.Path]::GetFullPath((Join-Path $SmokeDir $candidate))
        }

        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Smoke script was not found: $entry"
        }

        $resolved.Add((Resolve-Path -LiteralPath $path).Path)
    }

    if ($resolved.Count -eq 0) {
        throw "No smoke scripts were selected."
    }

    return $resolved.ToArray()
}

function Get-SessionStatus {
    return Invoke-SessiondJson @("status", "--state-dir", $StateDir, "--json") -AllowNonZeroExit
}

function Start-SessionIfNeeded {
    $status = Get-SessionStatus
    if ($status -and $status.derived_status -eq "running") {
        Write-Host "MayaSessiond already running on port $($status.state.port)."
        return
    }

    if ($NoStart) {
        throw "MayaSessiond is not running for state dir '$StateDir'. Remove -NoStart to launch it."
    }

    if (-not $SkipDoctor) {
        Write-Host "Running MayaSessiond doctor."
        Invoke-SessiondJson @(
            "doctor",
            "--state-dir", $StateDir,
            "--mcp-python", $SessiondPython,
            "--json"
        ) | Out-Null
    }

    if (Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue) {
        $portInUse = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
            Where-Object { $_.State -eq "Listen" }
        if ($portInUse) {
            throw "Port $Port is already in use. Pass -Port with a free ActionRail Sessiond port."
        }
    }

    Write-Host "Starting MayaSessiond on port $Port."
    $args = @(
        "start",
        "--state-dir", $StateDir,
        "--port", "$Port",
        "--mcp-python", $SessiondPython,
        "--maya-module-path", $RepoRoot,
        "--mcp-script-dirs", $SmokeDir,
        "--json"
    )
    if ($MayaExe) {
        $args += @("--maya-exe", (Resolve-RepoRelativePath $MayaExe))
    }

    Invoke-SessiondJson $args | Out-Null
}

function Assert-SmokeToolAvailable {
    Write-Host "Discovering MCP tools."
    $tools = Invoke-SessiondJson @("call", "--state-dir", $StateDir, "--list", "--json")
    if (-not $tools.ok -or -not ($tools.tool_names -contains "script.execute")) {
        throw "MCP tool discovery did not report script.execute."
    }
}

function Invoke-SmokeScript {
    param([Parameter(Mandatory = $true)][string] $Path)

    $name = Split-Path -Leaf $Path
    Write-Host "Running $name through script.execute."

    $structured = Invoke-ApprovedScript -Path $Path -Label $name

    $summary = ($structured.output | Out-String).Trim()
    if ($summary) {
        try {
            $summary = ($summary | ConvertFrom-Json) | ConvertTo-Json -Compress -Depth 12
        }
        catch {
            # Keep plain output when a smoke script intentionally prints text.
        }
        Write-Host "PASS $name $summary"
    }
    else {
        Write-Host "PASS $name"
    }
}

function Invoke-ApprovedScript {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][string] $Label
    )

    $expectedPath = [System.IO.Path]::GetFullPath($Path)
    $lastResult = $null

    for ($attempt = 1; $attempt -le 3; $attempt++) {
        $result = Invoke-SessiondJson @(
            "call",
            "--state-dir", $StateDir,
            "script.execute",
            "file_path=$expectedPath",
            "timeout=$Timeout",
            "--json"
        ) -AllowNonZeroExit
        $lastResult = $result

        if (-not $result.ok) {
            if ($attempt -lt 3) {
                Write-Host "Retrying $Label after script.execute transport failure."
                Start-Sleep -Seconds 1
                continue
            }
            throw "script.execute failed for ${Label}: $($result | ConvertTo-Json -Depth 8)"
        }

        $structured = $result.structured
        $actualPath = ""
        if ($structured -and $structured.script) {
            $actualPath = [System.IO.Path]::GetFullPath([string] $structured.script)
        }
        if ($actualPath -and $actualPath -ine $expectedPath) {
            if ($attempt -lt 3) {
                Write-Host "Retrying $Label after stale script.execute payload for $actualPath."
                Start-Sleep -Seconds 1
                continue
            }
            throw "script.execute returned stale payload for ${Label}: $($result | ConvertTo-Json -Depth 8)"
        }

        if (-not $structured -or -not $structured.success) {
            throw "Script failed for ${Label}: $($structured | ConvertTo-Json -Depth 8)"
        }

        return $structured
    }

    throw "script.execute failed for ${Label}: $($lastResult | ConvertTo-Json -Depth 8)"
}

function Invoke-SmokeCleanup {
    param([Parameter(Mandatory = $true)][string] $Reason)

    if (-not (Test-Path -LiteralPath $CleanupScript -PathType Leaf)) {
        throw "Smoke cleanup script was not found: $CleanupScript"
    }

    Write-Host "Cleaning Maya smoke state ($Reason)."
    Invoke-ApprovedScript -Path $CleanupScript -Label "cleanup" | Out-Null
}

$selectedScripts = Resolve-SmokeScripts

try {
    Start-SessionIfNeeded
    Assert-SmokeToolAvailable

    foreach ($path in $selectedScripts) {
        $name = Split-Path -Leaf $path
        Invoke-SmokeCleanup "before $name"
        try {
            Invoke-SmokeScript $path
        }
        finally {
            Invoke-SmokeCleanup "after $name"
        }
    }
}
finally {
    if ($StopAfter) {
        Write-Host "Stopping MayaSessiond."
        Invoke-SessiondJson @("stop", "--state-dir", $StateDir, "--json") | Out-Null
    }
}
