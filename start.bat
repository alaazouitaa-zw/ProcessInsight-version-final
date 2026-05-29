@echo off
cd /d "%~dp0"
title ProcessInsight - serveur local
echo.
echo  ProcessInsight - demarrage sur http://127.0.0.1:5000
echo  Gardez cette fenetre ouverte. Arret : Ctrl+C
echo.

where python >nul 2>&1
if %errorlevel%==0 (
    set PY=python
    goto :deps
)

where py >nul 2>&1
if %errorlevel%==0 (
    set PY=py -3
    goto :deps
)

echo [ERREUR] Python introuvable.
echo Installez Python depuis https://www.python.org/downloads/
echo Cochez "Add python.exe to PATH" pendant l'installation.
pause
exit /b 1

:deps
echo Installation des dependances...
%PY% -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERREUR] pip a echoue.
    pause
    exit /b 1
)

echo.
echo Ouverture du navigateur...
start "" http://127.0.0.1:5000

%PY% app.py
pause
