import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from router.crm import DEFAULT_MAPPING, deliver, mapped_fields, receipts
from router.database import connect, save_review
from router.models import Signals
from router.pipeline import run_records
from router.scraper import extract_signals

ROOT = Path(__file__).resolve().parents[1]

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / 'test.db'
        record = dict(company='Apple', website='https://www.apple.com', employee_count=1000,
                      industry='Technology', contact_name='Test Person', title='Head of Revenue Operations',
                      location='Demo', persona_note='Fictional test persona', crm_record_id='test-001')
        with patch('router.pipeline.extract_signals', return_value=Signals(scraped=True,b2b=True,confidence=.9)):
            run_records([record], self.db)
        conn = connect(self.db)
        self.lead = dict(conn.execute('SELECT * FROM routed_leads').fetchone())
        conn.close()
        self.lead['final_route'] = self.lead['route']

    def tearDown(self):
        self.temp.cleanup()

    def test_receipt_preserves_sent_mapping_and_value(self):
        mapping = {**DEFAULT_MAPPING, 'icp_score': 'Custom_Score'}
        deliver(self.db, self.lead, mapping)
        mapping['icp_score'] = 'Changed'
        snapshot = json.loads(receipts(self.db)[0]['payload'])
        self.assertEqual(snapshot['payload']['Custom_Score'], self.lead['score'])
        self.assertNotIn('Changed', snapshot['payload'])

    def test_repeated_send_updates_receiver(self):
        deliver(self.db, self.lead, DEFAULT_MAPPING)
        self.lead['final_route'] = 'Tier 1'
        deliver(self.db, self.lead, DEFAULT_MAPPING)
        conn = connect(self.db)
        records = conn.execute('SELECT payload FROM demo_crm_records').fetchall()
        conn.close()
        self.assertEqual(len(records), 1)
        self.assertEqual(json.loads(records[0][0])['lifecycle_stage'], 'Tier 1')
        self.assertEqual(len(receipts(self.db)), 2)

    def test_duplicate_fields_rejected(self):
        with self.assertRaises(ValueError):
            mapped_fields(self.lead, {k:'same' for k in DEFAULT_MAPPING})

    def test_hosted_domain_restriction(self):
        with patch('router.scraper.requests.get') as get:
            self.assertFalse(extract_signals('https://127.0.0.1/', hosted=True).scraped)
            get.assert_not_called()

    def test_ui_empty_filter_and_delivery(self):
        app = AppTest.from_file(str(ROOT / 'app.py'))
        app.session_state['router_db'] = str(self.db)
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.tabs), 5)
        next(m for m in app.multiselect if m.label == 'Route').set_value(['Disqualify']).run()
        self.assertFalse(app.exception)
        next(b for b in app.button if b.label == 'Send to demo CRM').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(receipts(self.db)), 1)

    def test_review_used_in_delivery(self):
        save_review(self.db, self.lead['id'], 'Tier 1', 'Verified by reviewer')
        app = AppTest.from_file(str(ROOT / 'app.py'))
        app.session_state['router_db'] = str(self.db)
        app.run()
        next(b for b in app.button if b.label == 'Send to demo CRM').click().run()
        self.assertFalse(app.exception)
        payload = json.loads(receipts(self.db)[0]['payload'])['payload']
        self.assertEqual(payload['lifecycle_stage'], 'Tier 1')
        self.assertEqual(payload['review_notes'], 'Verified by reviewer')

if __name__ == '__main__':
    unittest.main()
