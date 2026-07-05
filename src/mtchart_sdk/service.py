from __future__ import annotations

from datetime import datetime
from pathlib import Path

from mtchart_sdk.models import PartItem, ProcessInput, ProcessRecord, ReadingEvaluation
from mtchart_sdk.output_paths import OutputPaths, build_output_paths
from mtchart_sdk.reports import parts_control_path, report_summary
from mtchart_sdk.rules import calculate_exit_timing, evaluate_temperature, normalize_item, total_quantity
from mtchart_sdk.storage import PartsCatalogStorage, SQLitePartsCatalog


class MTChartService:
    def __init__(
        self,
        catalog_db: str | Path | None = None,
        catalog: PartsCatalogStorage | None = None,
    ) -> None:
        if catalog is not None and catalog_db is not None:
            raise ValueError("Use catalog or catalog_db, not both")
        self.catalog = catalog or SQLitePartsCatalog(catalog_db or "mtchart_sdk.db")

    def create_process(self, data: ProcessInput) -> ProcessRecord:
        started_at = data.started_at or datetime.now()
        items = [normalize_item(item) for item in data.items]
        for item in items:
            if item.name and item.pn:
                self.catalog.save(item.name, item.pn)
        expected_exit_at, _remaining = calculate_exit_timing(started_at, data.relief_hours, started_at)
        return ProcessRecord(
            report_number=data.report_number,
            project=data.project,
            process_name=data.process_name,
            oven=data.oven,
            relief_hours=float(data.relief_hours or 0),
            pen=data.pen,
            items=items,
            started_at=started_at,
            expected_exit_at=expected_exit_at,
            total_quantity=total_quantity(items),
            metadata=dict(data.metadata or {}),
        )

    def evaluate_reading(
        self,
        process: ProcessRecord,
        value: float | str | None,
        now: datetime | None = None,
    ) -> ReadingEvaluation:
        return evaluate_temperature(
            value=value,
            pen=process.pen,
            started_at=process.started_at,
            relief_hours=process.relief_hours,
            now=now,
        )

    def search_parts(self, term: str = "", limit: int = 100) -> list[dict[str, object]]:
        return self.catalog.search(term, limit)

    def build_output_paths(
        self,
        root: str | Path,
        reference_date: datetime | None = None,
        *,
        oven: str | None = None,
        lang: str = "PT",
    ) -> OutputPaths:
        return build_output_paths(root, reference_date, oven=oven, lang=lang)

    def parts_control_path(
        self,
        root: str | Path,
        process: ProcessRecord,
        reference_date: datetime | None = None,
        *,
        lang: str = "PT",
        prefix: str = "Controle_Pecas",
    ) -> Path:
        return parts_control_path(
            root,
            process.report_number,
            reference_date or process.started_at,
            oven=process.oven,
            lang=lang,
            prefix=prefix,
        )

    def report_summary(self, process: ProcessRecord) -> dict[str, object]:
        summary = report_summary(process.items)
        return {
            **summary,
            "report_number": process.report_number,
            "project": process.project,
            "oven": process.oven,
            "expected_exit_at": process.expected_exit_at,
        }
