@echo off
:: notify-sound.bat
:: Emite un sonido del sistema usando PowerShell
:: Uso: notify-sound.bat [tipo]
::   tipo: done     → sonido de tarea completada (asterisk)
::          confirm  → sonido de confirmacion requerida (exclamation)
::          (vacio)  → sonido generico (default beep)

set TYPE=%~1

if /I "%TYPE%"=="done" (
    powershell -Command "[System.Console]::Beep(880,200); Start-Sleep -Milliseconds 80; [System.Console]::Beep(1100,300)"
) else if /I "%TYPE%"=="confirm" (
    powershell -Command "[System.Console]::Beep(440,150); Start-Sleep -Milliseconds 60; [System.Console]::Beep(440,150); Start-Sleep -Milliseconds 60; [System.Console]::Beep(550,400)"
) else (
    powershell -Command "[System.Console]::Beep(660,200)"
)
