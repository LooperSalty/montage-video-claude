# Fonctions de l'installeur (chargées par install.ps1). Variables attendues dans la portée appelante :
# $Repo, $SkillsDir, $BackupDir, $FcDir, $FilmCraftVersion, $Launcher, $AssistServer.

$Placeholder = '{{DEPOT}}'
$Utf8NoBom = New-Object Text.UTF8Encoding($false)

function Write-Step([string]$msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok([string]$msg) { Write-Host "    OK  $msg" -ForegroundColor Green }
function Write-Warn([string]$msg) { Write-Host "    !!  $msg" -ForegroundColor Yellow }
function Test-Command([string]$name) { return [bool](Get-Command $name -ErrorAction SilentlyContinue) }

function Update-SessionPath {
    $machine = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $user = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = "$machine;$user"
}

function Install-WingetPackage([string]$id, [string]$command) {
    if (Test-Command $command) { return }
    if (-not (Test-Command 'winget')) { throw "$command introuvable et winget absent : installer « App Installer » (Microsoft Store)." }
    & winget install --id $id -e --silent --accept-package-agreements --accept-source-agreements
    Update-SessionPath
    if (-not (Test-Command $command)) { throw "$command introuvable après installation : rouvrir le terminal et relancer." }
}

# --- Skills -----------------------------------------------------------------------------------

function Set-RepoPath([string]$dir) {
    foreach ($file in Get-ChildItem $dir -Recurse -File -Filter *.md) {
        $text = [IO.File]::ReadAllText($file.FullName, $Utf8NoBom)
        if ($text.Contains($Placeholder)) {
            [IO.File]::WriteAllText($file.FullName, $text.Replace($Placeholder, $Repo), $Utf8NoBom)
        }
    }
}

function Install-Skills {
    New-Item -ItemType Directory -Force $SkillsDir | Out-Null
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    foreach ($skill in Get-ChildItem (Join-Path $Repo 'skills') -Directory) {
        $dest = Join-Path $SkillsDir $skill.Name
        if (Test-Path $dest) {
            # Sauvegarde hors de skills\ : sinon Claude Code chargerait deux skills du même nom.
            New-Item -ItemType Directory -Force $BackupDir | Out-Null
            Move-Item $dest (Join-Path $BackupDir "$($skill.Name)-$stamp")
            Write-Warn "ancienne version de $($skill.Name) déplacée dans $BackupDir"
        }
        Copy-Item $skill.FullName $dest -Recurse
        Set-RepoPath $dest
        Write-Ok "skill $($skill.Name) → $dest"
    }
}

function Install-RemotionSkills {
    if (-not (Test-Command 'npx.cmd')) { Write-Warn 'Node.js absent : skills Remotion ignorées (installer Node LTS, puis relancer)'; return }
    & npx.cmd -y skills add remotion-dev/skills
    if ($LASTEXITCODE -ne 0) { Write-Warn 'skills Remotion non installées : npx skills add remotion-dev/skills' }
    else { Write-Ok 'skills Remotion officielles' }
}

function Install-HyperFrames {
    if (-not (Test-Command 'claude')) { Write-Warn 'Claude Code absent : plugin HyperFrames ignoré'; return }
    & claude plugin marketplace add heygen-com/hyperframes
    & claude plugin install hyperframes@hyperframes
    if ($LASTEXITCODE -ne 0) {
        Write-Warn 'dans Claude Code : /plugin marketplace add heygen-com/hyperframes puis /plugin install hyperframes@hyperframes'
    } else { Write-Ok 'plugin HyperFrames' }
}

# --- FilmCraft --------------------------------------------------------------------------------

function Get-VerifiedDownload([string]$baseUrl, [string]$name, [string]$tmp) {
    $ProgressPreference = 'SilentlyContinue'  # la barre de progression rend Invoke-WebRequest 10x plus lent
    $file = Join-Path $tmp $name
    $sums = Join-Path $tmp 'SHA256SUMS.txt'
    Invoke-WebRequest "$baseUrl/$name" -OutFile $file -UseBasicParsing
    Invoke-WebRequest "$baseUrl/SHA256SUMS.txt" -OutFile $sums -UseBasicParsing
    $pattern = '^([0-9a-fA-F]{64})\s+\*?' + [regex]::Escape($name) + '$'
    $line = Get-Content $sums | Where-Object { $_ -match $pattern } | Select-Object -First 1
    if (-not $line) { throw "$name absent de SHA256SUMS.txt" }
    $expected = ($line -split '\s+')[0].ToUpperInvariant()
    if ((Get-FileHash $file -Algorithm SHA256).Hash -ne $expected) {
        throw "SHA256 invalide pour $name : téléchargement corrompu, relancer."
    }
    return $file
}

function Install-FilmCraftApp {
    if (Test-Path (Join-Path $FcDir 'filmcraft.exe')) { Write-Ok "FilmCraft déjà installé ($FcDir)"; return }
    $name = "filmcraft-$FilmCraftVersion-windows-x64-portable.zip"
    $tmp = Join-Path $env:TEMP "filmcraft-setup-$FilmCraftVersion"
    New-Item -ItemType Directory -Force $tmp | Out-Null
    Write-Host "    téléchargement de $name (~100 Mo)..."
    $zip = Get-VerifiedDownload "https://github.com/storytold/filmcraft/releases/download/v$FilmCraftVersion" $name $tmp
    $unzipped = Join-Path $tmp 'unzipped'
    Expand-Archive $zip -DestinationPath $unzipped -Force
    $exe = Get-ChildItem $unzipped -Recurse -Filter 'filmcraft.exe' | Select-Object -First 1
    if (-not $exe) { throw "filmcraft.exe introuvable dans $name" }
    New-Item -ItemType Directory -Force $FcDir | Out-Null
    Copy-Item (Join-Path $exe.DirectoryName '*') $FcDir -Recurse -Force
    Remove-Item $tmp -Recurse -Force
    Write-Ok "FilmCraft $FilmCraftVersion installé dans $FcDir"
}

function Install-Launcher {
    & (Join-Path $Launcher 'build.ps1')
    $shortcut = Join-Path ([Environment]::GetFolderPath('Desktop')) 'FilmCraft.lnk'
    $lnk = (New-Object -ComObject WScript.Shell).CreateShortcut($shortcut)
    $lnk.TargetPath = Join-Path $Launcher 'FilmCraftClaude.exe'
    $lnk.WorkingDirectory = $Launcher
    $lnk.IconLocation = Join-Path $Launcher 'filmcraft.ico'
    $lnk.Save()
    Write-Ok 'lanceur FilmCraftClaude.exe compilé + raccourci bureau « FilmCraft »'
}

function Install-AssistServer {
    Install-WingetPackage 'astral-sh.uv' 'uv'
    Install-WingetPackage 'Gyan.FFmpeg' 'ffmpeg'
    Write-Host '    dépendances de filmcraft-assist (faster-whisper + CUDA, ~2,5 Go)...'
    & uv sync --directory $AssistServer
    if ($LASTEXITCODE -ne 0) { throw "uv sync a échoué (code $LASTEXITCODE)" }
    Write-Ok 'filmcraft-assist prêt'
}

function Get-FilmCraftDocs {
    $dest = Join-Path $Repo 'filmcraft'
    if (Test-Path (Join-Path $dest 'docs')) { Write-Ok 'docs FilmCraft déjà présentes'; return }
    if (-not (Test-Command 'git')) { Write-Warn 'git absent : docs FilmCraft non clonées (facultatif)'; return }
    & git clone --quiet --depth 1 --branch "v$FilmCraftVersion" --filter=blob:none --sparse https://github.com/storytold/filmcraft $dest
    if ($LASTEXITCODE -eq 0) { & git -C $dest sparse-checkout set docs }
    if ($LASTEXITCODE -ne 0) { Write-Warn 'docs FilmCraft non clonées (facultatif)' }
    else { Write-Ok "docs FilmCraft → $dest\docs" }
}

function Register-Mcp([string]$name, [string[]]$command) {
    if (-not (Test-Command 'claude')) { Write-Warn "Claude Code absent : MCP $name non déclaré"; return }
    $exists = $false
    try { & claude mcp get $name *> $null; $exists = ($LASTEXITCODE -eq 0) } catch { $exists = $false }
    if ($exists) { Write-Ok "MCP $name déjà déclaré"; return }
    & claude mcp add -s user $name -- @command
    if ($LASTEXITCODE -ne 0) { throw "échec : claude mcp add $name" }
    Write-Ok "MCP $name déclaré (tous les projets)"
}

function Install-FilmCraft {
    Install-FilmCraftApp
    Install-Launcher
    Install-AssistServer
    Get-FilmCraftDocs
    Register-Mcp 'filmcraft' @('cmd', '/c', (Join-Path $Launcher 'filmcraft-bridge.cmd'))
    Register-Mcp 'filmcraft-assist' @('uv', 'run', '--directory', $AssistServer, 'filmcraft-assist')
}
