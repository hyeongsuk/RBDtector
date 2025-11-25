"""Compute Sleep Atonia Index (SAI) from RBDtector summary spreadsheets.

This script reads one or more ``RBDtector_results_*.xlsx`` files produced by the
RBDtector pipeline, extracts the REM epoch counts and Chin EMG activity metrics,
and derives the Sleep Atonia Index as described by Ferri et al. (2010).

The tool intentionally avoids heavy third-party dependencies (e.g. pandas) so it
can run inside restricted environments. Excel files are parsed through the OOXML
structure using the standard library.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from xml.etree import ElementTree as ET
from zipfile import ZipFile

NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
SHEET_PATH = "xl/worksheets/sheet1.xml"
SHARED_STRINGS_PATH = "xl/sharedStrings.xml"
DEFAULT_RESULTS_DIR = (Path(__file__).resolve().parent / "../RBDtector/tests/data/RBDtector output").resolve()

EXPECTED_KEYS = {
    "Global_REM_MiniEpochs_WO-Artifacts",
    "Global_REM_MacroEpochs_WO-Artifacts",
    "Chin_tonic_Abs",
    "Chin_any_Abs",
    "Subject ID",
}


@dataclass
class SaiMetrics:
    """Container for SAI-relevant values extracted from a workbook."""

    source: Path
    subject_id: str
    mini_total: float
    macro_total: float
    chin_tonic_abs: float
    chin_any_abs: float

    @property
    def mini_atonia(self) -> float:
        return self.mini_total - self.chin_any_abs

    @property
    def macro_atonia(self) -> float:
        return self.macro_total - self.chin_tonic_abs

    @property
    def sai_fraction(self) -> Optional[float]:
        denominator = self.mini_total + self.macro_total
        if denominator == 0:
            return None
        return (self.mini_atonia + self.macro_atonia) / denominator

    def as_csv_row(self) -> Dict[str, Optional[float]]:
        return {
            "source_file": str(self.source),
            "subject_id": self.subject_id,
            "global_rem_mini_epochs_wo_artifacts": self.mini_total,
            "global_rem_macro_epochs_wo_artifacts": self.macro_total,
            "chin_tonic_abs": self.chin_tonic_abs,
            "chin_any_abs": self.chin_any_abs,
            "mini_atonia": self.mini_atonia,
            "macro_atonia": self.macro_atonia,
            "sai_fraction": self.sai_fraction,
            "sai_percent": None if self.sai_fraction is None else self.sai_fraction * 100,
        }


class WorkbookParsingError(RuntimeError):
    """Raised when an expected structure is missing from the workbook."""


def iter_cells(row) -> Iterable[ET.Element]:  # type: ignore[override]
    for cell in row.findall("a:c", NS):
        yield cell


def column_ref(cell_ref: str) -> str:
    """Return the column letters from a cell reference (e.g. ``AZ12`` -> ``AZ``)."""

    letters = []
    for ch in cell_ref:
        if ch.isalpha():
            letters.append(ch)
        else:
            break
    return "".join(letters)


def read_shared_strings(zf: ZipFile) -> List[str]:
    try:
        data = zf.read(SHARED_STRINGS_PATH)
    except KeyError:
        return []
    root = ET.fromstring(data)
    strings: List[str] = []
    for si in root.findall("a:si", NS):
        text_parts = []
        for node in si.findall('.//a:t', NS):
            text_parts.append(node.text or "")
        strings.append("".join(text_parts))
    return strings


def cell_value(cell: ET.Element, shared: List[str]) -> Optional[float | str]:
    cell_type = cell.get("t")
    if cell_type == "inlineStr":
        text_node = cell.find("a:is/a:t", NS)
        return "" if text_node is None else text_node.text or ""
    if cell_type == "s":
        index_node = cell.find("a:v", NS)
        if index_node is None or index_node.text is None:
            return ""
        try:
            idx = int(index_node.text)
        except ValueError as exc:  # unexpected, treat as empty string
            raise WorkbookParsingError(f"Invalid shared string index: {index_node.text}") from exc
        return shared[idx] if 0 <= idx < len(shared) else ""
    value_node = cell.find("a:v", NS)
    if value_node is None or value_node.text is None:
        return None
    raw = value_node.text
    try:
        return float(raw)
    except ValueError:
        return raw


def parse_rows(sheet_xml: bytes, shared: List[str]) -> Dict[int, Dict[str, Optional[float | str]]]:
    root = ET.fromstring(sheet_xml)
    sheet_data = root.find("a:sheetData", NS)
    if sheet_data is None:
        raise WorkbookParsingError("Missing sheetData block in worksheet")

    rows: Dict[int, Dict[str, Optional[float | str]]] = {}
    for row in sheet_data.findall("a:row", NS):
        raw_index = row.get("r")
        if raw_index is None:
            continue
        try:
            idx = int(raw_index)
        except ValueError:
            continue
        entries: Dict[str, Optional[float | str]] = {}
        for cell in iter_cells(row):
            ref = cell.get("r")
            if ref is None:
                continue
            col = column_ref(ref)
            entries[col] = cell_value(cell, shared)
        rows[idx] = entries
    return rows


def extract_metrics_from_rows(rows: Dict[int, Dict[str, Optional[float | str]]]) -> SaiMetrics:
    header_row_index: Optional[int] = None
    headers: Dict[str, str] = {}
    for index in sorted(rows):
        values = rows[index]
        header_matches = {col: val for col, val in values.items() if isinstance(val, str)}
        if any(str(val).strip() == "Subject ID" for val in header_matches.values()):
            header_row_index = index
            headers = {col: str(val).strip() for col, val in header_matches.items() if isinstance(val, str)}
            break
    if header_row_index is None:
        raise WorkbookParsingError("Could not locate header row containing 'Subject ID'.")

    missing_keys = EXPECTED_KEYS.difference(headers.values())
    if missing_keys:
        raise WorkbookParsingError(f"Header row missing expected labels: {sorted(missing_keys)}")

    name_to_col = {label: col for col, label in headers.items()}
    subject_col = name_to_col["Subject ID"]

    data_row: Optional[Dict[str, Optional[float | str]]] = None
    for index in sorted(rows):
        if index <= header_row_index:
            continue
        row_values = rows[index]
        subject_value = row_values.get(subject_col)
        if subject_value in (None, ""):
            continue
        data_row = row_values
        break
    if data_row is None:
        raise WorkbookParsingError("No data row found after header row.")

    def grab(label: str) -> float:
        col = name_to_col[label]
        value = data_row.get(col)
        if not isinstance(value, (int, float)):
            if value is None or value == "":
                raise WorkbookParsingError(f"Value for '{label}' is missing in data row.")
            try:
                return float(value)
            except ValueError as exc:
                raise WorkbookParsingError(f"Value for '{label}' is not numeric: {value}") from exc
        return float(value)

    subject_raw = data_row.get(subject_col)
    subject_id = str(subject_raw) if subject_raw is not None else "Unknown"

    metrics = SaiMetrics(
        source=Path(""),  # placeholder; filled by caller
        subject_id=subject_id.strip(),
        mini_total=grab("Global_REM_MiniEpochs_WO-Artifacts"),
        macro_total=grab("Global_REM_MacroEpochs_WO-Artifacts"),
        chin_tonic_abs=grab("Chin_tonic_Abs"),
        chin_any_abs=grab("Chin_any_Abs"),
    )
    return metrics


def parse_workbook(path: Path) -> SaiMetrics:
    with ZipFile(path) as zf:
        shared_strings = read_shared_strings(zf)
        try:
            sheet_xml = zf.read(SHEET_PATH)
        except KeyError as exc:
            raise WorkbookParsingError(f"Worksheet '{SHEET_PATH}' not found in {path}") from exc
    rows = parse_rows(sheet_xml, shared_strings)
    metrics = extract_metrics_from_rows(rows)
    metrics.source = path
    return metrics


def collect_workbooks(path: Path) -> List[Path]:
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise FileNotFoundError(f"Input path does not exist: {path}")
    return sorted(
        file for file in path.rglob("RBDtector_results_*.xlsx") if file.is_file()
    )


def write_results(rows: List[SaiMetrics], output_dir: Path) -> Path:
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"sai_results_{timestamp}.csv"

    with output_path.open("w", newline="", encoding="utf-8") as fp:
        fieldnames = list(rows[0].as_csv_row().keys()) if rows else [
            "source_file",
            "subject_id",
            "global_rem_mini_epochs_wo_artifacts",
            "global_rem_macro_epochs_wo_artifacts",
            "chin_tonic_abs",
            "chin_any_abs",
            "mini_atonia",
            "macro_atonia",
            "sai_fraction",
            "sai_percent",
        ]
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for metrics in rows:
            writer.writerow(metrics.as_csv_row())
    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compute Sleep Atonia Index values from one or more RBDtector results\n"
            "Pass a single file or a directory that will be searched recursively."
        )
    )
    parser.add_argument(
        "input_path",
        nargs="?",
        type=Path,
        default=None,
        help=(
            "Path to an RBDtector results file or a directory containing them. "
            "If omitted, defaults to the latest outputs under tests/data/RBDtector output."
        ),
    )
    default_output = (Path(__file__).resolve().parent / "../SAI_pseudo_results").resolve()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=default_output,
        help=(
            "Directory where the aggregated CSV will be written (default: ../SAI_pseudo_results "
            "relative to this script)."
        ),
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-file console output; only print the summary path.",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    input_path = args.input_path
    if input_path is None:
        input_path = DEFAULT_RESULTS_DIR
    input_path = input_path.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()

    try:
        workbook_paths = collect_workbooks(input_path)
    except Exception as exc:
        parser.error(str(exc))
        return 2

    if not workbook_paths:
        parser.error(f"No files matching 'RBDtector_results_*.xlsx' found under {input_path}")
        return 2

    results: List[SaiMetrics] = []
    errors: List[str] = []

    for workbook in workbook_paths:
        try:
            metrics = parse_workbook(workbook)
            results.append(metrics)
            if not args.quiet:
                fraction = metrics.sai_fraction
                percent = "n/a" if fraction is None else f"{fraction * 100:.2f}%"
                print(f"{workbook}: SAI={percent} (subject={metrics.subject_id})")
        except WorkbookParsingError as exc:
            errors.append(f"{workbook}: {exc}")
        except Exception as exc:  # unexpected errors bubble up separately
            errors.append(f"{workbook}: unexpected error {exc}")

    if not results:
        for line in errors:
            print(line, file=sys.stderr)
        parser.error("Failed to compute SAI for any input file.")
        return 2

    output_path = write_results(results, output_dir)
    if not args.quiet:
        print(f"\nWrote aggregated results to: {output_path}")

    if errors:
        print("\nEncountered issues while processing some files:", file=sys.stderr)
        for line in errors:
            print(f"  - {line}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
