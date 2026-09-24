# Hosted demo

Deploy this Python app using Streamlit Community Cloud. Use `hosted_app.py` as the entrypoint and Python 3.12. Dependencies are in `requirements.txt`; the theme is in `.streamlit/config.toml`.

Each browser session gets a separate temporary SQLite database. Session data is not a durable CRM; export the mapped CSV or save your receipt before closing the session. The hosted entrypoint does not use the local database or Ollama. Its live website fetches are limited to the five demo company domains; other company domains route to Human Review.

The embedded demo CRM stores received records in the same session's database. Sending the same CRM ID updates its record. Each send adds an immutable receipt containing source fields, destination fields, values, response and timestamp. It requires no additional server and never writes to a real CRM.

Deploy only source files and fictional CSV fixtures. Never upload `.venv`, `.env`, Streamlit secrets, local databases, or real imported contacts.

Local preview of hosted behavior:

```sh
streamlit run hosted_app.py
```

Workflow checks:

```sh
python -m unittest discover -s tests -v
```
