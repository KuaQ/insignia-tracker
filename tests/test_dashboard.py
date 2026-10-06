import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('builder', ROOT / 'scripts/build_dashboard_data.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
SOURCE = json.loads((ROOT / 'data/recovered_history_2026-10-06.json').read_text(encoding='utf-8'))


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.rows, self.events = builder.recovered_payload(SOURCE)

    def test_entire_historical_set(self):
        self.assertEqual(len(self.rows), 53)
        self.assertEqual(sum(r['status'] == 'active' for r in self.rows.values()), 51)
        self.assertEqual(sum(r['status'] == 'sold' for r in self.rows.values()), 1)
        self.assertEqual(sum(r['status'] == 'gone' for r in self.rows.values()), 1)

    def test_no_reset_of_first_seen(self):
        self.assertEqual(self.rows['ID6HYQae']['first_seen'], '2026-10-02')
        self.assertIsNone(self.rows['ID6Ifr03']['first_seen'])

    def test_unknown_is_not_absent(self):
        self.assertNotIn('acc', self.rows['ID6IgSC6']['equipment'])
        self.assertIsNone(self.rows['ID6I3c9I']['gearbox'])
        self.assertIs(self.rows['ID6Igw4T']['equipment']['heated_steering'], False)

    def test_multiple_sources_preserved(self):
        self.assertEqual(len(self.rows['ID6Ig2tj']['copies']), 2)
        self.assertEqual(self.rows['AP4503-3017-RS']['copies'][1]['status'], 'gone')
        self.assertEqual(self.rows['AP4503-3017-RS']['status'], 'active')
        self.assertEqual(self.rows['OLX1099130583']['copies'][1]['price_pln'], 64000)

    def test_damaged_not_in_clean_sample(self):
        self.assertTrue(self.rows['ID6IbQAE']['problematic'])
        self.assertIn('vin_raw', self.rows['ID6IbQAE'])
        self.assertNotIn('vin', self.rows['ID6IbQAE'])

    def test_corrections_are_not_market_events(self):
        e = [e for e in self.events if e['key'] == 'ID6IfxyK']
        self.assertTrue(any(x['type'] == 'data_correction' for x in e))
        self.assertFalse(any(x['type'] == 'price_down' for x in e))

    def test_scraper_test_cannot_overwrite_curated_data(self):
        old = copy.deepcopy(self.rows)
        builder.merge_newer(self.rows, {'bad': {'key': 'ID6IgSC6', 'price_pln': 1, 'last_seen': '2026-10-07'}})
        self.assertEqual(old, self.rows)

    def test_verified_update_preserves_history_and_copies(self):
        builder.merge_newer(self.rows, {'one': {'key': 'ID6Ig2tj', 'price_pln': 49000,
            'observed_at': '2026-10-07T08:00:00+02:00', 'data_source': 'chat_tracker_run'}})
        row = self.rows['ID6Ig2tj']
        self.assertEqual(row['price_pln'], 49000)
        self.assertEqual(row['first_seen'], '2026-09-30')
        self.assertEqual(len(row['copies']), 2)

    def test_sold_not_reactivated_without_evidence(self):
        builder.merge_newer(self.rows, {'one': {'key': 'ID6HYQae', 'status': 'active',
            'observed_at': '2026-10-07T08:00:00+02:00', 'data_source': 'chat_tracker_run'}})
        self.assertEqual(self.rows['ID6HYQae']['status'], 'sold')

    def test_empty_runtime_still_builds_full_panel(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'data').mkdir()
            (root / 'data/recovered_history_2026-10-06.json').write_text(json.dumps(SOURCE), encoding='utf-8')
            (root / 'data/listings.json').write_text('{}', encoding='utf-8')
            payload = builder.build(root)
            self.assertEqual(len(payload['listings']), 53)
            self.assertEqual(len(json.loads((root / 'dashboard/data.json').read_text())['listings']), 53)


if __name__ == '__main__':
    unittest.main()
