# Compile le lanceur FilmCraftClaude.exe avec le compilateur C# fourni par Windows (.NET Framework 4).
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$csc = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not (Test-Path $csc)) { throw "Compilateur C# introuvable : $csc" }

$out = Join-Path $here 'FilmCraftClaude.exe'
$icon = Join-Path $here 'filmcraft.ico'
$cscArgs = @('/nologo', '/codepage:65001', '/target:winexe', '/optimize+', "/out:$out",
             '/r:System.Windows.Forms.dll', (Join-Path $here 'Launcher.cs'))
if (Test-Path $icon) { $cscArgs = @("/win32icon:$icon") + $cscArgs }

& $csc @cscArgs
if ($LASTEXITCODE -ne 0) { throw "Échec de la compilation (code $LASTEXITCODE)" }
Write-Output "OK : $out"
