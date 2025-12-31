#!/usr/bin/env python3
"""Continue medium-scale structuring without re-crawling.

This script is designed for the common workflow:
- `medium_scale_crawler.py` crawled + filtered results (e.g. 354)
- Structured extraction was capped (e.g. max_items=80)

It will:
- Load the latest (or specified) `academic_data/medium_scale_results_*.json`
- Load the matching (or specified) `academic_data/structured/medium_scale_structured_*.json`
- Extract structured records for remaining URLs only (resume)
- Write a full structured JSON and a flattened JSONL table

Notes:
- Uses the project's Ollama client (streaming) so WSL2 -> Windows Ollama works reliably.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# Match project import style used by crawlers
ROOT = Path(__file__).resolve().parent
sys.path.append(str(ROOT / "src"))

from analysis.enhanced_llm_analyzer import LLMConfig, OllamaClient  # noqa: E402

import medium_scale_crawler as m  # noqa: E402


@dataclass
class Inputs:
    results_file: Path
    structured_file: Path


def _pick_latest(pattern: str) -> Path:
    candidates = sorted(Path(".").glob(pattern))
    if not candidates:
        raise FileNotFoundError(f"No files match: {pattern}")
    return candidates[-1]


def _load_results(results_file: Path) -> List[Dict[str, Any]]:
    obj = json.loads(results_file.read_text(encoding="utf-8"))
    results = obj.get("filtered_results") or obj.get("results") or []
    if not isinstance(results, list):
        raise ValueError(f"Unexpected results format in {results_file}")
    return results


def _load_structured(structured_file: Path) -> List[Dict[str, Any]]:
    if not structured_file.exists():
        return []
    data = json.loads(structured_file.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Unexpected structured format in {structured_file}")
    return data


def _url_set(records: List[Dict[str, Any]]) -> Set[str]:
    urls: Set[str] = set()
    for rec in records:
        url = rec.get("url") or rec.get("source_url")
        if isinstance(url, str) and url.strip():
            urls.add(url.strip())
    return urls


def _flatten_and_write_jsonl(records: List[Dict[str, Any]], jsonl_path: Path) -> None:
    rows = m.flatten_for_analysis(records)
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with jsonl_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _default_outputs_for(structured_file: Path) -> Tuple[Path, Path]:
    # Keep original file untouched and write new “full” files.
    suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
    full_structured = structured_file.with_name(structured_file.stem + f"_full_{suffix}" + structured_file.suffix)
    analysis_jsonl = structured_file.parent / (structured_file.stem.replace("structured", "analysis") + f"_full_{suffix}.jsonl")
    return full_structured, analysis_jsonl


def _resolve_inputs(args: argparse.Namespace) -> Inputs:
    if args.results_file:
        results_file = Path(args.results_file)
    else:
        results_file = _pick_latest("academic_data/medium_scale_results_*.json")

    if args.structured_file:
        structured_file = Path(args.structured_file)
    else:
        # Best effort: pick the most recent structured file.
        structured_file = _pick_latest("academic_data/structured/medium_scale_structured_*.json")

    return Inputs(results_file=results_file, structured_file=structured_file)


def main() -> int:
    parser = argparse.ArgumentParser(description="Resume medium-scale structuring and fill remaining records.")
    parser.add_argument("--results-file", help="Path to academic_data/medium_scale_results_*.json")
    parser.add_argument("--structured-file", help="Path to academic_data/structured/medium_scale_structured_*.json")
    parser.add_argument("--max-new", type=int, default=10_000, help="Max number of NEW items to structure")
    parser.add_argument("--write-every", type=int, default=25, help="Checkpoint write interval (new items)")
    args = parser.parse_args()

    inputs = _resolve_inputs(args)
    print(f"RESULTS_FILE: {inputs.results_file}")
    print(f"STRUCTURED_FILE: {inputs.structured_file}")

    results = _load_results(inputs.results_file)
    existing = _load_structured(inputs.structured_file)

    existing_urls = _url_set(existing)
    remaining = [r for r in results if (r.get("url") or "").strip() and (r.get("url") or "").strip() not in existing_urls]

    print(f"TOTAL_FILTERED_RESULTS: {len(results)}")
    print(f"EXISTING_STRUCTURED: {len(existing)}")
    print(f"REMAINING_TO_STRUCT: {len(remaining)}")

    if not remaining:
        print("Nothing to do.")
        return 0

    llm_config = LLMConfig()
    ollama_client = OllamaClient(base_url=llm_config.ollama_base_url, model=llm_config.ollama_model)
    if not ollama_client.is_available():
        print("ERROR: Ollama is not available (check OLLAMA_BASE_URL/port).")
        return 2

    # Extract new records
    new_records: List[Dict[str, Any]] = []
    max_new = min(args.max_new, len(remaining))
    start = time.time()

    for i in range(0, max_new):
        item = remaining[i]
        batch = m.extract_structured_signals([item], ollama_client, max_items=1)
        if batch:
            new_records.append(batch[0])

        if (i + 1) % args.write_every == 0:
            elapsed = time.time() - start
            rate = (i + 1) / max(elapsed, 1e-6)
            print(f"progress: {i+1}/{max_new} new, {rate:.2f} items/s")

    elapsed = time.time() - start
    print(f"DONE_NEW: {len(new_records)} in {elapsed:.1f}s")

    combined = existing + new_records
    # Write new full outputs
    full_structured_path, analysis_jsonl_path = _default_outputs_for(inputs.structured_file)
    with full_structured_path.open("w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)

    _flatten_and_write_jsonl(combined, analysis_jsonl_path)

    print(f"WROTE_STRUCTURED: {full_structured_path} ({len(combined)})")
    print(f"WROTE_ANALYSIS_JSONL: {analysis_jsonl_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
