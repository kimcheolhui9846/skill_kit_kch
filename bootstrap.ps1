# Entry point for Windows PowerShell 5.1+. Hands off to the Python core when
# Python 3.9+ exists; otherwise copies AGENTS.md and the skills (shell-only mode).
# Keep this file ASCII-only: Windows PowerShell 5.1 reads BOM-less files as ANSI.

$KitRoot = $PSScriptRoot
$BeginMark = '<!-- hackathon-kit:begin -->'
$EndMark = '<!-- hackathon-kit:end -->'
$ProfileNames = @('core', 'python', 'data', 'web', 'full')

$Usage = @'
Usage: bootstrap.ps1 [--profile core|python|data|web|full] [--target DIR]
                     [--dry-run] [--offline] [--verify-only] [--no-mcp] [--verbose]

Installs AGENTS.md and the Codex skills into the target workspace
(default: current directory). Python 3.9+ enables verification, tools and MCP;
without Python only AGENTS.md and the skills are copied.

Exit codes:
  0   READY (or dry-run completed)
  1   PARTIAL - required items OK, optional items failed or unsupported
  2   BLOCKED - a required item failed or needs your decision
  64  invalid arguments
  65  target workspace missing or not a directory
'@

function Test-Python([string]$Exe, [string[]]$Prefix) {
    if (-not (Get-Command $Exe -ErrorAction SilentlyContinue)) { return $false }
    try {
        & $Exe @Prefix -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Write-Note([string]$Kind, [string]$Path) {
    Write-Output ('  {0,-9} {1}' -f $Kind, $Path)
}

function Write-Err([string]$Message) {
    [Console]::Error.WriteLine($Message)
}

function Stop-Blocked([string]$Message, [string]$Action) {
    Write-Err "error: $Message"
    Write-Output "Target:       $Target"
    Write-Output 'Mode:         shell-only (no Python 3.9+)'
    Write-Output 'Status:       BLOCKED'
    Write-Output 'Next action:'
    Write-Output "  - $Action"
    exit 2
}

$Subcommands = @('install', 'plan', 'verify', 'doctor', 'update', 'uninstall', 'restore',
    'profiles', 'source', 'capture', 'task', 'req', 'trace', 'report', 'recover', 'help', 'version')
$IsSubcommand = ($args.Count -gt 0) -and ($Subcommands -contains [string]$args[0])

if (-not $IsSubcommand) {
    foreach ($arg in $args) {
        if ($arg -eq '--help' -or $arg -eq '-h') { Write-Output $Usage; exit 0 }
    }
}

$Python = $null
if (Test-Path Env:KIT_PYTHON) {
    if (Test-Python $env:KIT_PYTHON @()) { $Python = @($env:KIT_PYTHON) }
} else {
    foreach ($cand in @('python3', 'python', 'py -3')) {
        $parts = @($cand -split ' ')
        $prefix = @($parts | Select-Object -Skip 1)
        if (Test-Python $parts[0] $prefix) { $Python = $parts; break }
    }
}

if ($null -ne $Python) {
    $env:KIT_SHELL = 'powershell'
    $prefix = @($Python | Select-Object -Skip 1)
    & $Python[0] @prefix -I (Join-Path $KitRoot 'run_kit.py') @args
    exit $LASTEXITCODE
}

# ---- shell-only mode -------------------------------------------------------
if ($IsSubcommand) {
    Write-Err "error: '$($args[0])' requires Python 3.9+ (shell-only mode supports only the legacy install)"
    exit 64
}
$Target = (Get-Location).Path
$DryRun = $false
$i = 0
while ($i -lt $args.Count) {
    $a = [string]$args[$i]
    if ($a -eq '--profile') {
        if ($i + 1 -ge $args.Count) { Write-Err 'error: --profile needs a value'; exit 64 }
        if ($ProfileNames -notcontains [string]$args[$i + 1]) {
            Write-Err "error: unknown profile: $($args[$i + 1])"; exit 64
        }
        $i += 2
    } elseif ($a -eq '--target') {
        if ($i + 1 -ge $args.Count) { Write-Err 'error: --target needs a value'; exit 64 }
        $Target = [string]$args[$i + 1]
        if ([string]::IsNullOrWhiteSpace($Target)) {
            Write-Err 'error: --target needs a non-empty directory'; exit 64
        }
        $i += 2
    } elseif ($a -eq '--dry-run') {
        $DryRun = $true
        $i += 1
    } elseif ($a -eq '--verify-only') {
        Write-Err 'error: --verify-only requires Python 3.9+ (shell-only mode cannot verify)'
        exit 64
    } elseif (@('--offline', '--no-mcp', '--verbose') -contains $a) {
        $i += 1
    } else {
        Write-Err "error: unknown argument: $a"
        Write-Err 'Run with --help for usage.'
        exit 64
    }
}

if (-not (Test-Path -LiteralPath $Target -PathType Container)) {
    Write-Err "error: target is not an existing directory: $Target"
    exit 65
}
$Target = (Resolve-Path -LiteralPath $Target).ProviderPath
$KitFull = (Resolve-Path -LiteralPath $KitRoot).ProviderPath
$Seps = [char[]]@(92, 47)
if ($Target.TrimEnd($Seps) -ieq $KitFull.TrimEnd($Seps)) {
    Write-Err 'error: target is the kit folder itself; run from your workspace or pass --target <workspace>'
    exit 65
}
$Utf8NoBom = New-Object System.Text.UTF8Encoding $false
$Conflict = $false

Write-Output 'Python 3.9+ not found: shell-only mode (copies AGENTS.md and skills; installs no tools).'

$AgentsPath = Join-Path $Target 'AGENTS.md'
if (Test-Path -LiteralPath $AgentsPath) {
    $existing = $null
    try { $existing = [System.IO.File]::ReadAllText($AgentsPath) } catch { $existing = $null }
    if ($null -ne $existing -and $existing.Contains($BeginMark)) {
        Write-Note 'SKIP' 'AGENTS.md (kit block present)'
    } else {
        Write-Note 'CONFLICT' 'AGENTS.md (exists; merging needs Python - add the kit block by hand)'
        $Conflict = $true
    }
} elseif ($DryRun) {
    Write-Note 'CREATE' 'AGENTS.md'
} else {
    $tmp = "$AgentsPath.kit-tmp"
    Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
    try {
        $body = [System.IO.File]::ReadAllText((Join-Path $KitRoot 'AGENTS.md')).Replace("`r`n", "`n").Trim()
        [System.IO.File]::WriteAllText($tmp, "$BeginMark`n$body`n$EndMark`n", $Utf8NoBom)
        Move-Item -LiteralPath $tmp -Destination $AgentsPath -ErrorAction Stop
    } catch {
        Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
        Stop-Blocked 'could not write AGENTS.md' "Check that $Target is writable, then re-run."
    }
    Write-Note 'CREATE' 'AGENTS.md'
}

$SkillsSrc = Join-Path $KitRoot '.agents\skills'
$SkillsDst = Join-Path $Target '.agents\skills'
foreach ($dir in Get-ChildItem -LiteralPath $SkillsSrc -Directory) {
    $dest = Join-Path $SkillsDst $dir.Name
    $rel = ".agents/skills/$($dir.Name)"
    if (Test-Path -LiteralPath $dest) {
        Write-Note 'SKIP' "$rel (exists, not checked)"
    } elseif ($DryRun) {
        Write-Note 'CREATE' $rel
    } else {
        $tmpDir = "$dest.kit-tmp"
        Remove-Item -LiteralPath $tmpDir -Recurse -Force -ErrorAction SilentlyContinue
        try {
            New-Item -ItemType Directory -Force -Path $SkillsDst -ErrorAction Stop | Out-Null
            Copy-Item -LiteralPath $dir.FullName -Destination $tmpDir -Recurse -ErrorAction Stop
            Move-Item -LiteralPath $tmpDir -Destination $dest -ErrorAction Stop
        } catch {
            Remove-Item -LiteralPath $tmpDir -Recurse -Force -ErrorAction SilentlyContinue
            Stop-Blocked "could not copy skill $($dir.Name)" "Check that $SkillsDst is writable, then re-run."
        }
        Write-Note 'CREATE' $rel
    }
}

Write-Output "Target:       $Target"
Write-Output 'Mode:         shell-only (no Python 3.9+)'
Write-Output 'Codex load:   UNVERIFIED (open Codex and run /skills)'
if ($DryRun) {
    Write-Output 'DRY RUN: nothing was written.'
    exit 0
}
if ($Conflict) {
    Write-Output 'Status:       BLOCKED'
    Write-Output 'Next action:'
    Write-Output "  - Add the kit block from $KitRoot\AGENTS.md to $AgentsPath by hand, or install Python 3.9+ and re-run."
    exit 2
}
Write-Output 'Status:       PARTIAL'
Write-Output 'Next action:'
Write-Output '  - Install Python 3.9+ and re-run to verify files and enable tools/MCP.'
Write-Output "  - Open Codex in $Target and run /skills to confirm the kit skills load."
exit 1
