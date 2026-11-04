@echo off
rem Serveur MCP « filmcraft » (pont vers l'appli lancée par FilmCraftClaude.exe).
rem Lit le jeton partagé puis lance le serveur MCP officiel de FilmCraft sur stdio.
rem Port fixe 9876 : le même que dans Launcher.cs et filmcraft_assist/config.py.
setlocal
set "FC_DIR=%LOCALAPPDATA%\Programs\FilmCraft"
set "TOKEN_FILE=%LOCALAPPDATA%\FilmCraft-Claude\control.token"
if exist "%TOKEN_FILE%" (
  set /p FILMCRAFT_CONTROL_TOKEN=<"%TOKEN_FILE%"
) else (
  echo filmcraft-bridge: jeton absent ^(%TOKEN_FILE%^). Lancer FilmCraft une fois par le raccourci du bureau, puis reconnecter ce MCP. 1>&2
)
"%FC_DIR%\filmcraft-cli.exe" mcp --bridge 127.0.0.1:9876
