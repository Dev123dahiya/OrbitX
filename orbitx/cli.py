from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from orbitx.config import load_settings
from orbitx.pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="AI document processing workflow")
    parser.add_argument("--input-dir", default="sample_docs", help="Folder containing PDF and TXT documents")
    parser.add_argument("--output-file", default="output/results.json", help="Path for the output JSON file")
    args = parser.parse_args()

    settings = load_settings()
    input_dir = Path(args.input_dir).resolve()
    output_file = Path(args.output_file).resolve()

    if not input_dir.exists():
        raise SystemExit(f"Input directory not found: {input_dir}")

    report = asyncio.run(run_pipeline(input_dir=input_dir, output_file=output_file, settings=settings))
    total = len(report.results)
    print(f"Processed {report.processed}/{total} files successfully")
    print(f"Failed: {report.failed}")
    print(f"Skipped: {report.skipped}")
    print(f"Output: {output_file}")
