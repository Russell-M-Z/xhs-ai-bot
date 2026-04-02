from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class UploadItem:
    external_id: str
    product_name: str
    short_name: str
    brand_name: str
    category_path: str
    spec_name_1: str
    spec_value_1: str
    barcode: str
    price: float
    original_price: float
    main_images: list[str]
    desc_text: str
    row_number: int


@dataclass
class StepTrace:
    step_name: str
    status: str
    started_at: str
    finished_at: str
    duration_ms: int
    screenshot_path: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class TaskResult:
    task_id: str
    external_id: str
    status: str
    started_at: str
    finished_at: str
    duration_ms: int
    steps: list[StepTrace] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class BatchReport:
    run_id: str
    mode: str
    started_at: str
    finished_at: str
    duration_ms: int
    report_path: str
    total_rows: int
    total_tasks: int
    success_tasks: int
    failed_tasks: int
    paused: bool
    pause_reason: str | None
    skipped_items: list[str]
    runtime_config: dict[str, Any]
    auto_debug: dict[str, Any]
    validation_errors: list[dict[str, Any]]
    tasks: list[TaskResult]


def utc_now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"
