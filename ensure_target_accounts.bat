@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "TARGET_COUNT=%~1"
if "%TARGET_COUNT%"=="" (
  set /p TARGET_COUNT=Please enter target valid account count: 
)

if "%TARGET_COUNT%"=="" (
  echo [error] target count is required.
  exit /b 1
)

shift
set "EXTRA_ARGS="
:collect_args
if "%~1"=="" goto run
set "EXTRA_ARGS=!EXTRA_ARGS! %~1"
shift
goto collect_args

:run
python main.py accounts ensure-target --target-count %TARGET_COUNT% --refresh-before-validate --output json !EXTRA_ARGS!
exit /b %ERRORLEVEL%
