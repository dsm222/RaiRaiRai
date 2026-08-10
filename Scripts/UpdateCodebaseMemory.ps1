param(
    [switch]$IncludeUE,
    [int]$MemoryLimitMB = 2200,
    [int]$TimeoutSeconds = 420
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
    @{ Project = "UE58-CoreEssential-Fast"; Root = "C:\Users\dsm\Desktop\UE58-CoreEssential.fast-view" },
    @{ Project = "UE58-UI-Fast"; Root = "C:\Users\dsm\Desktop\UE58-UI.fast-view" },
    @{ Project = "UE58-Chaos-Fast"; Root = "C:\Users\dsm\Desktop\UE58-Chaos.fast-view" },
    @{ Project = "UE58-EngineAPI-Fast"; Root = "C:\Users\dsm\Desktop\UE58-EngineAPI.fast-view" },
    @{ Project = "UE58-EnginePrivateCore-Fast"; Root = "C:\Users\dsm\Desktop\UE58-EnginePrivateCore.fast-view" },
    @{ Project = "UE58-EnginePrivateAnimation-Fast"; Root = "C:\Users\dsm\Desktop\UE58-EnginePrivateAnimation.fast-view" },
    @{ Project = "UE58-EnginePrivateRendering-Fast"; Root = "C:\Users\dsm\Desktop\UE58-EnginePrivateRendering.fast-view" },
    @{ Project = "UE58-EnginePrivateWorld-Fast"; Root = "C:\Users\dsm\Desktop\UE58-EnginePrivateWorld.fast-view" },
    @{ Project = "UE58-EnginePrivateOther-Fast"; Root = "C:\Users\dsm\Desktop\UE58-EnginePrivateOther.fast-view" },
    @{ Project = "UE58-RuntimeOther-AC-Fast"; Root = "C:\Users\dsm\Desktop\UE58-RuntimeOther-AC.fast-view" },
    @{ Project = "UE58-RuntimeOther-DH-Fast"; Root = "C:\Users\dsm\Desktop\UE58-RuntimeOther-DH.fast-view" },
    @{ Project = "UE58-RuntimeOther-IM-Fast"; Root = "C:\Users\dsm\Desktop\UE58-RuntimeOther-IM.fast-view" },
    @{ Project = "UE58-RuntimeOther-NR-Fast"; Root = "C:\Users\dsm\Desktop\UE58-RuntimeOther-NR.fast-view" },
    @{ Project = "UE58-RuntimeOther-SZ-Fast"; Root = "C:\Users\dsm\Desktop\UE58-RuntimeOther-SZ.fast-view" },
    @{ Project = "UE58-Editor-AF-Fast"; Root = "C:\Users\dsm\Desktop\UE58-Editor-AF.fast-view" },
    @{ Project = "UE58-Editor-GM-Fast"; Root = "C:\Users\dsm\Desktop\UE58-Editor-GM.fast-view" },
    @{ Project = "UE58-Editor-NS-Fast"; Root = "C:\Users\dsm\Desktop\UE58-Editor-NS.fast-view" },
    @{ Project = "UE58-Editor-TZ-Fast"; Root = "C:\Users\dsm\Desktop\UE58-Editor-TZ.fast-view" },
    @{ Project = "UE58-Developer-AM-Fast"; Root = "C:\Users\dsm\Desktop\UE58-Developer-AM.fast-view" },
    @{ Project = "UE58-Developer-NZ-Fast"; Root = "C:\Users\dsm\Desktop\UE58-Developer-NZ.fast-view" },
    @{ Project = "UE58-Programs-Fast"; Root = "C:\Users\dsm\Desktop\UE58-Programs.fast-view" }
)

foreach ($index in $ueIndexes) {
    Invoke-CbmIndex -Project $index.Project -Root $index.Root -Mode "fast"
}
