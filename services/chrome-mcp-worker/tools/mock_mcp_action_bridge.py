#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


def _read_payload() -> dict:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    parsed = json.loads(raw)
    if isinstance(parsed, dict):
        return parsed
    return {"payload": parsed}


def _write_json(data: dict) -> None:
    sys.stdout.write(json.dumps(data, ensure_ascii=False))


def _capture_screenshot(payload: dict) -> dict:
    output_dir = Path(payload.get("output_dir", "."))
    name = str(payload.get("name", "step"))
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{name}.txt"
    path.write_text("mock mcp screenshot placeholder\n", encoding="utf-8")
    return {"path": str(path)}


def main() -> int:
    if len(sys.argv) < 2:
        sys.stderr.write("missing action name\n")
        return 2

    action = sys.argv[1]
    payload = _read_payload()

    if action == "save_draft":
        _write_json({"toast": "保存草稿成功(mock)"})
        return 0

    if action == "capture_screenshot":
        _write_json(_capture_screenshot(payload))
        return 0

    _write_json(
        {
            "ok": True,
            "action": action,
            "received": payload,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
