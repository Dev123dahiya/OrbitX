from __future__ import annotations

from datetime import date
from typing import Any

from orbitx.schemas import DocumentType


def validate_record(doc_type: DocumentType, extracted_fields: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if doc_type == "invoice":
        total_amount = extracted_fields.get("total_amount")
        if total_amount is not None and not isinstance(total_amount, (int, float)):
            errors.append("total_amount must be numeric")
        for key in ("invoice_date", "due_date"):
            value = extracted_fields.get(key)
            if value is not None and not _is_iso_date(value):
                errors.append(f"{key} must be an ISO date string")
    if doc_type == "contract":
        for key in ("effective_date", "termination_date"):
            value = extracted_fields.get(key)
            if value is not None and not _is_iso_date(value):
                errors.append(f"{key} must be an ISO date string")
    return errors


def _is_iso_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False
