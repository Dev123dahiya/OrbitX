from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


DocumentType = Literal["invoice", "contract", "unknown"]
ConfidenceLevel = Literal["high", "medium", "low"]


class InvoiceLineItem(BaseModel):
    description: str | None = None
    quantity: float | None = None
    unit_price: float | None = None
    amount: float | None = None


class InvoiceFields(BaseModel):
    vendor_name: str | None = None
    invoice_number: str | None = None
    invoice_date: str | None = None
    due_date: str | None = None
    total_amount: float | None = None
    currency: str | None = None
    customer_name: str | None = None
    line_items: list[InvoiceLineItem] = Field(default_factory=list)


class ContractFields(BaseModel):
    agreement_name: str | None = None
    effective_date: str | None = None
    termination_date: str | None = None
    party_one: str | None = None
    party_two: str | None = None
    governing_law: str | None = None
    payment_terms: str | None = None
    renewal_terms: str | None = None


class UnknownFields(BaseModel):
    key_entities: list[str] = Field(default_factory=list)
    important_dates: list[str] = Field(default_factory=list)
    important_numbers: list[str] = Field(default_factory=list)


class LLMExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    doc_type: DocumentType
    extracted_fields: dict[str, Any]
    summary: str
    confidence: ConfidenceLevel


class DocumentResult(BaseModel):
    file: str
    doc_type: DocumentType | None
    extracted_fields: dict[str, Any] | None
    summary: str | None
    confidence: ConfidenceLevel | None
    errors: list[str] = Field(default_factory=list)
    skipped: bool = False
    skip_reason: str | None = None
    validation_errors: list[str] = Field(default_factory=list)


def schema_for_doc_type(doc_type: DocumentType) -> type[BaseModel]:
    if doc_type == "invoice":
        return InvoiceFields
    if doc_type == "contract":
        return ContractFields
    return UnknownFields
