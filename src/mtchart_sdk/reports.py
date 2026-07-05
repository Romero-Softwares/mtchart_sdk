from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from mtchart_sdk.models import PartItem
from mtchart_sdk.output_paths import build_output_paths, sanitize_path_part
from mtchart_sdk.rules import clean_identifier, normalize_item, total_quantity


@dataclass(frozen=True)
class ReportIdentity:
    report_number: str
    pn: str = ""
    sn: str = ""
    oven: str = ""
    project: str = ""

    @property
    def safe_report_number(self) -> str:
        return format_report_number(self.report_number) or "SEM_RELATORIO"


@dataclass(frozen=True)
class TemperatureLogPoint:
    timestamp: datetime
    value: float
    pen: str = ""


def format_report_number(value: object) -> str:
    return str(value or "").strip().replace("/", "-")


def is_batch_identifier(value: object, batch_label: str = "LOTE") -> bool:
    text = str(value or "").strip().upper()
    label = str(batch_label or "LOTE").upper()
    return text.startswith(("LOTE", "BATCH", label))


def serial_display_for_mass(sn: object, items_mass: str | Iterable[object] | None = None, multiple_label: str = "MULTIPLO") -> str:
    text = str(sn or "").strip()
    if text != multiple_label:
        return text
    if not items_mass:
        return ""
    try:
        items = json.loads(items_mass) if isinstance(items_mass, str) else items_mass
    except (TypeError, ValueError):
        return text
    for item in items or []:
        if isinstance(item, dict) and str(item.get("sn", "")).strip():
            return text
        if not isinstance(item, dict) and str(item).strip():
            return text
    return ""


def format_datetime_display(value: datetime | str | None, lang: str = "PT") -> str:
    if not value:
        return "-"
    if isinstance(value, datetime):
        date_value = value
    else:
        text = str(value).split(".")[0]
        try:
            date_value = datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return text
    date_format = "%Y/%m/%d %H:%M:%S" if str(lang).upper() == "EN" else "%d/%m/%Y %H:%M:%S"
    return date_value.strftime(date_format)


def temperature_status(value: object, low_limit: object, high_limit: object) -> tuple[str, bool]:
    try:
        numeric_value = float(value)
        low = float(low_limit)
        high = float(high_limit)
    except (TypeError, ValueError):
        return "N/A", False
    if low <= numeric_value <= high:
        return "NORMAL / CONFORME", True
    return "ANORMAL / FORA DO PADRAO", False


def temperature_log_filename(identity: ReportIdentity, batch_label: str = "LOTE") -> str:
    pn = clean_identifier(identity.pn)
    sn = "" if is_batch_identifier(identity.pn, batch_label) else identity.sn
    parts = [
        "Log",
        sanitize_path_part(identity.safe_report_number, "-"),
        sanitize_path_part(pn),
        sanitize_path_part(sn),
    ]
    return "_".join(part for part in parts if part) + ".xlsx"


def parts_control_filename(prefix: str = "Controle_Pecas", report_number: object = None, reference_date: datetime | None = None) -> str:
    reference_date = reference_date or datetime.now()
    safe_prefix = sanitize_path_part(prefix) or "Controle_Pecas"
    safe_report = sanitize_path_part(format_report_number(report_number), "-") or "SEM_RELATORIO"
    return f"{safe_prefix}_{safe_report}_{reference_date:%Y-%m-%d}.xlsx"


def parts_control_path(
    root: str | Path,
    report_number: object = None,
    reference_date: datetime | None = None,
    *,
    oven: str | None = None,
    lang: str = "PT",
    prefix: str = "Controle_Pecas",
) -> Path:
    paths = build_output_paths(root, reference_date, oven=oven, lang=lang)
    return paths.entry_control / parts_control_filename(prefix, report_number, reference_date)


def normalize_report_items(items: list[PartItem | dict[str, object] | str]) -> list[PartItem]:
    return [normalize_item(item) for item in items or []]


def report_summary(items: list[PartItem | dict[str, object] | str]) -> dict[str, object]:
    normalized = normalize_report_items(items)
    return {
        "items": normalized,
        "total_quantity": total_quantity(normalized),
        "has_multiple_items": len(normalized) > 1 or any(item.qty > 1 for item in normalized),
    }
