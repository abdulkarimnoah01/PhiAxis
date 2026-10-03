<#
.SYNOPSIS
  Installs (or updates, or removes) PhiAxis for every Houdini 20.5 - 22 on this PC.

.DESCRIPTION
  Copies the plugin into  %LOCALAPPDATA%\PhiAxis\versions\<version>  and writes one small
  package file, phiaxis.json, into each Houdini preferences folder (Documents\houdiniX.Y\
  packages). Running a newer release the same way updates it; the previous version is kept
  for one release so it can be rolled back. Your settings and presets live in your Houdini
  preferences and are never touched. No administrator rights are needed.

  Double-click "Install PhiAxis.cmd" for the normal case. Options:
    -Houdini 22.0,21.0   only these versions (default: every supported one found)
    -CreatePrefs         also prepare versions whose preferences folder does not exist yet
    -KeepLegacy          leave an old composition_guides.json package file alone
    -Uninstall           remove PhiAxis (settings are kept)
    -Quiet               no prompts or pause (used by the in-Houdini updater)
    -Documents, -InstallRoot   other locations (used for testing; the PHIAXIS_DOCUMENTS
                               variable sets the default for -Documents)
#>
[CmdletBinding()]
param(
    [string]$Documents = $(if ($env:PHIAXIS_DOCUMENTS) { $env:PHIAXIS_DOCUMENTS } else { [Environment]::GetFolderPath('MyDocuments') }),
    [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA 'PhiAxis'),
    [string[]]$Houdini = @(),
    [switch]$CreatePrefs,
    [switch]$KeepLegacy,
    [switch]$Uninstall,
    [switch]$Quiet
)
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$payload = Join-Path $here 'payload'
$Utf8 = New-Object System.Text.UTF8Encoding($false)

function Say($text) { Write-Host $text }
function Parse-Version([string]$text) {
    if ($text -match '^\s*v?(\d+)\.(\d+)(?:\.(\d+))?') {
        return [version]::new([int]$Matches[1], [int]$Matches[2], $(if ($Matches[3]) { [int]$Matches[3] } else { 0 }))
    }
    return $null
}
function Supported([int]$major, [int]$minor, $info) {
    $low = Parse-Version $info.houdini.min; $high = Parse-Version $info.houdini.max_exclusive
    $v = [version]::new($major, $minor, 0)
    return ($v -ge [version]::new($low.Major, $low.Minor, 0)) -and ($v -lt [version]::new($high.Major, $high.Minor, 0))
}
function Find-Prefs($info) {
    $found = @()
    if (-not (Test-Path $Documents)) { return $found }
    foreach ($dir in Get-ChildItem -Path $Documents -Directory -ErrorAction SilentlyContinue) {
        if ($dir.Name -match '^houdini(\d+)\.(\d+)$') {
            $label = '{0}.{1}' -f $Matches[1], $Matches[2]
            if ($Houdini.Count -gt 0 -and $Houdini -notcontains $label) { continue }
            if (Supported ([int]$Matches[1]) ([int]$Matches[2]) $info) {
                $found += [pscustomobject]@{ Label = $label; Path = $dir.FullName }
            }
        }
    }
    if ($CreatePrefs) {
        foreach ($label in $Houdini) {
            $path = Join-Path $Documents ("houdini$label")
            if (-not (Test-Path $path) -and $label -match '^(\d+)\.(\d+)$' -and
                (Supported ([int]$Matches[1]) ([int]$Matches[2]) $info)) {
                New-Item -ItemType Directory -Path $path | Out-Null
                $found += [pscustomobject]@{ Label = $label; Path = $path }
            }
        }
    }
    return $found
}
function Finish([int]$code) {
    if (-not $Quiet) { Read-Host 'Press Enter to close' | Out-Null }
    exit $code
}

# ---------------------------------------------------------------- uninstall
if ($Uninstall) {
    $record = Join-Path $InstallRoot 'installed.json'
    $targets = @()
    if (Test-Path $record) { $targets += (Get-Content $record -Raw | ConvertFrom-Json).prefs }
    if (Test-Path $Documents) {
        foreach ($dir in Get-ChildItem -Path $Documents -Directory -ErrorAction SilentlyContinue) {
            if ($dir.Name -match '^houdini\d+\.\d+$') { $targets += $dir.FullName }
        }
    }
    foreach ($prefs in ($targets | Select-Object -Unique)) {
        $file = Join-Path $prefs 'packages\phiaxis.json'
        if (Test-Path $file) { Remove-Item $file -Force; Say "Removed $file" }
    }
    if (Test-Path $InstallRoot) { Remove-Item $InstallRoot -Recurse -Force; Say "Removed $InstallRoot" }
    Say 'PhiAxis is removed. Your saved settings and presets (composition_guides.json in your'
    Say 'Houdini preferences folder) were kept. Restart Houdini.'
    Finish 0
}

# ------------------------------------------------------------------ install
if (-not (Test-Path (Join-Path $payload 'VERSION.json'))) {
    Say 'This installer must be run from the unpacked PhiAxis folder (payload\VERSION.json is missing).'
    Finish 1
}
$info = Get-Content (Join-Path $payload 'VERSION.json') -Raw | ConvertFrom-Json
Say ("Installing PhiAxis {0}" -f $info.version)

$prefsList = @(Find-Prefs $info)
if ($prefsList.Count -eq 0) {
    Say ("No Houdini {0} to {1} preferences folder was found in {2}." -f $info.houdini.min, $info.houdini.max_exclusive, $Documents)
    Say 'Start Houdini once so it creates its preferences folder, then run this again,'
    Say 'or run it with  -CreatePrefs -Houdini 22.0  to prepare a version in advance.'
    Finish 1
}

$destination = Join-Path $InstallRoot ('versions\' + $info.version)
if (Test-Path $destination) { Remove-Item $destination -Recurse -Force }
New-Item -ItemType Directory -Path $destination -Force | Out-Null
Copy-Item -Path (Join-Path $payload '*') -Destination $destination -Recurse -Force

$posix = $destination -replace '\\', '/'
$package = @"
{
    "enable": "houdini_version >= '$($info.houdini.min)' and houdini_version < '$($info.houdini.max_exclusive)'",
    "env": [
        {"PHIAXIS": "$posix"},
        {"PYTHONPATH": {"value": "`$PHIAXIS/python3.10libs", "method": "prepend"}}
    ],
    "path": "`$PHIAXIS"
}
"@
$done = @()
foreach ($prefs in $prefsList) {
    $packages = Join-Path $prefs.Path 'packages'
    New-Item -ItemType Directory -Path $packages -Force | Out-Null
    [System.IO.File]::WriteAllText((Join-Path $packages 'phiaxis.json'), $package, $Utf8)
    $legacy = Join-Path $packages 'composition_guides.json'
    if ((Test-Path $legacy) -and -not $KeepLegacy) {
        Move-Item $legacy ($legacy + '.bak-' + (Get-Date -Format 'yyyyMMdd')) -Force
        Say ("  Houdini {0}: the old composition_guides.json package was set aside (it would load a second copy)." -f $prefs.Label)
    }
    Say ("  Houdini {0}: ready ({1})" -f $prefs.Label, $packages)
    $done += $prefs.Path
}

# Keep this version and the one before it (a one-step rollback); remove older ones.
$versionsRoot = Join-Path $InstallRoot 'versions'
$kept = Get-ChildItem $versionsRoot -Directory | Where-Object { Parse-Version $_.Name } |
        Sort-Object { Parse-Version $_.Name } -Descending
foreach ($old in ($kept | Select-Object -Skip 2)) { Remove-Item $old.FullName -Recurse -Force }

if (Test-Path (Join-Path $payload 'update_source.txt')) {
    Copy-Item (Join-Path $payload 'update_source.txt') (Join-Path $InstallRoot 'update_source.txt') -Force
}
$record = [ordered]@{ version = $info.version; path = $posix; prefs = $done;
                      installed = (Get-Date -Format 'yyyy-MM-dd HH:mm') } | ConvertTo-Json
[System.IO.File]::WriteAllText((Join-Path $InstallRoot 'installed.json'), $record, $Utf8)

Say ''
Say ("PhiAxis {0} is installed for Houdini {1}." -f $info.version, (($prefsList | ForEach-Object { $_.Label }) -join ', '))
if (Get-Process houdini -ErrorAction SilentlyContinue) {
    Say 'Houdini is running: restart it to load this version.'
}
Say 'In Houdini add the PhiAxis shelf from the shelf "+" menu (Shelves > PhiAxis).'
Finish 0
