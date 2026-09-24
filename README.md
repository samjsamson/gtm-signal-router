# GTM Signal Router

A Python GTM workflow that imports lead CSVs, extracts company website signals, scores account and persona fit, supports human review, and delivers mapped records to a simulated CRM.

## Five-stage workspace

1. **Import leads:** upload a raw lead list or CRM export, match input columns, validate rows, and score the batch. Alternatively load 50 fictional contacts across Apple, NVIDIA, Tesla, Meta and Google.
2. **Score & fit:** filter the queue, compare account fit (70 points) and persona fit (30 points), and inspect the reasons behind each decision.
3. **Map CRM fields:** edit destination field names. Both export and delivery use this mapping.
4. **Human review:** override a single route with a reason while retaining the original recommendation.
5. **CRM handoff:** send selected records to the embedded demo CRM or download a mapped CSV. Each delivery receipt shows the source field, destination field, and exact value sent. Later mapping changes do not alter old receipts.

The receiver is simulated; no Salesforce or HubSpot account is connected. Repeated sends with the same CRM ID update one receiver record and create a new audit receipt. The original standalone HTTP mock server remains available for API experimentation; the redesigned dashboard uses the embedded receiver so it also works when hosted.

## Run locally

Requires Python 3.9+ (Python 3.12 recommended for new installs).

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The local app uses `data/gtm_router.db`. Existing saved data is preserved and schema additions are automatic. The 50-person samples are fictional; the company names and websites are real. Employee counts are illustrative seed inputs, not verified current figures. This app does not scrape people.

## Hosted demo

See [DEPLOYMENT.md](DEPLOYMENT.md). The hosted entrypoint is `hosted_app.py`. Each visitor receives an isolated temporary workspace; records may disappear after the session ends or the service restarts. The embedded demo CRM works without a second server.

Hosted website checks cover only the five demo companies. Other website domains produce no enrichment evidence and route to Human Review. The local version supports other public company sites. Website requests leave the machine/server; lead contact fields are not sent to company websites.

## Scoring and limitations

Tier 1 requires 80+ points, Nurture 50–79, and Disqualify fewer than 50. Failed website fetches or weak keyword evidence take precedence and route to Human Review. These are illustrative rules for a revenue-operations tool; scores are not validated purchase probabilities. Homepage keyword checks are basic heuristics, not verified buying intent. Duplicate company/contact pairs are skipped within each CSV upload; separate imports remain separate decision histories.

## Optional local Ollama

With Ollama installed and running:

```sh
ollama pull llama3.2:3b
export USE_OLLAMA=1
export OLLAMA_MODEL=llama3.2:3b
streamlit run app.py
```

Ollama adds a local research note; deterministic scoring controls routing. The hosted demo disables Ollama.

## Verify

```sh
python -m unittest discover -s tests -v
```

Checks cover the UI workflow, empty filters, reviewed routes, mapping validation, immutable delivery receipts, repeat delivery behavior, and the hosted website allowlist.
