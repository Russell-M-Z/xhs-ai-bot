from __future__ import annotations

import csv
import json
import random
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from .mcp_adapter import BrowserAdapter, step_payload_from_item
from .models import BatchReport, StepTrace, TaskResult, UploadItem, utc_now_iso
from .validator import validate_row


def _duration_ms(start_ts: float, end_ts: float) -> int:
    return int((end_ts - start_ts) * 1000)


@dataclass
class RunConfig:
    step_retries: int = 1
    step_retry_backoff_ms: int = 800
    max_consecutive_failures: int = 3
    item_delay_min_ms: int = 3000
    item_delay_max_ms: int = 8000
    random_seed: int | None = None


def persist_report(report: BatchReport) -> None:
    report_path = Path(report.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2), encoding="utf-8")


class UploadExecutor:
    def __init__(
        self,
        adapter: BrowserAdapter,
        output_dir: Path,
        run_config: RunConfig,
    ) -> None:
        self.adapter = adapter
        self.output_dir = output_dir
        self.run_config = run_config

    def _run_step(
        self,
        task_id: str,
        step_name: str,
        fn: Callable[[], dict],
    ) -> StepTrace:
        started_at = utc_now_iso()
        start_time = time.time()
        attempts = self.run_config.step_retries + 1

        for attempt in range(1, attempts + 1):
            try:
                details = fn() or {}
                details["attempt"] = attempt

                screenshot_path = self.adapter.capture_screenshot(
                    self.output_dir / "artifacts" / task_id,
                    step_name,
                )
                end_time = time.time()
                return StepTrace(
                    step_name=step_name,
                    status="SUCCESS",
                    started_at=started_at,
                    finished_at=utc_now_iso(),
                    duration_ms=_duration_ms(start_time, end_time),
                    screenshot_path=screenshot_path,
                    details=details,
                )
            except Exception as exc:  # noqa: BLE001
                if attempt < attempts:
                    time.sleep(max(0, self.run_config.step_retry_backoff_ms) / 1000)
                    continue

                end_time = time.time()
                return StepTrace(
                    step_name=step_name,
                    status="FAILED",
                    started_at=started_at,
                    finished_at=utc_now_iso(),
                    duration_ms=_duration_ms(start_time, end_time),
                    details={"attempts": attempt},
                    error=str(exc),
                )

        end_time = time.time()
        return StepTrace(
            step_name=step_name,
            status="FAILED",
            started_at=started_at,
            finished_at=utc_now_iso(),
            duration_ms=_duration_ms(start_time, end_time),
            details={"attempts": attempts},
            error="unknown step failure",
        )

    def execute_item(self, item: UploadItem) -> TaskResult:
        task_id = f"upload-{item.external_id}-{uuid.uuid4().hex[:8]}"
        task_start = time.time()
        task_started_at = utc_now_iso()
        steps: list[StepTrace] = []

        task_payload = step_payload_from_item(item)

        plan: list[tuple[str, Callable[[], dict]]] = [
            ("open_new_product_page", lambda: self.adapter.open_new_product_page() or task_payload),
            ("set_category", lambda: self.adapter.set_category(item.category_path) or {"category_path": item.category_path}),
            ("set_brand", lambda: self.adapter.set_brand(item.brand_name) or {"brand_name": item.brand_name}),
            (
                "set_product_names",
                lambda: self.adapter.set_product_names(item.product_name, item.short_name)
                or {"product_name": item.product_name, "short_name": item.short_name},
            ),
            (
                "set_primary_spec",
                lambda: self.adapter.set_primary_spec(item.spec_name_1, item.spec_value_1, item.barcode)
                or {
                    "spec_name_1": item.spec_name_1,
                    "spec_value_1": item.spec_value_1,
                    "barcode": item.barcode,
                },
            ),
            (
                "set_prices",
                lambda: self.adapter.set_prices(item.price, item.original_price)
                or {"price": item.price, "original_price": item.original_price},
            ),
            (
                "upload_main_images",
                lambda: self.adapter.upload_main_images(item.main_images)
                or {"image_count": len(item.main_images)},
            ),
            (
                "set_description",
                lambda: self.adapter.set_description(item.desc_text)
                or {"desc_length": len(item.desc_text)},
            ),
            (
                "save_draft",
                lambda: {"toast": self.adapter.save_draft()},
            ),
        ]

        status = "SUCCESS"
        errors: list[str] = []

        for step_name, action in plan:
            trace = self._run_step(task_id=task_id, step_name=step_name, fn=action)
            steps.append(trace)
            if trace.status == "FAILED":
                status = "FAILED"
                errors.append(f"{step_name}: {trace.error}")
                break

        task_end = time.time()
        return TaskResult(
            task_id=task_id,
            external_id=item.external_id,
            status=status,
            started_at=task_started_at,
            finished_at=utc_now_iso(),
            duration_ms=_duration_ms(task_start, task_end),
            steps=steps,
            errors=errors,
        )


def load_selector_map(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_items_from_csv(csv_path: Path) -> tuple[list[UploadItem], list[dict]]:
    items: list[UploadItem] = []
    validation_errors: list[dict] = []

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for index, row in enumerate(reader, start=2):
            item, errors = validate_row(row, row_number=index)
            if errors:
                validation_errors.append(
                    {
                        "row_number": index,
                        "external_id": row.get("external_id", ""),
                        "errors": errors,
                    }
                )
                continue
            assert item is not None
            items.append(item)

    return items, validation_errors


def run_batch(
    mode: str,
    adapter: BrowserAdapter,
    items: list[UploadItem],
    validation_errors: list[dict],
    output_dir: Path,
    run_config: RunConfig,
) -> BatchReport:
    if run_config.random_seed is not None:
        random.seed(run_config.random_seed)

    run_start_ts = time.time()
    started_at = utc_now_iso()
    run_id = f"run-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"

    executor = UploadExecutor(adapter=adapter, output_dir=output_dir, run_config=run_config)

    task_results: list[TaskResult] = []
    paused = False
    pause_reason: str | None = None
    skipped_items: list[str] = []
    consecutive_failures = 0

    for index, item in enumerate(items):
        result = executor.execute_item(item)
        task_results.append(result)

        if result.status == "FAILED":
            consecutive_failures += 1
        else:
            consecutive_failures = 0

        if (
            run_config.max_consecutive_failures > 0
            and consecutive_failures >= run_config.max_consecutive_failures
        ):
            paused = True
            pause_reason = (
                "consecutive failures reached threshold: "
                f"{consecutive_failures}/{run_config.max_consecutive_failures}"
            )
            skipped_items = [remaining.external_id for remaining in items[index + 1 :]]
            break

        is_last = index == len(items) - 1
        if not is_last and run_config.item_delay_max_ms > 0:
            min_delay = max(0, run_config.item_delay_min_ms)
            max_delay = max(min_delay, run_config.item_delay_max_ms)
            delay_ms = random.randint(min_delay, max_delay)
            time.sleep(delay_ms / 1000)

    success_tasks = sum(1 for task in task_results if task.status == "SUCCESS")
    failed_tasks = sum(1 for task in task_results if task.status == "FAILED")
    run_end_ts = time.time()

    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"{run_id}.json"

    report = BatchReport(
        run_id=run_id,
        mode=mode,
        started_at=started_at,
        finished_at=utc_now_iso(),
        duration_ms=_duration_ms(run_start_ts, run_end_ts),
        report_path=str(report_path),
        total_rows=len(items) + len(validation_errors),
        total_tasks=len(task_results),
        success_tasks=success_tasks,
        failed_tasks=failed_tasks,
        paused=paused,
        pause_reason=pause_reason,
        skipped_items=skipped_items,
        runtime_config=asdict(run_config),
        auto_debug={},
        validation_errors=validation_errors,
        tasks=task_results,
    )

    persist_report(report)

    return report
