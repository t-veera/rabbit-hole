# One-time setup for Windows (PowerShell). macOS/Linux: use setup.sh instead.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "==> Starting Postgres (docker compose)"
docker compose up -d

Write-Host "==> Backend: venv + dependencies"
Set-Location backend
if (-not (Test-Path .venv)) {
    python -m venv .venv
}
& .\.venv\Scripts\pip.exe install --upgrade pip | Out-Null
& .\.venv\Scripts\pip.exe install -r requirements.txt

if (-not (Test-Path .env)) {
    Copy-Item ..\.env.example .env
    Write-Host "    Created backend\.env -- edit it to add ANTHROPIC_API_KEY, UNPAYWALL_EMAIL, OPENALEX_MAILTO"
    Write-Host "    (or skip that and set them later from the app's Settings page instead)."
}

Write-Host "==> Running database migrations"
& .\.venv\Scripts\alembic.exe upgrade head

Write-Host "==> Frontend: npm install"
Set-Location ..\frontend
npm install
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
}

Set-Location ..
Write-Host ""
Write-Host "Setup complete. To run the app (two terminals):"
Write-Host ""
Write-Host "  cd backend; .\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8420"
Write-Host "  cd frontend; npm run dev"
Write-Host ""
Write-Host "Then open http://localhost:5173"
