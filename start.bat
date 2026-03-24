@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
cd /d "%~dp0"

set UV_DIR=%CD%\.runtime\uv
set UV_EXE=%UV_DIR%\uv.exe
set UV_VERSION=0.6.17
set UV_ZIP_URL=https://github.com/astral-sh/uv/releases/download/%UV_VERSION%/uv-x86_64-pc-windows-msvc.zip

if not exist "%UV_EXE%" (
  echo [INFO] Downloading uv runtime...
  if not exist "%UV_DIR%" mkdir "%UV_DIR%"
  powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%UV_ZIP_URL%', '.runtime\\uv\\uv.zip')"
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path '.runtime\\uv\\uv.zip' -DestinationPath '.runtime\\uv' -Force"
  if not exist "%UV_EXE%" (
    for /r "%UV_DIR%" %%F in (uv.exe) do (
      copy /Y "%%F" "%UV_EXE%" >nul
      goto :found_uv
    )
  )
)

:found_uv

set VENV_PY=%CD%\.runtime\venv\Scripts\python.exe
if not exist "%VENV_PY%" (
  echo [INFO] Creating Python 3.11 virtual environment...
  "%UV_EXE%" venv .runtime\venv --python 3.11
)

"%VENV_PY%" -m pip --version >nul 2>&1
if errorlevel 1 (
  echo [INFO] Restoring pip in virtual environment...
  "%VENV_PY%" -m ensurepip --upgrade
  "%VENV_PY%" -m pip install --upgrade pip
)

echo [INFO] Syncing dependencies...
"%UV_EXE%" pip install --python .runtime\venv\Scripts\python.exe -r requirements.txt

echo [INFO] Launching app...
"%VENV_PY%" converter.py --gui

endlocal
