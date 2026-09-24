import json
import sqlite3
from pathlib import Path
from typing import Union

from .models import Decision, Lead, Signals

SCHEMA = """
CREATE TABLE IF NOT EXISTS routed_leads (
 id INTEGER PRIMARY KEY, company TEXT, website TEXT, employee_count INTEGER, industry TEXT,
 contact_name TEXT, title TEXT, location TEXT, persona_note TEXT, score INTEGER, route TEXT,
 account_score INTEGER, persona_score INTEGER, reasons TEXT, outreach_angle TEXT, llm_summary TEXT, signals TEXT,
 reviewer_route TEXT, review_reason TEXT, reviewed_at TEXT, crm_record_id TEXT, source TEXT,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
"""

HANDOFF_SCHEMA = """
CREATE TABLE IF NOT EXISTS crm_handoffs (
 id INTEGER PRIMARY KEY, routed_lead_id INTEGER NOT NULL, endpoint TEXT NOT NULL, payload TEXT NOT NULL,
 status TEXT NOT NULL, response_body TEXT, attempted_at TEXT DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(routed_lead_id) REFERENCES routed_leads(id)
)
"""

MIGRATIONS = {
    "account_score": "INTEGER",
    "persona_score": "INTEGER",
    "reviewer_route": "TEXT",
    "review_reason": "TEXT",
    "reviewed_at": "TEXT",
    "crm_record_id": "TEXT",
    "source": "TEXT",
}


def connect(path: Union[str, Path]) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    conn.execute(HANDOFF_SCHEMA)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(routed_leads)")}
    for name, kind in MIGRATIONS.items():
        if name not in columns:
            conn.execute("ALTER TABLE routed_leads ADD COLUMN " + name + " " + kind)
    conn.commit()
    return conn


def save(conn: sqlite3.Connection, lead: Lead, signals: Signals, decision: Decision) -> None:
    conn.execute("""INSERT INTO routed_leads (company,website,employee_count,industry,contact_name,title,location,persona_note,score,route,account_score,persona_score,reasons,outreach_angle,llm_summary,signals,crm_record_id,source)
VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (lead.company, str(lead.website), lead.employee_count, lead.industry,
        lead.contact_name, lead.title, lead.location, lead.persona_note, decision.score, decision.route,
        decision.account_score, decision.persona_score, json.dumps(decision.reasons), decision.outreach_angle,
        decision.llm_summary, signals.model_dump_json(), lead.crm_record_id, lead.source))
    conn.commit()


def clear_history(path: Union[str, Path]) -> None:
    """Delete only locally generated routing history; keep the database schema."""
    conn = connect(path)
    conn.execute("DELETE FROM routed_leads")
    conn.commit()
    conn.close()


def save_review(path: Union[str, Path], lead_id: int, reviewer_route: str, review_reason: str) -> None:
    conn = connect(path)
    conn.execute("""UPDATE routed_leads
                    SET reviewer_route = ?, review_reason = ?, reviewed_at = CURRENT_TIMESTAMP
                    WHERE id = ?""", (reviewer_route, review_reason.strip(), lead_id))
    conn.commit()
    conn.close()


def record_handoff(path: Union[str, Path], lead_id: int, endpoint: str, payload: dict,
                   status: str, response_body: str) -> None:
    conn = connect(path)
    conn.execute("""INSERT INTO crm_handoffs (routed_lead_id, endpoint, payload, status, response_body)
                    VALUES (?, ?, ?, ?, ?)""",
                 (lead_id, endpoint, json.dumps(payload), status, response_body[:1000]))
    conn.commit()
    conn.close()


def latest_handoff(path: Union[str, Path], lead_id: int):
    conn = connect(path)
    row = conn.execute("""SELECT status, attempted_at, response_body FROM crm_handoffs
                          WHERE routed_lead_id = ? ORDER BY id DESC LIMIT 1""", (lead_id,)).fetchone()
    conn.close()
    return dict(row) if row else None
