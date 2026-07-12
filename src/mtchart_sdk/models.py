from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class AuditOperation:
    operator_id: str
    action: str
    tab: str = ""
    details: str = ""
    occurred_at: datetime | str | None = None
    id: int | None = None


@dataclass(frozen=True)
class PartItem:
    name: str = ""
    pn: str = ""
    sn: str = ""
    qty: int = 1
    project: str = ""


@dataclass(frozen=True)
class PenConfig:
    id: str
    name: str = ""
    stabilization_target: float | None = None
    low_limit: float | None = None
    high_limit: float | None = None
    tolerance: float = 0.5


@dataclass(frozen=True)
class ProcessInput:
    report_number: str
    project: str
    process_name: str
    oven: str
    relief_hours: float
    pen: PenConfig
    items: list[PartItem | dict[str, Any]] = field(default_factory=list)
    started_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProcessRecord:
    report_number: str
    project: str
    process_name: str
    oven: str
    relief_hours: float
    pen: PenConfig
    items: list[PartItem]
    started_at: datetime
    expected_exit_at: datetime
    total_quantity: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReadingEvaluation:
    value: float | None
    status: str
    is_numeric: bool
    is_within_limits: bool
    is_low_temperature: bool
    can_start_process: bool
    remaining_seconds: float
