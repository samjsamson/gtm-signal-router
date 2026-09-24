"""Mapped, auditable delivery to an embedded demonstration CRM."""
import json
import re
from .database import connect
from .handoff import handoff_payload

DEFAULT_MAPPING = {
    'crm_record_id': 'external_id', 'company': 'company_name',
    'contact_name': 'contact_name', 'title': 'job_title',
    'account_fit_score': 'account_fit', 'persona_fit_score': 'persona_fit',
    'icp_score': 'lead_score', 'recommended_route': 'suggested_route',
    'final_route': 'lifecycle_stage', 'review_reason': 'review_notes',
    'outreach_angle': 'outreach_context',
}

def mapped_fields(lead, mapping):
    destinations = list(mapping.values())
    if not mapping or len(set(destinations)) != len(destinations):
        raise ValueError('Choose a unique destination for every mapped field.')
    if any(not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,63}', name) for name in destinations):
        raise ValueError('CRM field names must start with a letter and use letters, numbers or underscores.')
    source = handoff_payload(lead)
    return [{'Source field': key, 'CRM field': target, 'Value sent': source[key]}
            for key, target in mapping.items()]

def deliver(path, lead, mapping):
    fields = mapped_fields(lead, mapping)
    payload = {field['CRM field']: field['Value sent'] for field in fields}
    record_key = lead.get('crm_record_id') or 'local-' + str(lead['id'])
    receipt = {'destination': 'Embedded demo CRM', 'record_key': record_key,
               'fields': fields, 'payload': payload}
    conn = connect(path)
    try:
        with conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS demo_crm_records
                (record_key TEXT PRIMARY KEY, payload TEXT NOT NULL, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
            conn.execute('''INSERT INTO demo_crm_records (record_key, payload) VALUES (?, ?)
                ON CONFLICT(record_key) DO UPDATE SET payload=excluded.payload, updated_at=CURRENT_TIMESTAMP''',
                (record_key, json.dumps(payload)))
            conn.execute('''INSERT INTO crm_handoffs
                (routed_lead_id, endpoint, payload, status, response_body) VALUES (?, ?, ?, ?, ?)''',
                (lead['id'], 'embedded-demo-crm', json.dumps(receipt), 'delivered',
                 json.dumps({'status': 'received', 'record_key': record_key})))
    finally:
        conn.close()
    return receipt

def receipts(path):
    conn = connect(path)
    try:
        return [dict(row) for row in conn.execute('SELECT * FROM crm_handoffs ORDER BY id DESC LIMIT 100')]
    finally:
        conn.close()
