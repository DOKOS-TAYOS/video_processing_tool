$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
$entryPoint = Join-Path $repoRoot "src\video_processing\__main__.py"
$configPath = Join-Path $repoRoot "config"
$distPath = Join-Path $repoRoot "dist"
$workPath = Join-Path $repoRoot "build\pyinstaller"

if (-not (Test-Path $pythonExe)) {
    throw "No se encontro .venv. Crea o actualiza el entorno virtual antes de generar el .exe."
}

Push-Location $repoRoot
try {
    & $pythonExe -m pip install -e ".[build-win]"
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudieron instalar las dependencias de build para Windows."
    }

    & $pythonExe -m PyInstaller `
        --noconfirm `
        --clean `
        --onefile `
        --name "video-processing" `
        --paths (Join-Path $repoRoot "src") `
        --distpath $distPath `
        --workpath $workPath `
        --specpath $workPath `
        --add-data "${configPath};config" `
        $entryPoint
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller no pudo generar el ejecutable."
    }
}
finally {
    Pop-Location
}
