"""Publish the most recent scan outcome separately from historical listing data."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def publish(root=ROOT):
    root = Path(root)
    source = root / 'data/last_run.json'
    if not source.exists():
        return
    scan = json.loads(source.read_text(encoding='utf-8'))
    if not scan.get('run_id') or not isinstance(scan.get('coverage'), dict):
        return
    out = root / 'dashboard'
    (out / 'scan.json').write_text(json.dumps(scan, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    index = out / 'index.html'
    text = index.read_text(encoding='utf-8')
    if './scan.js' not in text:
        if '</body>' not in text:
            raise ValueError('Dashboard HTML body missing')
        index.write_text(text.replace('</body>', '<script src="./scan.js"></script></body>'), encoding='utf-8')
    print('Published scan', scan['run_id'], 'status:', scan.get('status'))

if __name__ == '__main__':
    publish()
