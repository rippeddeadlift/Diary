# Diary (local)

Folder layout (Windows path):
- `C:\Users\ivank\Documents\Diary\diary-app` — React app source
- `C:\Users\ivank\Documents\Diary\data` — app data: sidecars, indexes, thumbnails, trip metadata, fitness logs
- `E:\Diary\data` — media archive: photos, videos, and GPX files

The backend uses `E:\Diary\data` for media by default on Windows. Set
`DIARY_MEDIA_DIR` before starting the backend to use another media root. The
backend writes media-relative `.json` sidecars and indexes under the C: `data`
folder; it does not use duplicate JSON files copied to the media archive.
Existing media on C: is left untouched and is not removed automatically.

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


