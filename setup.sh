#!/usr/bin/env bash
# One-time setup for macOS/Linux. Windows: use setup.ps1 instead.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

echo "==> Starting Postgres (docker compose)"
if docker compose version > /dev/null 2>&1; then
  docker compose up -d
else
  docker-compose up -d
fi

echo "==> Backend: venv + dependencies"
cd backend
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install --upgrade pip > /dev/null
.venv/bin/pip install -r requirements.txt

if [ ! -f .env ]; then
  cp ../.env.example .env
  echo "    Created backend/.env — edit it to add ANTHROPIC_API_KEY, UNPAYWALL_EMAIL, OPENALEX_MAILTO"
  echo "    (or skip that and set them later from the app's Settings page instead)."
fi

echo "==> Running database migrations"
.venv/bin/alembic upgrade head

echo "==> Frontend: npm install"
cd ../frontend
npm install
if [ ! -f .env ]; then
  cp .env.example .env
fi

cd ..
cat <<'EOF'

Setup complete. To run the app (two terminals):

  cd backend && .venv/bin/uvicorn app.main:app --reload --port 8420
  cd frontend && npm run dev

Then open http://localhost:5173
EOF
