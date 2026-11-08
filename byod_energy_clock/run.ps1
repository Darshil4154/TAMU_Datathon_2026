param(
    [ValidateSet('data', 'fake', 'test', 'check', 'app', 'demo')]
    [string]$Task = 'app'
)

$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    $energyPython = Join-Path $PSScriptRoot '.python/venv/Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $energyPython)) {
        $energyPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
    }
    if (-not (Test-Path -LiteralPath $energyPython)) {
        throw 'Create a Python 3.11 virtual environment and install requirements.txt first.'
    }
    switch ($Task) {
        'data' { & $energyPython -m src.pipeline }
        'fake' { & $energyPython -m src.pipeline --fake }
        'test' { & $energyPython -m pytest -q }
        'check' {
            & $energyPython -m pytest -q
            if ($LASTEXITCODE -eq 0) { & $energyPython -m src.check }
        }
        'app' {
            $priorMode = $env:ENERGY_CLOCK_TEST_MODE
            try {
                Remove-Item Env:ENERGY_CLOCK_TEST_MODE -ErrorAction SilentlyContinue
                & $energyPython -m streamlit run app.py
            } finally { $env:ENERGY_CLOCK_TEST_MODE = $priorMode }
        }
        'demo' {
            $priorMode = $env:ENERGY_CLOCK_TEST_MODE
            try {
                $env:ENERGY_CLOCK_TEST_MODE = '1'
                & $energyPython -m streamlit run app.py
            } finally { $env:ENERGY_CLOCK_TEST_MODE = $priorMode }
        }
    }
    if ($LASTEXITCODE -ne 0) { throw "Energy Clock command failed (exit $LASTEXITCODE)." }
} finally {
    Pop-Location
}
