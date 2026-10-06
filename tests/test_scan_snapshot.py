import json
import tempfile
import unittest
from pathlib import Path
from scripts.publish_scan import publish

ROOT = Path(__file__).resolve().parents[1]

class ScanTests(unittest.TestCase):
    def test_coverage_consistency(self):
        scan = json.loads((ROOT / 'data/runs/2026-10-06T184538Z.json').read_text(encoding='utf-8'))
        c = scan['coverage']
        self.assertEqual(sum(p['direct_attempts'] for p in c['by_portal'].values()), c['direct_attempts'])
        self.assertEqual(c['direct_attempts'], c['historical_cached_pages'] + c['failed_direct_reads'] + c['http_410_copies'])
        self.assertEqual(c['known_copies'], c['direct_attempts'] + c['search_only'])
        self.assertEqual(c['fresh_active_confirmations'], 0)
        self.assertEqual(scan['status'], 'partial')
        self.assertFalse(scan['gone'][0]['sale_confirmed'])
        self.assertTrue(all(not r['used_as_new_price'] for r in scan['discarded_cached_prices']))
    def test_publisher_idempotent_and_separate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root / 'data').mkdir(); (root / 'dashboard').mkdir()
            value = {'run_id':'test','coverage':{},'status':'partial'}
            source = root / 'data/last_run.json'; source.write_text(json.dumps(value))
            index = root / 'dashboard/index.html'; index.write_text('<body><main></main></body>')
            publish(root); publish(root)
            self.assertEqual(index.read_text().count('./scan.js'), 1)
            self.assertEqual(json.loads((root / 'dashboard/scan.json').read_text()), value)
            self.assertEqual(json.loads(source.read_text()), value)
            self.assertFalse((root / 'dashboard/data.json').exists())

if __name__ == '__main__': unittest.main()
