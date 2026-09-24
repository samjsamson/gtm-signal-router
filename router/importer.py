"""Safe local parsing for CRM CSV exports."""
from typing import Dict, List, Tuple

from pydantic import ValidationError

from .models import Lead

REQUIRED = ("company", "website", "contact_name", "title")
OPTIONAL = ("employee_count", "industry", "location", "crm_record_id")


def prepare_crm_records(raw_rows: List[Dict[str, str]], mapping: Dict[str, str]) -> Tuple[List[dict], List[dict], int]:
    """Map arbitrary CRM headers to valid leads and reject duplicate/bad records."""
    valid, errors, seen = [], [], set()
    for row_number, raw in enumerate(raw_rows, start=2):
        record = {field: str(raw.get(column) or "").strip() for field, column in mapping.items() if column}
        record["employee_count"] = record.get("employee_count") or 0
        record["industry"] = record.get("industry") or "Unknown"
        record["location"] = record.get("location") or "Unknown"
        record["persona_note"] = "Imported CRM record — verify permission and accuracy before outreach."
        record["source"] = "CRM CSV import"
        duplicate_key = (record.get("company", "").lower(), record.get("contact_name", "").lower())
        if duplicate_key in seen:
            errors.append({"row": row_number, "error": "Duplicate company + contact; skipped."})
            continue
        try:
            lead = Lead.model_validate(record)
        except ValidationError as error:
            errors.append({"row": row_number, "error": error.errors()[0]["msg"]})
            continue
        seen.add(duplicate_key)
        valid.append(lead.model_dump(mode="json"))
    return valid, errors, len(raw_rows)
