@echo off
setlocal EnableExtensions

cd /d "%~dp0"

if not exist "app.py" (
    echo Error: app.py was not found in "%~dp0".
    pause
    exit /b 1
)

if not exist "models\plant_disease_model_1_latest.pt" (
    echo Error: models\plant_disease_model_1_latest.pt is missing.
    echo This START.bat now only starts the local app. It does not download files.
    pause
    exit /b 1
)

if not exist "uploadimages" mkdir "uploadimages" >nul 2>&1
if not exist "logs" mkdir "logs" >nul 2>&1

set "PYTHON_EXE="
set "PYTHON_ARGS="
set "APP_PORT=5000"
set "APP_URL="

if exist "venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"
) else if exist "python_local\python.exe" (
    set "PYTHON_EXE=%~dp0python_local\python.exe"
) else (
    where py >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_EXE=py"
        set "PYTHON_ARGS=-3"
    )
)

if not defined PYTHON_EXE (
    where python >nul 2>&1
    if not errorlevel 1 set "PYTHON_EXE=python"
)

if not defined PYTHON_EXE (
    echo Error: Python was not found.
    echo Expected one of:
    echo   - venv\Scripts\python.exe
    echo   - python_local\python.exe
    echo   - py -3
    echo   - python
    pause
    exit /b 1
)

call :choose_app_port
if errorlevel 1 (
    echo Error: no free port was found between 5000 and 5005.
    pause
    exit /b 1
)

set "PORT=%APP_PORT%"
set "APP_URL=http://127.0.0.1:%APP_PORT%"

echo Starting Agro Vision on %APP_URL%...
start "Agro Vision Server" /D "%~dp0" cmd /k ""%PYTHON_EXE%" %PYTHON_ARGS% app.py"
if errorlevel 1 (
    echo Error: failed to start the server.
    pause
    exit /b 1
)

timeout /t 4 /nobreak >nul
start "" "%APP_URL%"
exit /b 0

:choose_app_port
for %%P in (5000 5001 5002 5003 5004 5005) do (
    call :is_port_free %%P
    if not errorlevel 1 (
        set "APP_PORT=%%P"
        exit /b 0
    )
)
exit /b 1

:is_port_free
netstat -ano -p tcp | findstr "LISTENING" | findstr /c:":%~1 " >nul
if errorlevel 1 exit /b 0
exit /b 1
