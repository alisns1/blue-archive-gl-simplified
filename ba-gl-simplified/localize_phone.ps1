# localize_phone.ps1 -- Blue Archive GL: Traditional Chinese -> Simplified Chinese, on-device.
#
# Ported from a working setup; contains no machine-specific paths.
# Requirements: adb in PATH, python 3.9+ with `pip install -r requirements.txt`.
#
# ASCII-only source on purpose: Windows PowerShell decodes BOM-less .ps1 files as ANSI,
# and non-ASCII bytes can break the parser.
param(
    [string]$Serial = "",
    [string]$Key = "",
    [string]$Python = "",
    [switch]$DryRun
)
$ErrorActionPreference = 'Continue'

# Show child-process output (python) as UTF-8 so nothing gets mangled in cmd.exe.
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
try { $OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

$Root   = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
$Pkg    = 'com.nexon.bluearchive'
$Base   = "/sdcard/Android/data/$Pkg/files/PUB/Resource"
$Work   = Join-Path $Root 'work'

function Step($m) { Write-Host ''; Write-Host "=== $m ===" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "  [ok] $m" -ForegroundColor Green }
function Bad($m)  { Write-Host "  [!!] $m" -ForegroundColor Red }

# ---------------------------------------------------------------- tools
# adb: env override -> PATH -> common bundled locations (emulators ship their own adb)
$Adb = $env:ADB
if (-not $Adb) {
    $cmd = Get-Command adb -ErrorAction SilentlyContinue
    if ($cmd) { $Adb = $cmd.Source }
}
if (-not $Adb) {
    $guesses = @(
        "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe",
        "C:\platform-tools\adb.exe",
        "C:\Android\platform-tools\adb.exe",
        "${env:ProgramFiles(x86)}\Netease\MuMu\nx_main\adb.exe",
        "$env:ProgramFiles\Netease\MuMu\nx_main\adb.exe",
        "$env:ProgramFiles\Netease\MuMuPlayer-12.0\shell\adb.exe",
        "C:\Program Files\Netease\MuMu\nx_main\adb.exe",
        "D:\Program Files\Netease\MuMu\nx_main\adb.exe",
        "E:\Program Files\Netease\MuMu\nx_main\adb.exe",
        "${env:ProgramFiles(x86)}\Nox\bin\adb.exe",
        "$env:ProgramFiles\BlueStacks_nxt\HD-Adb.exe",
        "$env:ProgramFiles\LDPlayer\LDPlayer9\adb.exe",
        "D:\LDPlayer\LDPlayer9\adb.exe"
    )
    foreach ($g in $guesses) { if (Test-Path $g) { $Adb = $g; break } }
}
if (-not $Adb) {
    Bad 'adb not found.'
    Write-Host '     Install Android platform-tools and add it to PATH,'
    Write-Host '     or set the path explicitly:   $env:ADB = "C:\path\to\adb.exe"'
    exit 1
}
Ok "adb = $Adb"

# python: pick the first interpreter that can actually USE sqlcipher3.
# A plain "does python exist" check is not enough: an alpha/beta build of a brand new
# Python can import the module and then crash inside the C extension (access violation),
# because prebuilt wheels target the FINAL ABI of that version. So we run a real probe.
# The probe lives in its own file on purpose: PowerShell strips embedded double quotes
# when passing arguments to a native command, which corrupts any inline `-c` version.
$Probe = Join-Path $Root 'tools\sqlcipher_probe.py'

function Test-PyCandidate($exe, $extra) {
    if (-not $exe) { return $false }
    if (-not (Test-Path $exe)) { return $false }
    if (-not (Test-Path $Probe)) { return $false }
    $out = & $exe @extra $Probe 2>&1
    return ($LASTEXITCODE -eq 0 -and (($out -join ' ') -match 'PROBE_OK'))
}

$cands = @()
if ($Python)     { $cands += ,@($Python, @()) }
if ($env:PYTHON) { $cands += ,@($env:PYTHON, @()) }
foreach ($c in @('python', 'python3')) {
    $s = (Get-Command $c -ErrorAction SilentlyContinue).Source
    if ($s) { $cands += ,@($s, @()) }
}
$pyLauncher = (Get-Command py -ErrorAction SilentlyContinue).Source
if ($pyLauncher) {
    # try pinned stable versions before whatever the launcher defaults to
    foreach ($v in @('3.13', '3.12', '3.11', '3.10', '3.9')) { $cands += ,@($pyLauncher, @("-$v")) }
    $cands += ,@($pyLauncher, @())
}
foreach ($r in @("$env:LOCALAPPDATA\Programs\Python", "$env:ProgramFiles", "C:\")) {
    if (-not (Test-Path $r)) { continue }
    Get-ChildItem $r -Directory -Filter 'Python3*' -ErrorAction SilentlyContinue |
        Sort-Object Name -Descending | ForEach-Object {
            $exe = Join-Path $_.FullName 'python.exe'
            if (Test-Path $exe) { $cands += ,@($exe, @()) }
        }
}

function Get-PyVersion($exe, $extra) {
    return (((& $exe @extra --version 2>&1) -join ' ').Trim())
}

$Py = $null; $PyArgs = @(); $rejected = @(); $stable = @()
foreach ($c in $cands) {
    $exe = $c[0]; $extra = @($c[1])
    if (-not $exe) { continue }
    if (-not (Test-Path $exe)) { continue }
    if (Test-PyCandidate $exe $extra) { $Py = $exe; $PyArgs = $extra; break }
    $ver = Get-PyVersion $exe $extra
    $rejected += ("{0} {1}  [{2}]" -f $exe, ($extra -join ' '), $ver)
    # only offer to install into real releases ("Python 3.12.10"), never alpha/beta builds
    if ($ver -match '^Python \d+\.\d+\.\d+$') { $stable += ,@($exe, $extra) }
}

# Nothing worked yet - install the (single) dependency ourselves, one time.
if (-not $Py -and $stable.Count -gt 0) {
    $req = Join-Path $Root 'requirements.txt'
    foreach ($c in $stable) {
        $exe = $c[0]; $extra = @($c[1])
        Step ("installing the sqlcipher3 dependency (one time) with " + (Get-PyVersion $exe $extra))
        & $exe @extra -m pip install --disable-pip-version-check -i https://pypi.tuna.tsinghua.edu.cn/simple -r $req
        if ($LASTEXITCODE -ne 0) {
            Write-Host '     mirror failed, retrying with the default index ...' -ForegroundColor Yellow
            & $exe @extra -m pip install --disable-pip-version-check -r $req
        }
        if (Test-PyCandidate $exe $extra) { $Py = $exe; $PyArgs = $extra; break }
    }
}
if (-not $Py) {
    Bad 'no usable Python + sqlcipher3 found.'
    $uniq = $rejected | Select-Object -Unique
    if ($uniq) { Write-Host '     tried:'; $uniq | ForEach-Object { Write-Host "       $_" } }
    Write-Host ''
    Write-Host '     How to fix (pick one):' -ForegroundColor Yellow
    Write-Host '       1) install a STABLE Python (3.10 - 3.13 recommended) from python.org'
    Write-Host '          then run:   py -3.12 -m pip install -r requirements.txt'
    Write-Host '          (avoid alpha/beta builds - the wheel may load but then crash)'
    Write-Host '       2) point at a working interpreter:'
    Write-Host '            $env:PYTHON = "C:\path\to\python.exe"'
    Write-Host '          or:'
    Write-Host '            .\localize_phone.ps1 -Python "C:\path\to\python.exe"'
    exit 1
}
Ok ("python = {0} {1}" -f $Py, ($PyArgs -join ' '))

$PackDb  = Join-Path $Root 'tools\patch_db.py'
$PackCat = Join-Path $Root 'tools\patch_catalog.py'
if (-not (Test-Path $PackDb)) { Bad "missing $PackDb"; exit 1 }

# ---------------------------------------------------------------- device
Step 'locating device'
& $Adb start-server 2>&1 | Out-Null
$cands = @()
foreach ($l in (& $Adb devices 2>&1)) {
    if ($l -match '^(\S+)\s+device') { $cands += $Matches[1] }
}
if ($Serial) {
    if ($cands -notcontains $Serial) { Bad "device '$Serial' not found. available: $($cands -join ', ')"; exit 1 }
    $Dev = $Serial
} else {
    $Dev = ($cands | Where-Object { $_ -notlike 'emulator-*' } | Select-Object -First 1)
    if (-not $Dev) { $Dev = $cands | Select-Object -First 1 }
}
if (-not $Dev) { Bad 'no device. Connect the phone over USB with USB debugging enabled.'; exit 1 }
Ok "device = $Dev"

New-Item -ItemType Directory -Force $Work | Out-Null
$OrigDb  = Join-Path $Work 'ExcelDB.orig.db'
$OrigCat = Join-Path $Work 'TableCatalog.orig.bytes'
$CnDb    = Join-Path $Work 'ExcelDB.cn.db'
$CnCat   = Join-Path $Work 'TableCatalog.cn.bytes'

# ---------------------------------------------------------------- pull
Step 'stopping the game and pulling the current database + catalog (kept as backup)'
& $Adb -s $Dev shell "am force-stop $Pkg" 2>&1 | Out-Null
& $Adb -s $Dev pull "$Base/Preload/TableBundles/ExcelDB.db" $OrigDb 2>&1 | Select-String 'pulled|error'
& $Adb -s $Dev pull "$Base/Catalog/TableBundles/TableCatalog.bytes" $OrigCat 2>&1 | Select-String 'pulled|error'
if (-not (Test-Path $OrigDb)) { Bad 'pull failed'; exit 1 }
Ok ('backup: {0:N1} MB' -f ((Get-Item $OrigDb).Length / 1MB))

# ---------------------------------------------------------------- convert
Step 'converting Traditional -> Simplified'
$argsDb = @($PackDb, '--in', $OrigDb, '--out', $CnDb)
if ($Key) { $argsDb += @('--key', $Key) }
& $Py @PyArgs -u @argsDb 2>&1 | Select-Object -Last 5
if (-not (Test-Path $CnDb)) { Bad 'conversion failed'; exit 1 }

Step 'patching the catalog CRC32'
$argsCat = @($PackCat, '--catalog', $OrigCat, '--db', $CnDb, '--out', $CnCat, '--expect-crc-db', $OrigDb)
& $Py @PyArgs -u @argsCat 2>&1 | Select-String 'crc|CRC|written'
if (-not (Test-Path $CnCat)) { Bad 'catalog patch failed'; exit 1 }

if ($DryRun) { Ok 'dry run: nothing was pushed'; exit 0 }

# ---------------------------------------------------------------- push
Step 'pushing the patched files back'
& $Adb -s $Dev push $CnDb "$Base/Preload/TableBundles/ExcelDB.db" 2>&1 | Select-String 'pushed|error'
& $Adb -s $Dev push $CnCat "$Base/Catalog/TableBundles/TableCatalog.bytes" 2>&1 | Select-String 'pushed|error'

Step 'done'

# ---------------------------------------------------------------- font fix
# The Android client bundles no Chinese font, so Chinese is rendered with a SYSTEM font
# chosen by the app's language.  With no per-app language the framework may pick a
# Traditional font, which lacks the Simplified glyphs we just wrote -> per-character font
# fallback -> mixed glyph sizes / weights.  Setting the app language to Simplified makes
# Android pick a full Simplified font, so everything renders uniformly.  No root needed.
Step 'fixing font fallback (app language -> Simplified Chinese)'
$sdkRaw = ((& $Adb -s $Dev shell "getprop ro.build.version.sdk" 2>&1) -join ' ').Trim()
$sdk = 0
if ($sdkRaw -match '(\d+)') { $sdk = [int]$Matches[1] }
if ($sdk -ge 33) {
    & $Adb -s $Dev shell "cmd locale set-app-locales $Pkg --locales zh-Hans-CN" 2>&1 | ForEach-Object { Write-Host "  $_" }
    $now = ((& $Adb -s $Dev shell "cmd locale get-app-locales $Pkg" 2>&1) -join ' ').Trim()
    Ok "app locale = $now"
    Write-Host '  (restart the game once so it re-loads the font)'
} else {
    Write-Host "  Android $sdk < 13 - per-app language is not supported."
    Write-Host '  If Chinese text has mixed glyph sizes, set the SYSTEM language to' -ForegroundColor Yellow
    Write-Host '  Simplified Chinese (Settings -> System -> Languages). Same fallback fix.' -ForegroundColor Yellow
}

Ok 'Launch the game - the UI and story text should be Simplified Chinese.'
Write-Host ''
Write-Host 'Notes:' -ForegroundColor Yellow
Write-Host '  * Re-run this script after every game update (the database changes).'
Write-Host '  * Do not use the in-game repair / redownload button; it restores the original files.'
Write-Host "  * Backups of the original files: $Work"
