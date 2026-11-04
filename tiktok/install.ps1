# Installe tout l'environnement du kit « Pourtant c'est vrai » (Windows 10/11).
# Lancer depuis ce dossier :  powershell -ExecutionPolicy Bypass -File install.ps1
# Options : -SkipRemotionSkills (ne pas installer les skills Remotion officielles pour Claude Code)
param([switch]$SkipRemotionSkills)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$MinPython = '3.10'
$MinNode = 18

function Write-Step([string]$msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok([string]$msg) { Write-Host "    OK  $msg" -ForegroundColor Green }
function Write-Warn([string]$msg) { Write-Host "    !!  $msg" -ForegroundColor Yellow }

function Update-SessionPath {
    $machine = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $user = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = "$machine;$user"
}

function Test-Command([string]$name) { return [bool](Get-Command $name -ErrorAction SilentlyContinue) }

function Test-Python {
    if (-not (Test-Command 'python')) { return $false }
    try {
        $ok = & python -c "import sys; print(sys.version_info >= ($($MinPython.Replace('.', ', '))))" 2>$null
        return ($LASTEXITCODE -eq 0 -and "$ok".Trim() -eq 'True')
    } catch { return $false }
}

function Test-Node {
    if (-not (Test-Command 'node')) { return $false }
    try {
        $major = [int]((& node -v).TrimStart('v').Split('.')[0])
        return ($major -ge $MinNode)
    } catch { return $false }
}

function Test-Ffmpeg {
    $winget = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Links\ffmpeg.exe'
    return ((Test-Path $winget) -or (Test-Command 'ffmpeg'))
}

function Install-WithWinget([string]$id, [string]$label, [string]$override) {
    if (-not (Test-Command 'winget')) {
        throw "winget introuvable : installe « App Installer » depuis le Microsoft Store, puis relance ce script."
    }
    Write-Host "    installation de $label via winget (1 à 3 min)..."
    $wingetArgs = @('install', '--id', $id, '-e', '--accept-package-agreements', '--accept-source-agreements')
    if ($override) { $wingetArgs += @('--override', $override) } else { $wingetArgs += '--silent' }
    & winget @wingetArgs
    if ($LASTEXITCODE -ne 0) { Write-Warn "winget a renvoyé le code $LASTEXITCODE pour $label" }
    Update-SessionPath
}

function Confirm-Tool([string]$label, [scriptblock]$test, [string]$wingetId, [string]$override = '') {
    if (& $test) { Write-Ok "$label déjà présent"; return }
    Install-WithWinget $wingetId $label $override
    if (-not (& $test)) {
        throw "$label toujours introuvable après installation : ferme ce terminal, rouvre-le et relance install.ps1."
    }
    Write-Ok "$label installé"
}

function Invoke-Checked([string]$label, [scriptblock]$command) {
    & $command
    if ($LASTEXITCODE -ne 0) { throw "échec : $label (code $LASTEXITCODE)" }
    Write-Ok $label
}

Write-Step "1/6 Outils système (Python >= $MinPython, Node >= $MinNode, ffmpeg)"
# Sans PrependPath=1, l'installeur Python silencieux n'ajoute pas python au PATH.
Confirm-Tool 'Python' { Test-Python } 'Python.Python.3.12' '/quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1'
Confirm-Tool 'Node.js' { Test-Node } 'OpenJS.NodeJS.LTS'
Confirm-Tool 'ffmpeg' { Test-Ffmpeg } 'Gyan.FFmpeg'

Write-Step '2/6 Paquets Python (edge-tts, pillow, requests)'
& python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Warn 'installation globale refusée, nouvel essai avec --user'
    Invoke-Checked 'paquets Python (--user)' { & python -m pip install --user -r requirements.txt }
} else { Write-Ok 'paquets Python' }

Write-Step '3/6 Dépendances du studio Remotion (npm ci, ~700 Mo, 1 à 3 min)'
Push-Location (Join-Path $Root 'studio')
try { Invoke-Checked 'node_modules' { & npm.cmd ci --no-audit --no-fund } } finally { Pop-Location }

Write-Step '4/6 Assets partagés (polices, sons, musiques, grain)'
Invoke-Checked 'assets' { & python -I pipeline/setup_assets.py }

Write-Step '5/6 Navigateur de rendu Remotion (Chrome Headless Shell, ~100 Mo)'
Push-Location (Join-Path $Root 'studio')
try { Invoke-Checked 'navigateur de rendu' { & npx.cmd remotion browser ensure } } finally { Pop-Location }

Write-Step '6/6 Claude Code et skills'
if (Test-Command 'claude') { Write-Ok 'Claude Code présent' }
else { Write-Warn "Claude Code absent. Pour l'installer :  irm https://claude.ai/install.ps1 | iex" }
Write-Ok 'skill du projet « pourtant-cest-vrai » : déjà dans .claude/skills (rien à faire)'
if ($SkipRemotionSkills) { Write-Warn 'skills Remotion officielles ignorées (-SkipRemotionSkills)' }
else {
    Write-Host '    skills Remotion officielles (optionnel, réponds aux questions si besoin)...'
    & npx.cmd -y skills add remotion-dev/skills
    if ($LASTEXITCODE -ne 0) { Write-Warn 'skills Remotion non installées (facultatif) : npx skills add remotion-dev/skills' }
    else { Write-Ok 'skills Remotion' }
}

Write-Host "`nTout est prêt." -ForegroundColor Green
Write-Host 'Test rapide (~5 min) : python -I pipeline/build_story.py lustig ; python -I pipeline/render.py lustig ; python -I pipeline/qc.py lustig'
Write-Host 'Avec Claude : lance « claude » dans ce dossier, puis demande « Fais la vidéo de la prochaine histoire du backlog ».'
