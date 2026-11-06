$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
$env:DEMO_MODE = "true"
$workspaceDb = Join-Path $PSScriptRoot "backend/data/paybridge.db"
$submissionDb = Join-Path $PSScriptRoot "backend/data/payment_data.db"
$selectedDb = if (Test-Path -LiteralPath $workspaceDb) { $workspaceDb } else { $submissionDb }
$env:DATABASE_URL = "sqlite:///" + $selectedDb.Replace("\", "/")
python -c "import streamlit, sqlalchemy, langgraph, razorpay, sklearn, fastapi, jwt, httpx"
if ($LASTEXITCODE -ne 0) {
    python -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }
}
python backend/scripts/setup_demo.py
if ($LASTEXITCODE -ne 0) { throw "Demo setup failed." }
if (-not (Test-NetConnection 127.0.0.1 -Port 8000 -InformationLevel Quiet)) {
    Start-Process -FilePath "python" -ArgumentList @("-m", "uvicorn", "backend:app", "--host", "127.0.0.1", "--port", "8000") -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
}
$apiReady = $false
for ($attempt = 0; $attempt -lt 20; $attempt++) {
    try {
        Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 2 | Out-Null
        $apiReady = $true
        break
    } catch {
        Start-Sleep -Milliseconds 500
    }
}
if (-not $apiReady) { throw "FastAPI did not become ready on port 8000." }
python -m streamlit run frontend/app.py --server.address 127.0.0.1
