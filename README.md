# OrbitX AI Document Processing Workflow

OrbitX is a batch document-processing pipeline built for the take-home assessment. It accepts a folder of mixed documents, extracts text from supported files, detects document type, uses an LLM to generate structured fields plus a concise summary, validates the result, and writes machine-readable JSON output for every document processed.

## Highlights

- Supports `.pdf` and `.txt`
- Gracefully skips unsupported files
- Detects `invoice`, `contract`, and `unknown`
- Uses type-specific extraction schemas
- Retries malformed LLM responses
- Validates dates and numeric amounts
- Processes files concurrently
- Ships with sample documents and a reproducible CLI flow

## Flow

```mermaid
flowchart LR
    A[Input Folder] --> B[File Filter]
    B --> C[Text Extraction]
    C --> D[LLM Extraction]
    D --> E[Schema Normalization]
    E --> F[Validation]
    F --> G[JSON Output]
```

## Project Structure

```text
orbitx/
  __main__.py
  cli.py
  config.py
  document_loader.py
  llm.py
  pipeline.py
  schemas.py
  validation.py
sample_docs/
output/
```

## Tech Choices

- Python for the CLI pipeline and batch orchestration
- PyMuPDF for PDF text extraction
- OpenAI Responses API for LLM-based detection, extraction, and summarization
- Pydantic for schema normalization and output consistency
- `asyncio` for concurrent document processing

## Tradeoffs

- I chose JSON output instead of Google Sheets so the submission is easier to run and verify locally.
- The default implementation targets OpenAI, but a mock LLM mode is included so the pipeline can be demonstrated without an API key.
- OCR for scanned PDFs is not implemented in the main path, but the design isolates text extraction so OCR can be added without touching the LLM or output layers.

## Supported Schemas

### Invoice

- `vendor_name`
- `invoice_number`
- `invoice_date`
- `due_date`
- `total_amount`
- `currency`
- `customer_name`
- `line_items`

### Contract

- `agreement_name`
- `effective_date`
- `termination_date`
- `party_one`
- `party_two`
- `governing_law`
- `payment_terms`
- `renewal_terms`

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file from `.env.example` and set your API key if you want to run the real LLM flow.

## Environment Variables

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `MAX_CONCURRENCY`
- `MAX_RETRIES`
- `USE_MOCK_LLM`

## Run

### Real LLM mode

```bash
python -m orbitx --input-dir sample_docs --output-file output/results.json
```

### Mock mode for local verification

```bash
set USE_MOCK_LLM=true
python -m orbitx --input-dir sample_docs --output-file output/results.json
```

## Output Shape

Each processed document is written as a JSON object with this structure:

```json
{
  "file": "invoice_april.pdf",
  "doc_type": "invoice",
  "extracted_fields": {
    "vendor_name": "Aster Labs",
    "invoice_number": "INV-2048"
  },
  "summary": "A short 2 to 4 sentence summary.",
  "confidence": "high",
  "errors": [],
  "skipped": false,
  "skip_reason": null,
  "validation_errors": []
}
```

## Edge Cases Covered

- Unsupported file types are skipped with a recorded error
- Corrupt PDFs return a file-level error and the batch continues
- Empty files are skipped with `skip_reason: "empty_document"`
- Missing fields stay `null` instead of `"N/A"`
- Malformed LLM output triggers retries and eventually downgrades confidence
- Validation issues are surfaced in `validation_errors`

## Sample Run Summary

The included sample set covers:

- Invoice in PDF format
- Invoice in TXT format
- Contract in PDF format
- Empty TXT file
- Unsupported file type

This gives visible coverage for success, skip, and validation-friendly paths in a single demo.

## Demo Notes

For the demo video, run the sample batch once in mock mode to show the pipeline end-to-end, then optionally rerun with a real API key to show live extraction quality.

## Future Improvements

- OCR fallback for scanned PDFs
- Vision model support for image-heavy documents
- Per-document prompt specialization beyond `invoice` and `contract`
- CSV and Google Sheets exporters
- Token usage and latency metrics in the final report
