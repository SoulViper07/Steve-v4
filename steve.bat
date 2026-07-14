@echo off
setlocal

set "PYTHONUTF8=1"
chcp 65001 >nul

set "STEVE_LAUNCH_DIR=%CD%"
set "STEVE_AGENT=%~dp0agent.py"

if not exist "%STEVE_AGENT%" (
    echo Steve agent entry point not found: "%STEVE_AGENT%" 1>&2
    exit /b 1
)

if defined STEVE_PYTHON (
    "%STEVE_PYTHON%" "%STEVE_AGENT%" --workdir "%STEVE_LAUNCH_DIR%" %*
) else (
    python "%STEVE_AGENT%" --workdir "%STEVE_LAUNCH_DIR%" %*
)
set "STEVE_EXIT=%ERRORLEVEL%"

exit /b %STEVE_EXIT%
