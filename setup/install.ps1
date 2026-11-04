# Installe l'environnement de montage vidéo piloté par Claude Code (Windows 10/11).
# Depuis la racine du dépôt :
#   powershell -ExecutionPolicy Bypass -File setup\install.ps1                   # skills + Remotion
#   powershell -ExecutionPolicy Bypass -File setup\install.ps1 -WithFilmCraft    # + FilmCraft et ses 2 MCP (~3 Go)
#   powershell -ExecutionPolicy Bypass -File setup\install.ps1 -WithHyperFrames  # + plugin HyperFrames
# Le kit TikTok a son propre installeur : tiktok\install.ps1
param(
    [switch]$WithFilmCraft,
    [switch]$WithHyperFrames,
    [switch]$SkipRemotionSkills,
    [string]$FilmCraftVersion = '0.13.0',  # version pour laquelle la skill filmcraft a été écrite
    [string]$SkillsDir = (Join-Path $env:USERPROFILE '.claude\skills')
)

$ErrorActionPreference = 'Stop'
$Repo = Split-Path -Parent $PSScriptRoot
$BackupDir = Join-Path (Split-Path -Parent $SkillsDir) 'skills-backup'
$FcDir = Join-Path $env:LOCALAPPDATA 'Programs\FilmCraft'
$Launcher = Join-Path $Repo 'filmcraft-mcp\launcher'
$AssistServer = Join-Path $Repo 'filmcraft-mcp\server'
. (Join-Path $PSScriptRoot 'lib.ps1')

Write-Step '1/4 Skills de montage (filmcraft, anakin-video-creator)'
Install-Skills

Write-Step '2/4 Skills Remotion officielles'
if ($SkipRemotionSkills) { Write-Warn 'ignorées (-SkipRemotionSkills)' } else { Install-RemotionSkills }

Write-Step "3/4 FilmCraft $FilmCraftVersion + MCP filmcraft / filmcraft-assist"
if ($WithFilmCraft) { Install-FilmCraft } else { Write-Warn 'ignoré (ajouter -WithFilmCraft pour l''installer, ~3 Go, GPU NVIDIA conseillé)' }

Write-Step '4/4 Plugin HyperFrames (HTML + GSAP)'
if ($WithHyperFrames) { Install-HyperFrames } else { Write-Warn 'ignoré (ajouter -WithHyperFrames)' }

Write-Host "`nTerminé. Redémarre Claude Code pour charger les nouvelles skills et MCP." -ForegroundColor Green
Write-Host 'Kit TikTok « Pourtant c''est vrai » : powershell -ExecutionPolicy Bypass -File tiktok\install.ps1'
