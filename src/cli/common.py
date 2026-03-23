"""Shared CLI formatting and parsing helpers."""

from __future__ import annotations

import json
from typing import Any, Callable, Iterable


TextFormatter = Callable[[Any], None]


def emit_output(payload: Any, output: str, text_formatter: TextFormatter | None = None) -> None:
    if output == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    if text_formatter is not None:
        text_formatter(payload)
        return

    if isinstance(payload, list):
        print_collection(payload, output="text")
        return

    print(json.dumps(payload, ensure_ascii=False))


def print_collection(items: list[dict[str, Any]], output: str) -> None:
    if output == "json":
        print(json.dumps(items, ensure_ascii=False, indent=2))
        return

    if not items:
        print("No records found")
        return

    for item in items:
        print(json.dumps(item, ensure_ascii=False))


def parse_csv_ints(raw_value: str | None) -> list[int]:
    if not raw_value:
        return []

    values: list[int] = []
    for chunk in raw_value.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        values.append(int(chunk))
    return values


def dedupe_preserve_order(values: Iterable[int]) -> list[int]:
    seen: set[int] = set()
    ordered: list[int] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise ValueError("value must be >= 1")
    return parsed
