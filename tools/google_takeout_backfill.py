#!/usr/bin/env python3
# Google Photos Takeout Backfill: fill createdAt from Takeout JSON timestamps
# Usage: cd Diary; python tools/google_takeout_backfill.py /path/to/Takeout/Google\\ Photos/JSON/
# Matches JSON 'title' (IMG_7316.JPG) to data/photos/inbox/*/*.JPG sidecar
# Sets createdAt from 'photoTakenTime.timestamp' (unix sec → ISO UTC)

import glob
import json
import re
import sys
from pathlib import Path
from datetime import datetime

DATA_INBOX = Path('data/photos/inbox').resolve()

def unix_sec_to_iso(ts_sec: str) -> str:
    dt = datetime.utcfromtimestamp(int(ts_sec))
    return dt.isoformat(timespec='seconds') + 'Z'

if len(sys.argv) != 2:
    print('Usage: python tools/google_takeout_backfill.py \"C:\\Users\\ivank\\Downloads\\test\"')
    sys.exit(1)

takeout_root = Path(sys.argv[1]).resolve()
if not takeout_root.exists():
    print(f'Error: {takeout_root} not found')
    sys.exit(1)

fixed = skipped_has_date = skipped_no_title = skipped_no_ts = no_match = errors = 0

for json_path in takeout_root.rglob('*.json'):
    try:
        data = json.loads(json_path.read_text(encoding='utf-8'))
        title = data.get('title', '')
        if not title:
            skipped_no_title += 1
            print(f'Skipped no title: {json_path.name}')
            continue

        # Extract ID: IMG_7994.JPG → '7994'
        match = re.search(r'IMG_(\d+)\.', title)
        if not match:
            skipped_no_title += 1
            print(f'Skipped no IMG_ID in title \'{title}\': {json_path.name}')
            continue
        photo_id = match.group(1)
        print(f'Processing {json_path.name} → ID \'{photo_id}\' (title \'{title}\')')

        candidates = glob.glob(str(DATA_INBOX / '**' / f'*IMG_{photo_id}*.jp*g'), recursive=True)
        if not candidates:
            no_match += 1
            continue

        # 1. Erst prüfen, ob das Takeout-JSON überhaupt ein Datum liefert
        photo_time = data.get('photoTakenTime', {}) or data.get('creationTime', {})
        ts_sec = photo_time.get('timestamp')
        if not ts_sec:
            skipped_no_ts += 1
            continue # Kein Timestamp, wir können dieses JSON komplett ignorieren

        # 2. Jetzt alle gefundenen Duplikate durchgehen und Datum eintragen
        applied = False
        for cand in candidates:
            photo_path = Path(cand)
            sidecar_path = photo_path.with_name(photo_path.name + '.json')

            if not sidecar_path.exists():
                continue

            sidecar_data = json.loads(sidecar_path.read_text(encoding='utf-8'))
            
            # Wenn dieses Bild schon ein Datum hat, prüfen wir das nächste Duplikat
            if sidecar_data.get('createdAt'):
                continue

            # Wir haben ein Bild ohne Datum gefunden!
            sidecar_data['createdAt'] = unix_sec_to_iso(ts_sec)
            sidecar_data['createdAtSource'] = 'google_takeout'
            sidecar_path.write_text(json.dumps(sidecar_data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            print(f'✓ Fixed {photo_path.name}: {ts_sec} -> {sidecar_data["createdAt"]}')
            fixed += 1
            applied = True
            break # Erfolgreich eingetragen, wir können mit dem nächsten JSON weitermachen

        if not applied:
            # Kein passendes Bild ohne Datum gefunden
            skipped_has_date += 1
            print(f'  Skipped: Alle {len(candidates)} Bilder mit ID {photo_id} haben bereits ein Datum oder keinen Sidecar')
        photo_path = Path(candidates[0])
        print(f'  Match: {photo_path}')
        sidecar_path = photo_path.with_name(photo_path.name + '.json')
        if not sidecar_path.exists():
            print(f'  No sidecar: {sidecar_path}')
            no_match += 1
            continue

        sidecar_data = json.loads(sidecar_path.read_text(encoding='utf-8'))
        if sidecar_data.get('createdAt'):
            skipped_has_date += 1
            print(f'  Skipped (has date): {sidecar_data["createdAt"]}')
            continue

        # Prefer photoTakenTime, fallback creationTime
        photo_time = data.get('photoTakenTime', {}) or data.get('creationTime', {})
        ts_sec = photo_time.get('timestamp')
        if not ts_sec:
            skipped_no_ts += 1
            print(f'  Skipped no timestamp')
            continue

        sidecar_data['createdAt'] = unix_sec_to_iso(ts_sec)
        sidecar_data['createdAtSource'] = 'google_takeout'
        sidecar_path.write_text(json.dumps(sidecar_data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'✓ Fixed {photo_path.name} ({photo_path.parent.name}): {ts_sec} → {sidecar_data["createdAt"]}')
        fixed += 1
    except Exception as e:
        print(f'✗ Error {json_path}: {e}')
        errors += 1

print(f'\n=== SUMMARY ===')
print(f'Fixed: {fixed}')
print(f'Skipped (already has date): {skipped_has_date}')
print(f'Skipped (no title/ID): {skipped_no_title}')
print(f'Skipped (no timestamp): {skipped_no_ts}')
print(f'No matching photo/sidecar: {no_match}')
print(f'Errors: {errors}')
print(f'Total JSONs scanned: {fixed + skipped_has_date + skipped_no_title + skipped_no_ts + no_match + errors}')