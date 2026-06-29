from __future__ import annotations

from datetime import datetime
from pathlib import Path

from mtchart_sdk.models import PartItem, ProcessInput, ProcessRecord, ReadingEvaluation
from mtchart_sdk.rules import calculate_exit_timing, evaluate_temperature, normalize_item, total_quantity
from mtchart_sdk.storage import PartsCatalog


class MTChartService:
    def __init__(self, catalog_db: str | Path | None = None) -> None:
        self.catalog = PartsCatalog(catalog_db or "mtchart_sdk.db")

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
