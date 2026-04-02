from __future__ import annotations

import json
from abc import ABC, abstractmethod
from textwrap import dedent

from openai import OpenAI

from orbitx.schemas import DocumentType, LLMExtraction


class BaseLLMClient(ABC):
    @abstractmethod
    def extract(self, file_name: str, text: str, retry_count: int) -> LLMExtraction:
        raise NotImplementedError


class OpenAILLMClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def extract(self, file_name: str, text: str, retry_count: int) -> LLMExtraction:
        prompt = _build_prompt(file_name=file_name, text=text, retry_count=retry_count)
        response = self.client.responses.create(
            model=self.model,
            input=prompt,
        )
        raw_text = response.output_text.strip()
        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Malformed JSON from LLM: {exc}") from exc
        return LLMExtraction.model_validate(payload)


class MockLLMClient(BaseLLMClient):
    def extract(self, file_name: str, text: str, retry_count: int) -> LLMExtraction:
        doc_type = _detect_type(text)
        if doc_type == "invoice":
            payload = {
                "doc_type": "invoice",
                "extracted_fields": {
                    "vendor_name": _match_after(text, "Vendor:", "Acme Ltd"),
                    "invoice_number": _match_after(text, "Invoice Number:", "INV-0001"),
                    "invoice_date": _match_after(text, "Invoice Date:", "2026-01-10"),
                    "due_date": _match_after(text, "Due Date:", "2026-01-20"),
                    "total_amount": _number_after(text, "Total:", 4200.0),
                    "currency": _match_after(text, "Currency:", "USD"),
                    "customer_name": _match_after(text, "Bill To:", "OrbitX"),
                    "line_items": [],
                },
                "summary": "Invoice covering billed services, vendor details, and payment deadline.",
                "confidence": "medium",
            }
            return LLMExtraction.model_validate(payload)
        if doc_type == "contract":
            payload = {
                "doc_type": "contract",
                "extracted_fields": {
                    "agreement_name": _match_after(text, "Agreement:", "Services Agreement"),
                    "effective_date": _match_after(text, "Effective Date:", "2026-02-01"),
                    "termination_date": _match_after(text, "Termination Date:", "2027-02-01"),
                    "party_one": _match_after(text, "Party One:", "OrbitX Labs"),
                    "party_two": _match_after(text, "Party Two:", "Nova Systems"),
                    "governing_law": _match_after(text, "Governing Law:", "California"),
                    "payment_terms": _match_after(text, "Payment Terms:", "Net 30"),
                    "renewal_terms": _match_after(text, "Renewal Terms:", "Annual renewal"),
                },
                "summary": "Contract defining the agreement scope, parties, dates, and renewal structure.",
                "confidence": "medium",
            }
            return LLMExtraction.model_validate(payload)
        payload = {
            "doc_type": "unknown",
            "extracted_fields": {
                "key_entities": [],
                "important_dates": [],
                "important_numbers": [],
            },
            "summary": "Document content did not strongly match the invoice or contract schema.",
            "confidence": "low",
        }
        return LLMExtraction.model_validate(payload)


def build_llm_client(api_key: str, model: str, use_mock_llm: bool) -> BaseLLMClient:
    if use_mock_llm:
        return MockLLMClient()
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required when USE_MOCK_LLM is false")
    return OpenAILLMClient(api_key=api_key, model=model)


def _build_prompt(file_name: str, text: str, retry_count: int) -> str:
    retry_instruction = ""
    if retry_count > 0:
        retry_instruction = "Your previous output was invalid. Return strict JSON only with no markdown and no extra prose."
    return dedent(
        f"""
        You are an expert document processing system.
        {retry_instruction}

        Read the document and do all of the following:
        1. Detect whether it is an invoice, contract, or unknown.
        2. Extract structured fields using the schema that best matches the detected type.
        3. Use null for missing scalar values and [] for missing array values.
        4. Produce a concise 2 to 4 sentence summary.
        5. Set confidence to high, medium, or low.
        6. Dates must be ISO format YYYY-MM-DD when they can be inferred reliably.
        7. Amounts must be numbers, not strings.

        Return JSON with exactly this shape:
        {{
          "doc_type": "invoice|contract|unknown",
          "extracted_fields": {{
            "vendor_name": null,
            "invoice_number": null,
            "invoice_date": null,
            "due_date": null,
            "total_amount": null,
            "currency": null,
            "customer_name": null,
            "line_items": []
          }},
          "summary": "2 to 4 sentence summary",
          "confidence": "high|medium|low"
        }}

        If the document is a contract, use this extracted_fields shape instead:
        {{
          "agreement_name": null,
          "effective_date": null,
          "termination_date": null,
          "party_one": null,
          "party_two": null,
          "governing_law": null,
          "payment_terms": null,
          "renewal_terms": null
        }}

        If the document is unknown, use this extracted_fields shape instead:
        {{
          "key_entities": [],
          "important_dates": [],
          "important_numbers": []
        }}

        File name: {file_name}
        Document text:
        {text[:12000]}
        """
    ).strip()


def _detect_type(text: str) -> DocumentType:
    lowered = text.lower()
    if "invoice" in lowered or "total:" in lowered:
        return "invoice"
    if "agreement" in lowered or "governing law" in lowered or "party one:" in lowered:
        return "contract"
    return "unknown"


def _match_after(text: str, label: str, fallback: str) -> str | None:
    for line in text.splitlines():
        if line.lower().startswith(label.lower()):
            value = line.split(":", 1)[-1].strip()
            return value or None
    return fallback


def _number_after(text: str, label: str, fallback: float) -> float | None:
    value = _match_after(text, label, str(fallback))
    if value is None:
        return None
    cleaned = value.replace(",", "").replace("$", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return fallback
