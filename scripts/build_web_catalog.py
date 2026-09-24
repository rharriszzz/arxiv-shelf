"""Export the merged portable catalog for the static browser edition."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from catalog import Catalog

EVENTS = list((ROOT / 'catalog').glob('*.json'))
papers, _ = Catalog(ROOT / 'catalog').read_state()
latest = max((path.stat().st_mtime for path in EVENTS), default=None)
updated = datetime.fromtimestamp(latest, timezone.utc).date().isoformat() if latest else None
output = ROOT / 'dist' / 'catalog.json'
output.write_text(
    json.dumps({'updated': updated, 'papers': papers}, ensure_ascii=False, separators=(',', ':')) + '\n',
    encoding='utf-8',
)
print(f'Exported {len(papers)} papers to {output.relative_to(ROOT)}')
