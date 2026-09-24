import csv
import hashlib
import io
import json
from pathlib import Path

import streamlit as st

from router.crm import DEFAULT_MAPPING, deliver, mapped_fields, receipts
from router.database import connect, save_review
from router.importer import OPTIONAL, REQUIRED, prepare_crm_records
from router.pipeline import run_records

ROOT = Path(__file__).parent
DB = Path(st.session_state.get('router_db', ROOT / 'data/gtm_router.db'))
ROUTES = ['Tier 1', 'Nurture', 'Disqualify', 'Human Review']
st.set_page_config(page_title='Signal Router · GTM workspace', page_icon='↗', layout='wide')
st.markdown('''<style>
.block-container {max-width:1280px;padding-top:2.5rem;padding-bottom:4rem}
h1 {font-size:2.35rem!important;letter-spacing:-.055em}
h2 {font-size:1.5rem!important;letter-spacing:-.025em}
h3 {font-size:1.1rem!important}
[data-testid="stMetric"] {background:white;border:1px solid #e2e8f0;border-radius:12px;padding:16px 20px}
[data-testid="stMetricValue"] {font-size:1.8rem}
[data-testid="stVerticalBlockBorderWrapper"] {border-radius:14px}
button[data-baseweb="tab"] {font-size:14px;padding:14px 18px}
[data-baseweb="tab-list"] {gap:6px;margin:10px 0 20px;border-bottom:1px solid #dce3ef}
.eyebrow {color:#2563eb;font-size:12px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;margin-bottom:6px}
.subline {color:#607086;font-size:16px;margin-bottom:24px}
</style>''', unsafe_allow_html=True)
st.markdown('<div class="eyebrow">Revenue operations / workspace</div>', unsafe_allow_html=True)
st.title('GTM Signal Router')
st.markdown('<div class="subline">Turn raw leads into scored accounts and mapped CRM records.</div>', unsafe_allow_html=True)
hosted = st.session_state.get('hosted_demo', False)
st.caption('Demo CRM · Fictional sample contacts · ' + ('Private to this browser session; refresh may reset your data.' if hosted else 'Saved on this Mac'))

conn = connect(DB)
rows = [dict(row) for row in conn.execute('SELECT * FROM routed_leads ORDER BY id DESC')]
conn.close()
for row in rows:
    row['final_route'] = row['reviewer_route'] or row['route']
metrics = st.columns(4)
metrics[0].metric('Leads scored', len(rows))
metrics[1].metric('Tier 1 accounts / contacts', sum(r['final_route'] == 'Tier 1' for r in rows))
metrics[2].metric('Awaiting review', sum(r['final_route'] == 'Human Review' for r in rows))
metrics[3].metric('CRM deliveries', sum(r['status'] == 'delivered' for r in receipts(DB)))
tabs = st.tabs(['01  Import leads', '02  Score & fit', '03  Map CRM fields', '04  Human review', '05  CRM handoff'])

with tabs[0]:
    st.header('Start with your raw leads')
    st.caption('Upload a scraped lead list or CRM export. Company websites provide account signals; titles provide persona fit.')
    left, right = st.columns([2, 1], gap='large')
    with left, st.container(border=True):
        uploaded = st.file_uploader('Lead CSV', type='csv')
        if uploaded:
            try:
                reader = csv.DictReader(io.StringIO(uploaded.getvalue().decode('utf-8-sig')))
                headers = reader.fieldnames or []
                raw = list(reader)
                if not headers or len(set(headers)) != len(headers) or any(None in r for r in raw):
                    raise ValueError('Use unique column headers and the same number of columns on every row.')
                if not raw or len(raw) > 500:
                    raise ValueError('Upload between 1 and 500 leads per batch.')
                st.caption(f'{len(raw)} rows detected')
                st.dataframe(raw[:5], hide_index=True, width='stretch')
                aliases = {'company': 'account_name', 'website': 'company_website', 'contact_name': 'full_name',
                           'title': 'job_title', 'location': 'city', 'crm_record_id': 'id'}
                normalized = {h.lower().replace(' ', '_'): h for h in headers}
                mapping = {}
                with st.expander('Match input columns', expanded=True):
                    cols = st.columns(2)
                    for i, field in enumerate(REQUIRED + OPTIONAL):
                        choices = ['Skip'] + headers
                        default = normalized.get(field, normalized.get(aliases.get(field), 'Skip'))
                        mapping[field] = cols[i % 2].selectbox(field.replace('_', ' ').title() + (' *' if field in REQUIRED else ''),
                            choices, index=choices.index(default), key='input-' + field + hashlib.sha256(uploaded.getvalue()).hexdigest()[:8])
                missing = [f for f in REQUIRED if mapping[f] == 'Skip']
                if st.button('Validate & score leads', type='primary', disabled=bool(missing)):
                    records, errors, total = prepare_crm_records(raw, {k:v for k,v in mapping.items() if v != 'Skip'})
                    st.session_state.import_errors = errors
                    if records:
                        with st.spinner('Reading company websites and scoring leads…'):
                            run_records(records, DB, hosted=hosted)
                        st.session_state.import_message = f'{len(records)} of {total} leads scored. Continue to Score & fit.'
                        st.rerun()
            except (ValueError, UnicodeDecodeError, csv.Error) as error:
                st.error(str(error))
        else:
            st.info('Drop a CSV here or start with the 50-person fictional dataset.')
    with right, st.container(border=True):
        st.subheader('Try a complete batch')
        st.write('50 fictional contacts. Five real companies. A full routing workflow.')
        if st.button('Load & score 50 demo leads', type='primary'):
            with (ROOT / 'data/sample_leads.csv').open(newline='', encoding='utf-8') as source:
                records = list(csv.DictReader(source))
            for i, record in enumerate(records, 1001):
                record['crm_record_id'] = f'crm-{i}'
            with st.spinner('Reading five company websites…'):
                run_records(records, DB, hosted=hosted)
            st.session_state.import_message = '50 fictional leads scored. Continue to Score & fit.'
            st.rerun()
        st.download_button('Download sample CSV', (ROOT / 'data/example_crm_import_50.csv').read_bytes(),
                           'fictional_crm_leads_50.csv', 'text/csv')
        st.caption('Each run adds a batch. Website requests go to the listed company domains; personal contact fields are not sent to them.')
        if hosted:
            st.caption('Hosted demo: live website checks cover Apple, NVIDIA, Tesla, Meta and Google. Other domains route to Human Review. Ollama runs only in the local version.')
    if st.session_state.get('import_message'):
        st.success(st.session_state.import_message)
    if st.session_state.get('import_errors'):
        with st.expander('Skipped rows'):
            st.dataframe(st.session_state.import_errors, hide_index=True)

with tabs[1]:
    st.header('See who fits, and why')
    st.caption('Account fit / 70 + persona fit / 30 = ICP score / 100. Weak website evidence always goes to human review.')
    if not rows:
        st.info('Import your first batch to see scores and routing decisions.')
    else:
        filters = st.columns(2)
        companies = filters[0].multiselect('Company', sorted({r['company'] for r in rows}))
        routes = filters[1].multiselect('Route', ROUTES)
        filtered = [r for r in rows if (not companies or r['company'] in companies) and (not routes or r['final_route'] in routes)]
        if not filtered:
            st.info('No leads match these filters.')
        else:
            st.dataframe([{'ID':r['id'], 'Company':r['company'], 'Contact':r['contact_name'], 'Title':r['title'],
                'Account fit':r['account_score'], 'Persona fit':r['persona_score'], 'ICP score':r['score'], 'Route':r['final_route']}
                for r in filtered], hide_index=True, width='stretch', height=340,
                column_config={'Account fit':st.column_config.ProgressColumn(min_value=0,max_value=70,format='%d'),
                               'Persona fit':st.column_config.ProgressColumn(min_value=0,max_value=30,format='%d')})
            selected = st.selectbox('Inspect a lead', [r['id'] for r in filtered],
                format_func=lambda id: next(f"{r['contact_name']} · {r['company']} · #{id}" for r in filtered if r['id']==id))
            lead = next(r for r in filtered if r['id']==selected)
            st.session_state.selected_lead = selected
            a,b = st.columns(2)
            with a, st.container(border=True):
                st.subheader(lead['contact_name'])
                st.write(lead['title'] + ' · ' + lead['company'])
                st.metric(lead['final_route'], f"{lead['score']} / 100")
                st.caption(lead['persona_note'])
            with b, st.container(border=True):
                st.subheader('Decision evidence')
                for reason in json.loads(lead['reasons']):
                    st.write('• ' + reason)
                with st.expander('Website signals & outreach context'):
                    st.write(lead['website'])
                    st.json(json.loads(lead['signals']))
                    st.write(lead['outreach_angle'])
                    if lead['llm_summary']:
                        st.write(lead['llm_summary'])

with tabs[2]:
    st.header('Define your CRM field mapping')
    st.caption('Choose destination field names. This mapping controls both the CSV export and the demo CRM delivery.')
    edited = st.data_editor([{'Source field':k, 'CRM field':v} for k,v in DEFAULT_MAPPING.items()],
        disabled=['Source field'], hide_index=True, width='stretch', key='crm-mapping', height=425)
    crm_mapping = {r['Source field']:r['CRM field'] for r in edited}
    mapping_error = None
    try:
        if rows:
            mapped_fields(rows[0], crm_mapping)
        elif len(set(crm_mapping.values())) != len(crm_mapping):
            raise ValueError('Destination field names must be unique.')
    except (ValueError, TypeError) as error:
        mapping_error = str(error)
        st.error(mapping_error)
    st.caption('Example: ICP score → lead_score; final route → lifecycle_stage. Destination: demonstration CRM.')

with tabs[3]:
    st.header('Handle the exceptions')
    st.caption('Make a one-off decision before delivery. The original automated route remains in the record.')
    if not rows:
        st.info('Import leads first.')
    else:
        review_id = st.selectbox('Lead to review', [r['id'] for r in rows],
            format_func=lambda id: next(f"{r['contact_name']} · {r['company']} · {r['final_route']} · #{id}" for r in rows if r['id']==id))
        review_lead = next(r for r in rows if r['id']==review_id)
        with st.form('review'):
            col1,col2 = st.columns([1,3])
            route = col1.selectbox('Final route', ROUTES, index=ROUTES.index(review_lead['final_route']))
            reason = col2.text_input('Reason for decision', placeholder='What makes this lead an exception?')
            submitted = st.form_submit_button('Save review')
        if submitted:
            if not reason.strip():
                st.error('Add a reason so the decision can be explained later.')
            else:
                save_review(DB, review_id, route, reason)
                st.rerun()
        if review_lead['reviewed_at']:
            st.success(f"Saved {review_lead['reviewed_at']} UTC · {review_lead['review_reason']}")

with tabs[4]:
    st.header('Deliver leads. Keep the receipt.')
    st.caption('The demo CRM receives mapped records inside this app. No Salesforce or HubSpot account is connected.')
    if not rows:
        st.info('Import and score leads before sending them.')
    else:
        chosen = st.multiselect('Leads to send', [r['id'] for r in rows],
            default=[st.session_state.get('selected_lead', rows[0]['id'])],
            format_func=lambda id: next(f"{r['contact_name']} · {r['company']} · #{id}" for r in rows if r['id']==id))
        selected_rows = [r for r in rows if r['id'] in chosen]
        st.caption(f'{len(selected_rows)} selected · Re-sending the same CRM ID updates its demo record.')
        actions = st.columns([1,1,2])
        if actions[0].button('Send to demo CRM', type='primary', disabled=not selected_rows or bool(mapping_error)):
            for lead in selected_rows:
                deliver(DB, lead, crm_mapping)
            st.session_state.delivery_message = f'{len(selected_rows)} records delivered to the demo CRM.'
            st.rerun()
        if selected_rows and not mapping_error:
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=list(crm_mapping.values()))
            writer.writeheader()
            for lead in selected_rows:
                values = {f['CRM field']:f['Value sent'] for f in mapped_fields(lead, crm_mapping)}
                writer.writerow({k: ("'"+v if isinstance(v,str) and v.startswith(('=', '+', '-', '@')) else v) for k,v in values.items()})
            actions[1].download_button('Export mapped CSV', output.getvalue(), 'crm_mapped_leads.csv', 'text/csv')
        if st.session_state.get('delivery_message'):
            st.success(st.session_state.delivery_message)
    history = receipts(DB)
    if history:
        st.subheader('Delivery receipts')
        receipt_id = st.selectbox('Sent record', [r['id'] for r in history],
            format_func=lambda id: next(f"#{id} · lead {r['routed_lead_id']} · {r['status']} · {r['attempted_at']} UTC" for r in history if r['id']==id))
        receipt = next(r for r in history if r['id']==receipt_id)
        snapshot = json.loads(receipt['payload'])
        st.caption('Snapshot at send time. Changing the mapping or reviewing a lead does not change an earlier receipt.')
        if 'fields' in snapshot:
            st.dataframe([{**f, 'Value sent': '' if f['Value sent'] is None else str(f['Value sent'])}
                          for f in snapshot['fields']], hide_index=True, width='stretch')
        else:
            st.json(snapshot)
        with st.expander('Receiver response'):
            st.code(receipt['response_body'])
