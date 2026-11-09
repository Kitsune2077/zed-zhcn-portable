<#
.SYNOPSIS
Build the Windows setup.exe with Inno Setup (ISCC).

The installer ships zed.exe plus first-run settings. The app itself still
keeps all user data in <install dir>\data (the portable layout), so the
installer defaults to %LOCALAPPDATA%\Programs\Zed-zhCN: a per-user directory
that is always writable without elevation.

.PARAMETER ZedRoot
Checked-out zed source tree containing target\release\zed.exe.

.PARAMETER Version
Release version shown to the user, e.g. 1.27.0.

.PARAMETER SeedSettings
settings.json seeded on first install (ui_locale: zh-CN for the official
pipeline, ui_language: zh-CN for the zed-ZH_CN fallback).

.PARAMETER DistDir
Directory receiving the setup.exe and its .sha256 file.

.PARAMETER UsageFile
Optional USAGE.txt shipped next to zed.exe.

.PARAMETER SetupIcon
Optional .ico for the installer; defaults to the icon in the zed source tree.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ZedRoot,
    [Parameter(Mandatory = $true)][string]$Version,
    [Parameter(Mandatory = $true)][string]$SeedSettings,
    [Parameter(Mandatory = $true)][string]$DistDir,
    [string]$UsageFile,
    [string]$SetupIcon
)

$ErrorActionPreference = 'Stop'

function Resolve-FullPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    return (Resolve-Path -LiteralPath $Path).ProviderPath
}

$repoRoot = Split-Path -Parent $PSScriptRoot

$zedRootFull = Resolve-FullPath $ZedRoot
$exe = Join-Path $zedRootFull 'target\release\zed.exe'
if (-not (Test-Path -LiteralPath $exe)) {
    throw "zed.exe not found: $exe"
}

$seed = Resolve-FullPath $SeedSettings
if (-not $UsageFile) { $UsageFile = Join-Path $repoRoot 'seed\USAGE.txt' }
$usage = Resolve-FullPath $UsageFile

if (-not (Test-Path -LiteralPath $DistDir)) {
    New-Item -ItemType Directory -Force -Path $DistDir | Out-Null
}
$dist = Resolve-FullPath $DistDir

if (-not $SetupIcon) {
    $candidate = Join-Path $zedRootFull 'crates\zed\resources\windows\app-icon.ico'
    if (Test-Path -LiteralPath $candidate) {
        $SetupIcon = Resolve-FullPath $candidate
    }
}

# Inno's VersionInfoVersion needs numeric x.y.z; fall back for branch/commit refs.
$numericVersion = if ($Version -match '^v?(\d+\.\d+\.\d+)') { $Matches[1] } else { '0.0.0' }
$safeVersion = ($Version -replace '[^0-9A-Za-z._-]', '-')

# ISCC.exe is preinstalled on GitHub-hosted Windows runners but is not on PATH.
$iscc = $null
$command = Get-Command 'iscc.exe' -ErrorAction SilentlyContinue
if ($command) { $iscc = $command.Source }
if (-not $iscc) {
    $candidates = @()
    $pf86 = ${env:ProgramFiles(x86)}
    if ($pf86) { $candidates += (Join-Path $pf86 'Inno Setup 6\ISCC.exe') }
    if ($env:ProgramFiles) { $candidates += (Join-Path $env:ProgramFiles 'Inno Setup 6\ISCC.exe') }
    $iscc = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $iscc) {
    throw 'Inno Setup compiler (ISCC.exe) not found; expected C:\Program Files (x86)\Inno Setup 6\ISCC.exe'
}

$iss = Join-Path $PSScriptRoot 'zed-zhcn.iss'
# Inno only treats a script as UTF-8 when it starts with a BOM. Normalize here
# so git EOL/encoding settings on the runner cannot break the Chinese strings.
$scriptText = [System.IO.File]::ReadAllText($iss)
[System.IO.File]::WriteAllText($iss, $scriptText, (New-Object System.Text.UTF8Encoding($true)))

$isccArgs = @(
    "/DZedVersion=$Version",
    "/DNumericVersion=$numericVersion",
    "/DSafeVersion=$safeVersion",
    "/DSourceExe=$exe",
    "/DSeedSettings=$seed",
    "/DUsageFile=$usage",
    "/DRepoRoot=$repoRoot",
    "/DOutputDir=$dist"
)
if ($SetupIcon) { $isccArgs += "/DSetupIcon=$SetupIcon" }

Write-Host "ISCC: $iscc"
Write-Host "Building Zed-zhCN-$safeVersion-setup-x64.exe"
& $iscc @isccArgs $iss
if ($LASTEXITCODE -ne 0) {
    throw "ISCC failed with exit code $LASTEXITCODE"
}

$setup = Join-Path $dist "Zed-zhCN-$safeVersion-setup-x64.exe"
if (-not (Test-Path -LiteralPath $setup)) {
    throw "installer was not produced: $setup"
}

$hash = (Get-FileHash -LiteralPath $setup -Algorithm SHA256).Hash.ToLower()
"$hash  $([System.IO.Path]::GetFileName($setup))" |
    Out-File -FilePath "$setup.sha256" -Encoding ascii -NoNewline

$sizeMb = [math]::Round((Get-Item -LiteralPath $setup).Length / 1MB, 1)
Write-Host "setup installer: $setup ($sizeMb MB)"
