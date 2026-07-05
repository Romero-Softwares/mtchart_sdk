from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


MONTH_NAMES = {
    "PT": [
        "JANEIRO",
        "FEVEREIRO",
        "MARCO",
        "ABRIL",
        "MAIO",
        "JUNHO",
        "JULHO",
        "AGOSTO",
        "SETEMBRO",
        "OUTUBRO",
        "NOVEMBRO",
        "DEZEMBRO",
    ],
    "EN": [
        "JANUARY",
        "FEBRUARY",
        "MARCH",
        "APRIL",
        "MAY",
        "JUNE",
        "JULY",
        "AUGUST",
        "SEPTEMBER",
        "OCTOBER",
        "NOVEMBER",
        "DECEMBER",
    ],
}


@dataclass(frozen=True)
class OutputFolderNames:
    logs: str = "LOGS"
    entry_control: str = "CONTROLE DE ENTRADAS"
    pdf_reports: str = "RELATORIOS PDF"
    charts: str = "GRAFICOS HISTORICOS"


@dataclass(frozen=True)
class OutputPaths:
    root: Path
    period: Path
    logs: Path
    entry_control: Path
    pdf_reports: Path
    charts: Path


def sanitize_path_part(value: object, replacement: str = "") -> str:
    return re.sub(r'[\\/*?:"<>|]', replacement, str(value or "")).strip(replacement + " ")


def month_folder_name(reference_date: datetime, lang: str = "PT") -> str:
    names = MONTH_NAMES.get(str(lang or "PT").upper(), MONTH_NAMES["PT"])
    return sanitize_path_part(names[reference_date.month - 1]).upper()


def period_folder(root: str | Path, reference_date: datetime | None = None, lang: str = "PT") -> Path:
    reference_date = reference_date or datetime.now()
    return Path(root) / reference_date.strftime("%Y") / month_folder_name(reference_date, lang)


def build_output_paths(
    root: str | Path,
    reference_date: datetime | None = None,
    *,
    oven: str | None = None,
    lang: str = "PT",
    names: OutputFolderNames | None = None,
) -> OutputPaths:
    names = names or OutputFolderNames()
    period = period_folder(root, reference_date, lang)
    subfolder = sanitize_path_part(oven).upper()

    def child(folder_name: str) -> Path:
        path = period / sanitize_path_part(folder_name).upper()
        return path / subfolder if subfolder else path

    pdf_reports = child(names.pdf_reports)
    return OutputPaths(
        root=Path(root),
        period=period,
        logs=child(names.logs),
        entry_control=child(names.entry_control),
        pdf_reports=pdf_reports,
        charts=pdf_reports / sanitize_path_part(names.charts).upper(),
    )
