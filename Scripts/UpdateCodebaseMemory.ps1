param(
    [switch]$IncludeUE,
    [int]$MemoryLimitMB = 10000,
    [int]$TimeoutSeconds = 2400
)

$ErrorActionPreference = "Stop"

$CbmExe = "C:\Users\dsm\AppData\Local\codebase-memory-mcp\codebase-memory-mcp.exe"
$ProjectRoot = "C:\Users\dsm\Desktop\RaiRaiRai"
$LogDir = "C:\Users\dsm\.codex\tmp\rairairai-cbm-safe"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Invoke-CbmIndex {
    param(
        [Parameter(Mandatory = $true)][string]$Project,
        [Parameter(Mandatory = $true)][string]$Root,
        [Parameter(Mandatory = $true)][ValidateSet("fast", "moderate", "full")][string]$Mode
    )

    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $out = Join-Path $LogDir "$Project-$stamp.out.log"
    $err = Join-Path $LogDir "$Project-$stamp.err.log"

    Write-Host "Indexing $Project ($Mode)"
    $process = Start-Process -FilePath $CbmExe `
        -ArgumentList @("cli", "index_repository", "--repo-path", $Root, "--name", $Project, "--mode", $Mode, "--persistence", "true") `
        -RedirectStandardOutput $out `
        -RedirectStandardError $err `
        -WindowStyle Hidden `
        -PassThru

    try { $process.PriorityClass = "BelowNormal" } catch {}

    $started = Get-Date
    while ($true) {
        Start-Sleep -Seconds 10

        $processes = @(Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -eq $process.Id -or $_.ParentProcessId -eq $process.Id })
        foreach ($child in $processes) {
            try { (Get-Process -Id $child.ProcessId -ErrorAction SilentlyContinue).PriorityClass = "BelowNormal" } catch {}
        }

        $ids = @($processes | Select-Object -ExpandProperty ProcessId)
        $live = @()
        if ($ids.Count -gt 0) {
            $live = @(Get-Process -Id $ids -ErrorAction SilentlyContinue)
        }

        $maxMemoryMB = 0
        if ($live.Count -gt 0) {
            $maxMemoryMB = ($live | Measure-Object -Property WorkingSet64 -Maximum).Maximum / 1MB
        }

        $elapsed = ((Get-Date) - $started).TotalSeconds
        if ($maxMemoryMB -gt $MemoryLimitMB) {
            foreach ($item in $live) {
                Stop-Process -Id $item.Id -Force -ErrorAction SilentlyContinue
            }
            throw "Aborted ${Project}: memory $([math]::Round($maxMemoryMB, 1)) MB exceeded limit $MemoryLimitMB MB."
        }

        if ($elapsed -gt $TimeoutSeconds) {
            foreach ($item in $live) {
                Stop-Process -Id $item.Id -Force -ErrorAction SilentlyContinue
            }
            throw "Aborted ${Project}: timeout $TimeoutSeconds seconds exceeded."
        }

        if (-not (Get-Process -Id $process.Id -ErrorAction SilentlyContinue)) {
            break
        }
    }

    Get-Content -LiteralPath $err -ErrorAction SilentlyContinue -Tail 5
    Get-Content -LiteralPath $out -ErrorAction SilentlyContinue -Tail 5
}

Invoke-CbmIndex -Project "RaiRaiRai" -Root $ProjectRoot -Mode "full"

if (-not $IncludeUE) {
    Write-Host "Project index updated. Pass -IncludeUE to refresh UE indexes."
    exit 0
}

$ueIndexes = @(
    @{ Project = "UE58-Runtime-Fast"; Root = "C:\Program Files\Epic Games\UE_5.8\Engine\Source\Runtime" },
    @{ Project = "UE58-Editor-Fast"; Root = "C:\Program Files\Epic Games\UE_5.8\Engine\Source\Editor" },
    @{ Project = "UE58-Developer-Fast"; Root = "C:\Program Files\Epic Games\UE_5.8\Engine\Source\Developer" },
    @{ Project = "UE58-Programs-Fast"; Root = "C:\Program Files\Epic Games\UE_5.8\Engine\Source\Programs" }
)

foreach ($index in $ueIndexes) {
    Invoke-CbmIndex -Project $index.Project -Root $index.Root -Mode "fast"
}
