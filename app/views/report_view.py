from __future__ import annotations

import math
from pathlib import Path

import pandas as pd


def write_markdown(path: Path, content: str) -> None:
    path.write_text(content.strip() + "\n", encoding="utf-8")


def markdown_table(df: pd.DataFrame, max_rows: int = 20) -> str:
    if df.empty:
        return "_Sin datos._"
    view = df.head(max_rows).copy()
    headers = list(view.columns)
    rows = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in view.iterrows():
        values = [format_markdown_value(row[col]) for col in headers]
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join(rows)


def format_markdown_value(value: object) -> str:
    if isinstance(value, float):
        if math.isnan(value):
            return ""
        return f"{value:.5g}"
    return str(value).replace("|", "/")
