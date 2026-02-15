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

## Add a new trip
Create folder: `trips/YYYY-MM-DD-something/`

Required files:
- `meta.json` (see example)
- `route.gpx`
- `notes.md` (optional)
- `photos/` (optional)

Then add it to `trips/index.json`.

(We can later automate index generation.)
