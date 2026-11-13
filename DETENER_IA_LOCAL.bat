@echo off
title VotoSeguro v2 - Detener Nodo Neuronal Local y Tunel Estatico
color 0E
echo ===============================================================================
echo   VOTOSEGURO v2.0 - DETENER IA LOCAL Y LIBERAR MEMORIA RAM
echo ===============================================================================
echo.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\stop_static_ai_tunnel.ps1"
pause
