"""Local-only CRM handoff client and field mapping."""
from typing import Dict, Tuple
from urllib.parse import urlparse

import requests


def handoff_payload(lead: Dict) -> Dict:
    """A compact schema a CRM integration could map to real destination fields."""
    return {
        "crm_record_id": lead.get("crm_record_id"),
        "company": lead["company"],
        "contact_name": lead["contact_name"],
        "title": lead["title"],
        "account_fit_score": lead.get("account_score"),
        "persona_fit_score": lead.get("persona_score"),
        "icp_score": lead["score"],
        "recommended_route": lead["route"],
        "final_route": lead["final_route"],
        "review_reason": lead.get("review_reason"),
        "outreach_angle": lead["outreach_angle"],
    }


def send_to_local_crm(endpoint: str, payload: Dict) -> Tuple[str, str]:
    """POST only to localhost so this demo cannot send data to an external service."""
    hostname = urlparse(endpoint).hostname
    if hostname not in {"127.0.0.1", "localhost"}:
        return "blocked", "Demo handoff only permits localhost endpoints."
    try:
        response = requests.post(endpoint, json=payload, timeout=8)
        response.raise_for_status()
        return "delivered", response.text
    except requests.RequestException as error:
        return "failed", str(error)
