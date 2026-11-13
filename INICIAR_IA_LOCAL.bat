@echo off
title VotoSeguro v2 - Iniciar Nodo Neuronal Local y Tunel Estatico
color 0B
echo ===============================================================================
echo   VOTOSEGURO v2.0 - INICIADOR DE 1-CLIC DE IA LOCAL Y TUNEL ESTATICO NGROK
echo ===============================================================================
echo.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\start_static_ai_tunnel.ps1"
pause
