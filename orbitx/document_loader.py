from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz


SUPPORTED_EXTENSIONS = {".pdf", ".txt"}


@dataclass(frozen=True)
class ExtractedDocument:
    path: Path
    text: str


def list_documents(folder: Path) -> list[Path]:
    return sorted(path for path in folder.iterdir() if path.is_file())


def extract_document_text(path: Path) -> ExtractedDocument:
    suffix = path.suffix.lower()
    if suffix == ".txt":
        text = path.read_text(encoding="utf-8", errors="ignore")
        return ExtractedDocument(path=path, text=text.strip())
    if suffix == ".pdf":
        try:
            document = fitz.open(path)
        except Exception as exc:
            raise ValueError(f"Unable to open PDF: {exc}") from exc
        parts: list[str] = []
        try:
            for page in document:
                parts.append(page.get_text("text"))
        finally:
            document.close()
        return ExtractedDocument(path=path, text="\n".join(parts).strip())
    raise ValueError(f"Unsupported file type: {suffix}")
