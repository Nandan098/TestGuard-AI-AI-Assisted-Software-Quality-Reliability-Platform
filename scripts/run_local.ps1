$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

python -m venv "$Root\.venv"
& "$Root\.venv\Scripts\Activate.ps1"
pip install -r "$Root\target_app\requirements.txt" -r "$Root\backend\requirements.txt"

Write-Host "Starting demo target API, backend and frontend in separate terminal windows..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$Root\target_app'; ..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8001"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$Root\backend'; `$env:TARGET_BASE_URL='http://127.0.0.1:8001'; ..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$Root\frontend'; npm install; npm run dev -- --host 0.0.0.0"
Write-Host "Open http://localhost:5173 after startup completes."
