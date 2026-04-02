from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path

from orbitx.config import Settings, ensure_directory
from orbitx.document_loader import SUPPORTED_EXTENSIONS, extract_document_text, list_documents
from orbitx.llm import build_llm_client
from orbitx.schemas import DocumentResult, schema_for_doc_type
from orbitx.validation import validate_record


@dataclass
class PipelineReport:
    processed: int = 0
    failed: int = 0
    skipped: int = 0
    results: list[DocumentResult] = field(default_factory=list)


async def run_pipeline(input_dir: Path, output_file: Path, settings: Settings) -> PipelineReport:
    llm_client = build_llm_client(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        use_mock_llm=settings.use_mock_llm,
    )
    ensure_directory(output_file.parent)
    semaphore = asyncio.Semaphore(settings.max_concurrency)
    report = PipelineReport()
    documents = list_documents(input_dir)
    tasks = [
        _process_path(path=path, llm_client=llm_client, semaphore=semaphore, settings=settings)
        for path in documents
    ]
    for result in await asyncio.gather(*tasks):
        report.results.append(result)
        if result.skipped:
            report.skipped += 1
        elif result.errors:
            report.failed += 1
        else:
            report.processed += 1
    output_file.write_text(
        json.dumps([result.model_dump(mode="json") for result in report.results], indent=2),
        encoding="utf-8",
    )
    return report


async def _process_path(path: Path, llm_client, semaphore: asyncio.Semaphore, settings: Settings) -> DocumentResult:
    async with semaphore:
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return DocumentResult(
                file=path.name,
                doc_type=None,
                extracted_fields=None,
                summary=None,
                confidence=None,
                errors=[f"Unsupported file type: {path.suffix.lower()}"],
                skipped=True,
                skip_reason="unsupported_file_type",
            )
        try:
            extracted_document = await asyncio.to_thread(extract_document_text, path)
        except Exception as exc:
            return DocumentResult(
                file=path.name,
                doc_type=None,
                extracted_fields=None,
                summary=None,
                confidence=None,
                errors=[str(exc)],
                skipped=False,
            )
        if not extracted_document.text.strip():
            return DocumentResult(
                file=path.name,
                doc_type=None,
                extracted_fields=None,
                summary=None,
                confidence=None,
                errors=[],
                skipped=True,
                skip_reason="empty_document",
            )
        extraction = None
        errors: list[str] = []
        for retry_count in range(settings.max_retries + 1):
            try:
                extraction = await asyncio.to_thread(
                    llm_client.extract,
                    extracted_document.path.name,
                    extracted_document.text,
                    retry_count,
                )
                break
            except Exception as exc:
                errors.append(str(exc))
        if extraction is None:
            return DocumentResult(
                file=path.name,
                doc_type=None,
                extracted_fields=None,
                summary=None,
                confidence="low",
                errors=errors,
                skipped=False,
            )
        model = schema_for_doc_type(extraction.doc_type)
        normalized_fields = model.model_validate(extraction.extracted_fields).model_dump(mode="json")
        validation_errors = validate_record(extraction.doc_type, normalized_fields)
        confidence = extraction.confidence
        if errors or validation_errors:
            confidence = "low"
        return DocumentResult(
            file=path.name,
            doc_type=extraction.doc_type,
            extracted_fields=normalized_fields,
            summary=extraction.summary.strip(),
            confidence=confidence,
            errors=errors,
            skipped=False,
            validation_errors=validation_errors,
        )
