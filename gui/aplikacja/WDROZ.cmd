@echo off
title Punkt Zycia - wdrozenie na Azure
set IP=20.215.200.98
set U=azureuser
cd /d "%~dp0"
set MODEL=
if exist model.env set MODEL=model.env
echo [1/2] Wysylam pliki na %U%@%IP% (wpisz haslo do VM)
scp -o StrictHostKeyChecking=accept-new -r index.html sw.js manifest.webmanifest icon-192.png icon-512.png deploy.sh %MODEL% ..\zrodla\aedverify %U%@%IP%:PunktZycia/
if errorlevel 1 goto blad
echo.
echo [2/2] Instaluje serwer i HTTPS (wpisz haslo jeszcze raz)
ssh -t %U%@%IP% "bash ~/PunktZycia/deploy.sh %IP%"
if errorlevel 1 goto blad
echo.
echo GOTOWE: https://20-215-200-98.sslip.io/start
echo Weryfikacja: https://20-215-200-98.sslip.io/weryfikuj.html
pause
exit /b 0
:blad
echo.
echo BLAD - zrob zrzut tego okna.
pause
