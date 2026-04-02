from __future__ import annotations

import argparse
from pathlib import Path

from .auto_debug import AutoDebugConfig, trigger_auto_debug
from .executor import RunConfig, load_items_from_csv, load_selector_map, persist_report, run_batch
from .mcp_adapter import build_adapter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MCP product upload executor")
    parser.add_argument(
        "--input",
        required=True,
        help="Path to upload CSV file",
    )
    parser.add_argument(
        "--selector-map",
        default="configs/selector-map.example.json",
        help="Path to selector map JSON",
    )
    parser.add_argument(
        "--output-dir",
        default="runs",
        help="Directory for reports and artifacts",
    )
    parser.add_argument(
        "--mode",
        choices=["dry-run", "mcp"],
        default="dry-run",
        help="dry-run for structure validation, mcp for real browser execution",
    )
    parser.add_argument(
        "--base-url",
        default="https://ark.xiaohongshu.com",
        help="Seller backend base URL",
    )
    parser.add_argument(
        "--mcp-action-cmd",
        default="",
        help="Command used as MCP action bridge, e.g. 'python3 tools/mock_mcp_action_bridge.py'",
    )
    parser.add_argument(
        "--mcp-timeout-sec",
        type=int,
        default=30,
        help="Timeout for each MCP action call",
    )
    parser.add_argument(
        "--step-retries",
        type=int,
        default=1,
        help="Retry count per step after first attempt",
    )
    parser.add_argument(
        "--step-retry-backoff-ms",
        type=int,
        default=800,
        help="Backoff milliseconds between step retries",
    )
    parser.add_argument(
        "--max-consecutive-failures",
        type=int,
        default=3,
        help="Pause batch when this threshold is reached",
    )
    parser.add_argument(
        "--item-delay-min-ms",
        type=int,
        default=3000,
        help="Minimum delay between item tasks",
    )
    parser.add_argument(
        "--item-delay-max-ms",
        type=int,
        default=8000,
        help="Maximum delay between item tasks",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=None,
        help="Optional random seed for deterministic delay",
    )
    parser.add_argument(
        "--auto-debug-on-failure",
        action="store_true",
        help="Automatically invoke Codex to troubleshoot and fix when batch has failures",
    )
    parser.add_argument(
        "--auto-debug-timeout-sec",
        type=int,
        default=1200,
        help="Timeout for auto-debug codex invocation",
    )
    parser.add_argument(
        "--auto-debug-cmd",
        default="",
        help=(
            "Optional override command for auto-debug. Supports placeholders: "
            "{incident_path}, {workspace_root}"
        ),
    )
    parser.add_argument(
        "--workspace-root",
        default=str(Path(__file__).resolve().parents[3]),
        help="Workspace root for auto-debug codex execution",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    input_path = Path(args.input)
    selector_map_path = Path(args.selector_map)
    output_dir = Path(args.output_dir)

    if not input_path.exists():
        print(f"[ERROR] input file not found: {input_path}")
        return 1

    selector_map = load_selector_map(selector_map_path)

    adapter = build_adapter(
        mode=args.mode,
        base_url=args.base_url,
        selector_map=selector_map,
        action_command=args.mcp_action_cmd,
        timeout_sec=max(1, args.mcp_timeout_sec),
    )

    run_config = RunConfig(
        step_retries=max(0, args.step_retries),
        step_retry_backoff_ms=max(0, args.step_retry_backoff_ms),
        max_consecutive_failures=max(0, args.max_consecutive_failures),
        item_delay_min_ms=max(0, args.item_delay_min_ms),
        item_delay_max_ms=max(0, args.item_delay_max_ms),
        random_seed=args.random_seed,
    )

    items, validation_errors = load_items_from_csv(input_path)
    report = run_batch(
        mode=args.mode,
        adapter=adapter,
        items=items,
        validation_errors=validation_errors,
        output_dir=output_dir,
        run_config=run_config,
    )

    auto_debug_result = trigger_auto_debug(
        report=report,
        run_output_dir=output_dir,
        config=AutoDebugConfig(
            enabled=args.auto_debug_on_failure,
            workspace_root=Path(args.workspace_root),
            timeout_sec=max(60, args.auto_debug_timeout_sec),
            command_override=args.auto_debug_cmd,
        ),
    )
    report.auto_debug = auto_debug_result
    persist_report(report)

    print("[INFO] upload batch finished")
    print(f"[INFO] mode={report.mode}")
    print(f"[INFO] total_rows={report.total_rows}")
    print(f"[INFO] total_tasks={report.total_tasks}")
    print(f"[INFO] success_tasks={report.success_tasks}")
    print(f"[INFO] failed_tasks={report.failed_tasks}")
    print(f"[INFO] paused={report.paused}")
    print(f"[INFO] skipped_items={len(report.skipped_items)}")
    print(f"[INFO] validation_errors={len(report.validation_errors)}")
    print(f"[INFO] auto_debug_status={report.auto_debug.get('status')}")
    if report.auto_debug.get("triggered"):
        print(f"[INFO] auto_debug_incident={report.auto_debug.get('incident_path')}")
    print(f"[INFO] report_id={report.run_id}")
    print(f"[INFO] report_path={report.report_path}")

    if report.failed_tasks > 0 or report.validation_errors:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
