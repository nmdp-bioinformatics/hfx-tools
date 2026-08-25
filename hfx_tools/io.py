from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .util import safe_relpath


def read_hfx_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_hfx_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=False)
        f.write("\n")


def parse_frequency_location(freq_loc: str) -> tuple[str, str | None]:
    """
    Returns (kind, value)
      - ("inline", None)
      - ("file", relative_path) for file://...
      - ("http", uri) for http(s)://... (not bundled in MVP)
    """
    if freq_loc == "inline":
        return ("inline", None)

    u = urlparse(freq_loc)
    if u.scheme in ("http", "https"):
        return ("http", freq_loc)
    if u.scheme == "file":
        # file://data/f.csv -> path = "data/f.csv"
        # urlparse gives netloc + path; handle both
        raw = (u.netloc + u.path).lstrip("/")
        return ("file", safe_relpath(raw))

    # allow plain relative path as a convenience (not strictly per schema format=uri)
    return ("file", safe_relpath(freq_loc))


def _resolve_header_mapping(hfx_obj: dict[str, Any]) -> dict[str, str]:
    """Return {original_col: canonical_col} from metadata.frequencyFileHeader.

    The schema defines frequencyFileHeader as an object mapping CSV header
    names to expected field names (e.g. {"Haplo": "haplotype", "Freq": "frequency"}).
    """
    return hfx_obj.get("metadata", {}).get("frequencyFileHeader", {})


def load_frequency_rows(hfx_path: Path, hfx_obj: dict[str, Any]) -> list[tuple[str, float]]:
    md = hfx_obj.get("metadata", {})
    freq_loc = md.get("frequencyLocation")
    if not freq_loc:
        raise ValueError("metadata.frequencyLocation is required")

    kind, val = parse_frequency_location(freq_loc)
    header_map = _resolve_header_mapping(hfx_obj)

    if kind == "inline":
        rows = hfx_obj.get("frequencyData")
        if rows is None:
            raise ValueError("frequencyLocation is 'inline' but top-level frequencyData is missing")
        out = []
        for r in rows:
            out.append((r["haplotype"], float(r["frequency"])))
        return out

    if kind == "http":
        raise ValueError(
            "http(s) frequencyLocation not supported in MVP loader; "
            "please download locally or bundle with file://"
        )

    # file
    rel = val
    assert rel is not None
    # Resolve relative to parent of metadata/ if inside build folder structure
    base = hfx_path.parent
    if base.name == "metadata":
        base = base.parent
    freq_file = (base / rel).resolve()
    if not freq_file.exists():
        raise FileNotFoundError(f"Referenced frequency file not found: {freq_file}")

    if freq_file.suffix.lower() == ".csv":
        return load_csv(freq_file, header_map=header_map)
    if freq_file.suffix.lower() == ".parquet":
        return load_parquet(freq_file, header_map=header_map)

    raise ValueError(f"Unsupported frequency file type: {freq_file.suffix}")


def _apply_header_map(fieldnames: list, header_map: dict[str, str]) -> dict[str, str]:
    """Build a reverse lookup: {original_col: canonical_col} for the columns we need."""
    # header_map is {csv_col: canonical_col}, e.g. {"Haplo": "haplotype"}
    reverse: dict[str, str] = {}
    for orig, canon in header_map.items():
        if orig in fieldnames:
            reverse[orig] = canon
    return reverse


def load_csv(path: Path, header_map: dict[str, str] | None = None) -> list[tuple[str, float]]:
    out: list[tuple[str, float]] = []
    header_map = header_map or {}
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        mapping = _apply_header_map(reader.fieldnames or [], header_map)
        # Determine which column names to use for haplotype and frequency
        haplo_col = "haplotype"
        freq_col = "frequency"
        for orig, canon in mapping.items():
            if canon == "haplotype":
                haplo_col = orig
            elif canon == "frequency":
                freq_col = orig
        if haplo_col not in reader.fieldnames or freq_col not in reader.fieldnames:
            raise ValueError(
                f"CSV must have columns haplotype,frequency (or mapped via frequencyFileHeader); "
                f"found {reader.fieldnames}"
            )
        for row in reader:
            out.append((row[haplo_col], float(row[freq_col])))
    return out


def load_parquet(path: Path, header_map: dict[str, str] | None = None) -> list[tuple[str, float]]:
    try:
        import pandas as pd  # type: ignore
    except Exception as e:
        raise ImportError(
            "Parquet support requires pandas + pyarrow. "
            "Install with: pip install 'hfx-tools[parquet]'"
        ) from e

    header_map = header_map or {}
    df = pd.read_parquet(path)
    # Apply header mapping: rename columns to canonical names
    rename = {orig: canon for orig, canon in header_map.items() if orig in df.columns}
    if rename:
        df = df.rename(columns=rename)
    if "haplotype" not in df.columns or "frequency" not in df.columns:
        raise ValueError(
            f"Parquet must have columns haplotype,frequency (or mapped via frequencyFileHeader); "
            f"found {list(df.columns)}"
        )
    return [(str(h), float(f)) for h, f in zip(df["haplotype"], df["frequency"], strict=True)]
