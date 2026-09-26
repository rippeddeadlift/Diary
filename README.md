# Diary (local)

Folder layout (Windows path):
- `C:\Users\ivank\Documents\Diary\diary-app` — React app source
- `C:\Users\ivank\Documents\Diary\trips` — your data (GPX, photos, notes)

## Run (dev)

From WSL/Ubuntu:

```bash
cd /mnt/c/Users/ivank/Documents/Diary/diary-app
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

Open in Windows browser:
- http://localhost:5173/

## Server tests (Windows / PowerShell)

```powershell
# Create venv (once)
python -m venv server\.venv

# Activate venv
.\server\.venv\Scripts\Activate.ps1

# Install deps (includes pytest)
pip install -r server\requirements.txt

# Run tests
python -m pytest -v
```

## Frontend tests (Vitest)

```powershell
cd diary-app
npm install
npm test -- --run
```

## Add a new trip

Create folder: `trips/YYYY-MM-DD-something/`

Required files:
- `route.gpx`


