@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "DRY_RUN=0"

if /I "%~1"=="--help" goto :usage
if /I "%~1"=="-h" goto :usage
if /I "%~1"=="--dry-run" set "DRY_RUN=1"
if /I "%~1"=="-n" set "DRY_RUN=1"

if not "%~1"=="" if "%DRY_RUN%"=="0" if /I not "%~1"=="--help" if /I not "%~1"=="-h" goto :usage

pushd "%~dp0" >nul
set "ROOT=%CD%"
popd >nul

set /a REMOVED_DIRS=0
set /a REMOVED_FILES=0
set /a SKIPPED=0
set /a FAILED=0

echo.
echo Limpiando artefactos del proyecto en:
echo   "%ROOT%"
echo Manteniendo intacto:
echo   "%ROOT%\.venv"
if "%DRY_RUN%"=="1" (
    echo.
    echo Modo simulacion activado. No se borrara nada.
)
echo.

for %%D in (
    ".pytest_cache"
    ".ruff_cache"
    ".mypy_cache"
    ".hypothesis"
    ".tox"
    ".nox"
    ".tmp"
    "build"
    "dist"
    "htmlcov"
    "pip-wheel-metadata"
    ".eggs"
) do (
    call :remove_dir "%ROOT%\%%~D"
)

for /d %%D in ("%ROOT%\*.egg-info") do (
    call :remove_dir "%%~fD"
)

for /d %%D in ("%ROOT%\pytest-cache-files-*") do (
    call :remove_dir "%%~fD"
)

pushd "%ROOT%" >nul

for /f "delims=" %%D in ('dir /s /b /ad __pycache__ 2^>nul ^| findstr /I /V /L /C:"\.venv\"') do (
    call :remove_dir "%%~fD"
)

for /f "delims=" %%D in ('dir /s /b /ad .ipynb_checkpoints 2^>nul ^| findstr /I /V /L /C:"\.venv\"') do (
    call :remove_dir "%%~fD"
)

for %%P in (
    "*.pyc"
    "*.pyo"
    "*$py.class"
    ".coverage"
    ".coverage.*"
    "coverage.xml"
    "*.cover"
    "*.log"
    "Thumbs.db"
    "Desktop.ini"
) do (
    for /f "delims=" %%F in ('dir /s /b /a-d %%~P 2^>nul ^| findstr /I /V /L /C:"\.venv\"') do (
        call :remove_file "%%~fF"
    )
)

popd >nul

echo.
echo Resumen:
echo   Carpetas eliminadas: !REMOVED_DIRS!
echo   Archivos eliminados: !REMOVED_FILES!
echo   Elementos omitidos:  !SKIPPED!
echo   Fallos:              !FAILED!
echo.

if "!FAILED!"=="0" (
    echo Limpieza terminada.
    exit /b 0
)

echo Limpieza terminada con avisos.
exit /b 1

:remove_dir
set "TARGET=%~1"
if not exist "!TARGET!" exit /b 0

call :is_inside_venv "!TARGET!"
if "!IN_VENV!"=="1" (
    exit /b 0
)

if "%DRY_RUN%"=="1" (
    set /a SKIPPED+=1
    echo [DRY ] "!TARGET!"
    exit /b 0
)

echo [DEL ] "!TARGET!"
rmdir /s /q "!TARGET!" 2>nul
if exist "!TARGET!" (
    set /a FAILED+=1
    echo [WARN] No se pudo borrar "!TARGET!"
    exit /b 0
)

set /a REMOVED_DIRS+=1
echo [ OK ] "!TARGET!"
exit /b 0

:remove_file
set "TARGET=%~1"
if not exist "!TARGET!" exit /b 0

call :is_inside_venv "!TARGET!"
if "!IN_VENV!"=="1" (
    exit /b 0
)

if "%DRY_RUN%"=="1" (
    set /a SKIPPED+=1
    echo [DRY ] "!TARGET!"
    exit /b 0
)

echo [DEL ] "!TARGET!"
del /f /q "!TARGET!" 2>nul
if exist "!TARGET!" (
    set /a FAILED+=1
    echo [WARN] No se pudo borrar "!TARGET!"
    exit /b 0
)

set /a REMOVED_FILES+=1
echo [ OK ] "!TARGET!"
exit /b 0

:is_inside_venv
set "IN_VENV=0"
set "CHECK=%~1"

if /I "!CHECK!"=="%ROOT%\.venv" set "IN_VENV=1"
if /I not "!CHECK:%ROOT%\.venv\=!"=="!CHECK!" set "IN_VENV=1"
exit /b 0

:usage
echo Uso:
echo   clean.bat
echo   clean.bat --dry-run
echo.
echo Borra caches, artefactos de build y temporales comunes del proyecto,
echo sin tocar nada dentro de ".venv".
exit /b 0
