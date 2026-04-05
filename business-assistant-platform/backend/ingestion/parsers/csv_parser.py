"""
File: backend/ingestion/parsers/csv_parser.py
Purpose: CSV parser with basic cleaning, profiling, and text rendering for chunking.
"""

import io
import json

import pandas as pd

from backend.ingestion.parsers.base import ParsedDocument


def _normalize_column_name(column_name: str) -> str:
    """
    Convert arbitrary column names into stable snake_case style identifiers.
    """
    return (
        column_name.strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
    )


def parse_csv(file_bytes: bytes) -> ParsedDocument:
    """
    Parse CSV bytes into a normalized tabular representation.
    """
    dataframe = pd.read_csv(io.BytesIO(file_bytes))
    dataframe.columns = [_normalize_column_name(str(col)) for col in dataframe.columns]

    # Remove duplicated records and rows that are entirely empty.
    dataframe = dataframe.drop_duplicates().dropna(how="all")

    # Normalize string cells by trimming whitespace.
    for column_name in dataframe.select_dtypes(include=["object"]).columns:
        dataframe[column_name] = dataframe[column_name].astype("string").str.strip()

    profile = {
        "row_count": int(len(dataframe)),
        "column_count": int(len(dataframe.columns)),
        "columns": list(dataframe.columns),
        "dtypes": {col: str(dtype) for col, dtype in dataframe.dtypes.items()},
        "null_counts": {
            column_name: int(dataframe[column_name].isna().sum())
            for column_name in dataframe.columns
        },
    }

    # Keep the preview bounded so response payloads remain manageable.
    preview_records = json.loads(
        dataframe.head(50).to_json(orient="records", date_format="iso")
    )

    # Render rows into natural-language-friendly text used for chunk generation.
    rendered_rows: list[str] = []
    for _, row in dataframe.head(500).iterrows():
        fields = []
        for column_name in dataframe.columns:
            value = row[column_name]
            if pd.notna(value):
                fields.append(f"{column_name}: {value}")
        if fields:
            rendered_rows.append("; ".join(fields))

    rendered_text = "\n".join(rendered_rows)

    return ParsedDocument(
        document_type="csv",
        text=rendered_text,
        metadata=profile,
        tabular_preview=preview_records,
    )

