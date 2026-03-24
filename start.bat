@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

set UV_DIR=%CD%\.runtime\uv
set UV_EXE=%UV_DIR%\uv.exe
set UV_VERSION=0.6.17
set UV_ZIP_URL=https://github.com/astral-sh/uv/releases/download/%UV_VERSION%/uv-x86_64-pc-windows-msvc.zip

if not exist "%UV_EXE%" (
  echo [INFO] uv をダウンロードしています...
  if not exist "%UV_DIR%" mkdir "%UV_DIR%"
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%UV_ZIP_URL%' -OutFile '.runtime\\uv\\uv.zip'"
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
  echo [INFO] Python 3.11 仮想環境を作成します...
  "%UV_EXE%" venv .runtime\venv --python 3.11
)

echo [INFO] 依存関係を同期します...
"%UV_EXE%" pip install --python .runtime\venv\Scripts\python.exe -r requirements.txt

echo [INFO] アプリを起動します...
"%VENV_PY%" converter.py --gui

endlocal
