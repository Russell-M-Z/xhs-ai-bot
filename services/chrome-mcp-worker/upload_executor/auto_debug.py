from __future__ import annotations

import json
import subprocess
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import BatchReport, utc_now_iso


@dataclass
class AutoDebugConfig:
    enabled: bool
    workspace_root: Path
    timeout_sec: int = 1200
    command_override: str = ""


def _should_trigger(report: BatchReport) -> bool:
    return bool(report.failed_tasks > 0 or report.validation_errors or report.paused)


def _tail(value: str, max_chars: int = 4000) -> str:
    if len(value) <= max_chars:
        return value
    return value[-max_chars:]


def _build_incident_payload(report: BatchReport) -> dict[str, Any]:
    failed_tasks = [task for task in report.tasks if task.status == "FAILED"]

    return {
        "timestamp": utc_now_iso(),
        "run_id": report.run_id,
        "mode": report.mode,
        "report_path": report.report_path,
        "failed_tasks": report.failed_tasks,
        "success_tasks": report.success_tasks,
        "paused": report.paused,
        "pause_reason": report.pause_reason,
        "skipped_items": report.skipped_items,
        "validation_errors": report.validation_errors,
        "failed_task_samples": [
            {
                "task_id": task.task_id,
                "external_id": task.external_id,
                "errors": task.errors,
                "last_step": task.steps[-1].step_name if task.steps else None,
            }
            for task in failed_tasks[:5]
        ],
        "runtime_config": report.runtime_config,
    }


def _default_codex_prompt(incident_path: Path) -> str:
    return textwrap.dedent(
        f"""
        你是 xhs-ai-bot 的自动故障修复代理。

        请读取故障上下文文件：{incident_path}

        任务要求：
        1. 先定位根因（字段校验、选择器、执行逻辑、桥接命令、重试/熔断策略）。
        2. 在当前工作区内直接实施修复。
        3. 修复后执行必要验证（最少运行一次上传执行器命令）。
        4. 输出：根因、修改文件、验证结果、后续风险。
        """
    ).strip()


def _run_codex_default(
    incident_path: Path,
    workspace_root: Path,
    timeout_sec: int,
    output_dir: Path,
) -> tuple[int | None, str, str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    last_message_path = output_dir / "codex_last_message.txt"

    cmd = [
        "codex",
        "exec",
        "--dangerously-bypass-approvals-and-sandbox",
        "--skip-git-repo-check",
        "--cd",
        str(workspace_root),
        "-o",
        str(last_message_path),
        _default_codex_prompt(incident_path),
    ]

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        check=False,
    )

    return proc.returncode, proc.stdout or "", proc.stderr or "", " ".join(cmd)


def _run_command_override(
    command_override: str,
    incident_path: Path,
    workspace_root: Path,
    timeout_sec: int,
) -> tuple[int | None, str, str, str]:
    command = command_override
    command = command.replace("{incident_path}", str(incident_path))
    command = command.replace("{workspace_root}", str(workspace_root))

    proc = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        check=False,
    )

    return proc.returncode, proc.stdout or "", proc.stderr or "", command


def trigger_auto_debug(
    report: BatchReport,
    run_output_dir: Path,
    config: AutoDebugConfig,
) -> dict[str, Any]:
    if not config.enabled:
        return {"triggered": False, "status": "disabled"}

    if not _should_trigger(report):
        return {"triggered": False, "status": "no_failure"}

    incidents_dir = run_output_dir / "incidents"
    incidents_dir.mkdir(parents=True, exist_ok=True)

    incident_path = incidents_dir / f"{report.run_id}.json"
    incident_payload = _build_incident_payload(report)
    incident_path.write_text(json.dumps(incident_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    try:
        if config.command_override:
            code, stdout, stderr, command = _run_command_override(
                command_override=config.command_override,
                incident_path=incident_path,
                workspace_root=config.workspace_root,
                timeout_sec=config.timeout_sec,
            )
        else:
            code, stdout, stderr, command = _run_codex_default(
                incident_path=incident_path,
                workspace_root=config.workspace_root,
                timeout_sec=config.timeout_sec,
                output_dir=incidents_dir,
            )

        status = "success" if code == 0 else "failed"
        return {
            "triggered": True,
            "status": status,
            "incident_path": str(incident_path),
            "command": command,
            "exit_code": code,
            "stdout_tail": _tail(stdout),
            "stderr_tail": _tail(stderr),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "triggered": True,
            "status": "timeout",
            "incident_path": str(incident_path),
            "error": str(exc),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "triggered": True,
            "status": "error",
            "incident_path": str(incident_path),
            "error": str(exc),
        }
