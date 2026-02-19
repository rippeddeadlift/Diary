#!/usr/bin/env python3
# Google Photos Takeout Backfill: fill createdAt from Takeout JSON timestamps
# Usage: cd Diary; python tools/google_takeout_backfill.py /path/to/Takeout/Google\\ Photos/JSON/
# Matches JSON 'title' (IMG_7316.JPG) to data/photos/inbox/*/*.JPG sidecar
# Sets createdAt from 'photoTakenTime.timestamp' (unix sec → ISO UTC)

import json
import sys
from pathlib import Path
from datetime import datetime

DATA_INBOX = Path('data/photos/inbox').resolve()

def unix_sec_to_iso(ts_sec: str) -> str:
    dt = datetime.utcfromtimestamp(int(ts_sec))
    return dt.isoformat(timespec='seconds') + 'Z'

if len(sys.argv) != 2:
    print('Usage: python google_takeout_backfill.py <takeout_json_root>')
    sys.exit(1)

takeout_root = Path(sys.argv[1]).resolve()
if not takeout_root.exists():
    print(f'Error: {takeout_root} not found')
    sys.exit(1)

fixed = skipped_has_date = skipped_no_ts = no_match = errors = 0

for json_path in takeout_root.rglob('*.json'):
    try:
        data = json.loads(json_path.read_text(encoding='utf-8'))
        title = data.get('title', '')
        if not title:
            skipped_no_ts += 1
            continue

        photo_name = title  # e.g. 'IMG_7316.JPG'

        # Find matching photo sidecar in inbox
        photo_path = None
        for folder in DATA_INBOX.iterdir():
            if folder.is_dir():
                candidate = folder / photo_name
                if candidate.exists():
                    photo_path = candidate
                    break

        if not photo_path:
            no_match += 1
            continue

        sidecar_path = photo_path.with_suffix('.json')
        if not sidecar_path.exists():
            no_match += 1
            continue

        sidecar_data = json.loads(sidecar_path.read_text(encoding='utf-8'))
        if sidecar_data.get('createdAt'):
            skipped_has_date += 1
            continue

        photo_time = data.get('photoTakenTime', {})
        ts_sec = photo_time.get('timestamp')
        if not ts_sec:
            skipped_no_ts += 1
            continue

        sidecar_data['createdAt'] = unix_sec_to_iso(ts_sec)
        sidecar_path.write_text(json.dumps(sidecar_data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

        print(f'✓ Fixed {photo_path.name} ({photo_path.parent.name}): {ts_sec} → {sidecar_data["createdAt"]}')
        fixed += 1

    except Exception as e:
        print(f'✗ Error {json_path}: {e}')
        errors += 1

print(f'\n=== SUMMARY ===')
print(f'Fixed: {fixed}')
print(f'Skipped (already has date): {skipped_has_date}')
print(f'Skipped (no timestamp): {skipped_no_ts}')
print(f'No matching photo/sidecar: {no_match}')
print(f'Errors: {errors}')
print(f'Total JSONs scanned: {fixed + skipped_has_date + skipped_no_ts + no_match + errors}')
