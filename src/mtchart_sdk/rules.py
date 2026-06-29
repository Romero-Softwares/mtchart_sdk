from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any

from mtchart_sdk.models import PartItem, PenConfig, ReadingEvaluation


def to_float_or_none(value: Any) -> float | None:
    try:
        if value in ("", None):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def clean_identifier(value: Any) -> str:
    text = str(value or "").strip()
    return re.sub(r"^\s*(PN|P/N|LOTE|BATCH)\s*:\s*", "", text, flags=re.IGNORECASE).strip()


def normalize_item(item: PartItem | dict[str, Any] | str) -> PartItem:
    if isinstance(item, PartItem):
        return item
    if isinstance(item, dict):
        try:
            qty = max(1, int(str(item.get("qty", 1)).strip() or "1"))
        except (TypeError, ValueError):
            qty = 1
        return PartItem(
            name=str(item.get("name", item.get("nome", ""))).strip(),
            pn=clean_identifier(item.get("pn", "")),
            sn=str(item.get("sn", "")).strip(),
            qty=qty,
            project=str(item.get("project", item.get("projeto", ""))).strip(),
        )
    return PartItem(sn=str(item or "").strip())


def total_quantity(items: list[PartItem | dict[str, Any] | str]) -> int:
    return sum(normalize_item(item).qty for item in items or [])


def calculate_exit_timing(started_at: datetime, relief_hours: float, now: datetime | None = None) -> tuple[datetime, float]:
    now = now or datetime.now()
    expected_exit_at = started_at + timedelta(hours=float(relief_hours or 0))
    return expected_exit_at, (expected_exit_at - now).total_seconds()


def evaluate_temperature(
    value: Any,
    pen: PenConfig,
    started_at: datetime,
    relief_hours: float,
    now: datetime | None = None,
) -> ReadingEvaluation:
    numeric_value = to_float_or_none(value)
    expected_exit_at, remaining_seconds = calculate_exit_timing(started_at, relief_hours, now)
    del expected_exit_at

    if numeric_value is None:
        return ReadingEvaluation(
            value=None,
            status="N/A",
            is_numeric=False,
            is_within_limits=False,
            is_low_temperature=False,
            can_start_process=False,
            remaining_seconds=remaining_seconds,
        )

    low_limit = pen.low_limit
    high_limit = pen.high_limit
    has_low = low_limit is not None
    has_high = high_limit is not None
    is_low = has_low and numeric_value < float(low_limit)
    is_high = has_high and numeric_value > float(high_limit)
    is_within = not is_low and not is_high
    target = pen.stabilization_target
    can_start = target is not None and numeric_value >= float(target) - float(pen.tolerance)

    if is_low:
        status = "LOW"
    elif is_high:
        status = "HIGH"
    elif is_within:
        status = "OK"
    else:
        status = "UNKNOWN"

    return ReadingEvaluation(
        value=numeric_value,
        status=status,
        is_numeric=True,
        is_within_limits=is_within,
        is_low_temperature=is_low,
        can_start_process=can_start,
        remaining_seconds=remaining_seconds,
    )
