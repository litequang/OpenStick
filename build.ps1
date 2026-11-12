$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
& .\.venv\Scripts\python.exe -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --name UZ801-OpenStick-Manager --collect-data uz801_manager launcher.py
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
& .\dist\UZ801-OpenStick-Manager.exe --self-test
if ($LASTEXITCODE -ne 0) { throw 'Packaged self-test failed' }
Get-FileHash -LiteralPath .\dist\UZ801-OpenStick-Manager.exe -Algorithm SHA256
