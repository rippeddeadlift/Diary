#!/usr/bin/env python3
# Google Photos Takeout Backfill: fill createdAt and location from Takeout JSON timestamps
# Usage: cd Diary; python tools/google_takeout_backfill.py /path/to/Takeout/Google\ Photos/JSON/
# python tools/google_takeout_backfill.py "C:\Users\ivank\Downloads\GOOGLEFOTOS\Takeout"

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
    print('Usage: python tools/google_takeout_backfill.py "C:\\Users\\ivank\\Downloads\\test"')
    sys.exit(1)

takeout_root = Path(sys.argv[1]).resolve()
if not takeout_root.exists():
    print(f'Error: {takeout_root} not found')
    sys.exit(1)

fixed = skipped_has_date_and_loc = skipped_no_title = skipped_no_ts = no_match = errors = 0

for json_path in takeout_root.rglob('*.json'):
    try:
        data = json.loads(json_path.read_text(encoding='utf-8'))
        title = data.get('title', '')
        if not title:
            skipped_no_title += 1
            continue

        # Extract ID: IMG_7994.JPG → '7994'
        match = re.search(r'IMG_(\d+)\.', title)
        if not match:
            skipped_no_title += 1
            continue
            
        photo_id = match.group(1)

        candidates = glob.glob(str(DATA_INBOX / '**' / f'*IMG_{photo_id}*.jp*g'), recursive=True)
        if not candidates:
            no_match += 1
            continue

        # 1. Daten aus dem Takeout JSON extrahieren
        photo_time = data.get('photoTakenTime', {}) or data.get('creationTime', {})
        ts_sec = photo_time.get('timestamp')
        
        geo_data = data.get('geoData', {})
        lat = geo_data.get('latitude')
        lon = geo_data.get('longitude')
        
        if not ts_sec:
            skipped_no_ts += 1
            continue

        # 2. Alle gefundenen Bilder in deiner Inbox durchgehen
        applied_to_any = False
        
        for cand in candidates:
            photo_path = Path(cand)
            sidecar_path = photo_path.with_name(photo_path.name + '.json')

            if not sidecar_path.exists():
                continue

            sidecar_data = json.loads(sidecar_path.read_text(encoding='utf-8'))
            needs_save = False
            
            # A) Datum prüfen und ggf. eintragen
            if not sidecar_data.get('createdAt'):
                sidecar_data['createdAt'] = unix_sec_to_iso(ts_sec)
                sidecar_data['createdAtSource'] = 'google_takeout'
                needs_save = True
                
            # B) Location prüfen und ggf. eintragen (nur wenn Google echte Koordinaten liefert)
            if lat and lon and (abs(lat) > 0.001 or abs(lon) > 0.001):
                if not sidecar_data.get('location'):
                    sidecar_data['location'] = {
                        'lat': lat,
                        'lon': lon,
                        'source': 'google_takeout'
                    }
                    needs_save = True

            # Wenn wir etwas geändert haben -> Speichern!
            if needs_save:
                sidecar_path.write_text(json.dumps(sidecar_data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
                print(f'✓ Updated {photo_path.name} (Date/Location from Takeout)')
                fixed += 1
                applied_to_any = True

        if not applied_to_any:
            skipped_has_date_and_loc += 1

    except Exception as e:
        print(f'✗ Error {json_path}: {e}')
        errors += 1

print(f'\n=== SUMMARY ===')
print(f'Updated sidecars: {fixed}')
print(f'Skipped (no update needed): {skipped_has_date_and_loc}')
print(f'Skipped (no title/ID): {skipped_no_title}')
print(f'Skipped (no timestamp): {skipped_no_ts}')
print(f'No matching photo/sidecar: {no_match}')
print(f'Errors: {errors}')