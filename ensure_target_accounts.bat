@echo off
setlocal EnableExtensions
cd /d "%~dp0"
python main.py run %*
exit /b %ERRORLEVEL%
