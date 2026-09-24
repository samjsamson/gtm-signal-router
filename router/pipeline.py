import csv
from pathlib import Path
from typing import Union

from .database import connect, save
from .models import Lead
from .ollama import optional_classification
from .scraper import extract_signals
from .scoring import score_and_route


def run(csv_path: Union[str, Path], db_path: Union[str, Path]) -> list[dict]:
    with open(csv_path, newline="", encoding="utf-8") as source:
        return run_records(list(csv.DictReader(source)), db_path)


def run_records(records: list[dict], db_path: Union[str, Path], hosted: bool = False) -> list[dict]:
    conn, outcomes = connect(db_path), []
    signal_cache = {}
    try:
        for row in records:
            lead = Lead.model_validate(row)
            website = str(lead.website)
            if website not in signal_cache:
                signal_cache[website] = extract_signals(website, hosted=hosted)
            signals = signal_cache[website]
            decision = score_and_route(lead, signals)
            decision.llm_summary = None if hosted else optional_classification(lead, signals)
            save(conn, lead, signals, decision)
            outcomes.append({"company": lead.company, "score": decision.score, "route": decision.route})
    finally:
        conn.close()
    return outcomes
