from __future__ import annotations

import json
import shlex
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from .models import UploadItem


class BrowserAdapter(ABC):
    @abstractmethod
    def open_new_product_page(self) -> None:
        pass

    @abstractmethod
    def set_category(self, category_path: str) -> None:
        pass

    @abstractmethod
    def set_brand(self, brand_name: str) -> None:
        pass

    @abstractmethod
    def set_product_names(self, product_name: str, short_name: str) -> None:
        pass

    @abstractmethod
    def set_primary_spec(self, spec_name: str, spec_value: str, barcode: str) -> None:
        pass

    @abstractmethod
    def set_prices(self, price: float, original_price: float) -> None:
        pass

    @abstractmethod
    def upload_main_images(self, image_urls: list[str]) -> None:
        pass

    @abstractmethod
    def set_description(self, desc_text: str) -> None:
        pass

    @abstractmethod
    def save_draft(self) -> str:
        pass

    @abstractmethod
    def capture_screenshot(self, output_dir: Path, name: str) -> str:
        pass


class DryRunBrowserAdapter(BrowserAdapter):
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    def open_new_product_page(self) -> None:
        return

    def set_category(self, category_path: str) -> None:
        if not category_path:
            raise ValueError("category_path is empty")

    def set_brand(self, brand_name: str) -> None:
        if not brand_name:
            raise ValueError("brand_name is empty")

    def set_product_names(self, product_name: str, short_name: str) -> None:
        if not product_name:
            raise ValueError("product_name is empty")
        if len(short_name) > 15:
            raise ValueError("short_name too long")

    def set_primary_spec(self, spec_name: str, spec_value: str, barcode: str) -> None:
        if not spec_name or not spec_value or not barcode:
            raise ValueError("spec or barcode fields are invalid")

    def set_prices(self, price: float, original_price: float) -> None:
        if price < 0 or original_price < 0:
            raise ValueError("prices cannot be negative")

    def upload_main_images(self, image_urls: list[str]) -> None:
        if not image_urls:
            raise ValueError("no images provided")

    def set_description(self, desc_text: str) -> None:
        if not desc_text:
            raise ValueError("desc_text is empty")

    def save_draft(self) -> str:
        return "Draft saved (dry-run)"

    def capture_screenshot(self, output_dir: Path, name: str) -> str:
        output_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = output_dir / f"{name}.txt"
        screenshot_path.write_text("dry-run screenshot placeholder\n", encoding="utf-8")
        return str(screenshot_path)


class ShellActionBridge:
    """
    Execute MCP actions through an external command.

    Contract:
    1. Tool command is called as: <command> <action_name>
    2. JSON payload is sent via stdin
    3. Tool returns JSON on stdout
    """

    def __init__(self, command: str, timeout_sec: int = 30) -> None:
        self.command = command
        self.timeout_sec = timeout_sec

    def call(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        cmd = shlex.split(self.command)
        cmd.append(action)

        proc = subprocess.run(
            cmd,
            input=json.dumps(payload, ensure_ascii=False),
            text=True,
            capture_output=True,
            timeout=self.timeout_sec,
            check=False,
        )

        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()

        if proc.returncode != 0:
            raise RuntimeError(
                f"bridge action failed: action={action}, code={proc.returncode}, stderr={stderr}"
            )

        if not stdout:
            return {}

        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError:
            return {"raw_output": stdout}

        if isinstance(parsed, dict):
            return parsed
        return {"result": parsed}


class ChromeMCPBrowserAdapter(BrowserAdapter):
    def __init__(
        self,
        base_url: str,
        selector_map: dict,
        action_command: str,
        timeout_sec: int,
    ) -> None:
        self.base_url = base_url
        self.selector_map = selector_map
        self.bridge = ShellActionBridge(command=action_command, timeout_sec=timeout_sec)

    def _selector_payload(self, key: str) -> dict[str, Any]:
        node = (self.selector_map.get("selectors") or {}).get(key) or {}
        return {
            "primary": node.get("primary"),
            "fallback": node.get("fallback") or [],
        }

    def open_new_product_page(self) -> None:
        page_cfg = self.selector_map.get("page") or {}
        new_product_url = page_cfg.get("new_product_url") or f"{self.base_url}/app-seller/goods/create"
        self.bridge.call("open_new_product_page", {"url": new_product_url})

    def set_category(self, category_path: str) -> None:
        self.bridge.call(
            "set_category",
            {
                "category_path": category_path,
                "selector": self._selector_payload("category_input"),
            },
        )

    def set_brand(self, brand_name: str) -> None:
        self.bridge.call(
            "set_brand",
            {
                "brand_name": brand_name,
                "selector": self._selector_payload("brand_input"),
            },
        )

    def set_product_names(self, product_name: str, short_name: str) -> None:
        self.bridge.call(
            "set_product_names",
            {
                "product_name": product_name,
                "short_name": short_name,
                "selectors": {
                    "product_name": self._selector_payload("product_name_input"),
                    "short_name": self._selector_payload("short_name_input"),
                },
            },
        )

    def set_primary_spec(self, spec_name: str, spec_value: str, barcode: str) -> None:
        self.bridge.call(
            "set_primary_spec",
            {
                "spec_name_1": spec_name,
                "spec_value_1": spec_value,
                "barcode": barcode,
                "selectors": {
                    "spec_name": self._selector_payload("spec_name_input"),
                    "spec_value": self._selector_payload("spec_value_input"),
                    "barcode": self._selector_payload("barcode_input"),
                },
            },
        )

    def set_prices(self, price: float, original_price: float) -> None:
        self.bridge.call(
            "set_prices",
            {
                "price": price,
                "original_price": original_price,
                "selectors": {
                    "price": self._selector_payload("price_input"),
                    "original_price": self._selector_payload("original_price_input"),
                },
            },
        )

    def upload_main_images(self, image_urls: list[str]) -> None:
        self.bridge.call(
            "upload_main_images",
            {
                "image_urls": image_urls,
                "selector": self._selector_payload("image_upload"),
            },
        )

    def set_description(self, desc_text: str) -> None:
        self.bridge.call(
            "set_description",
            {
                "desc_text": desc_text,
                "selector": self._selector_payload("desc_textarea"),
            },
        )

    def save_draft(self) -> str:
        result = self.bridge.call(
            "save_draft",
            {
                "selector": self._selector_payload("save_draft_button"),
            },
        )
        return str(result.get("toast", "save_draft called"))

    def capture_screenshot(self, output_dir: Path, name: str) -> str:
        output_dir.mkdir(parents=True, exist_ok=True)
        result = self.bridge.call(
            "capture_screenshot",
            {
                "output_dir": str(output_dir),
                "name": name,
            },
        )
        path = result.get("path")
        if path:
            return str(path)

        fallback = output_dir / f"{name}.txt"
        fallback.write_text("screenshot path not returned by bridge\n", encoding="utf-8")
        return str(fallback)


def build_adapter(
    mode: str,
    base_url: str,
    selector_map: dict,
    action_command: str,
    timeout_sec: int,
) -> BrowserAdapter:
    if mode == "dry-run":
        return DryRunBrowserAdapter(base_url=base_url)
    if mode == "mcp":
        if not action_command:
            raise ValueError("mcp mode requires --mcp-action-cmd")
        return ChromeMCPBrowserAdapter(
            base_url=base_url,
            selector_map=selector_map,
            action_command=action_command,
            timeout_sec=timeout_sec,
        )
    raise ValueError(f"unsupported mode: {mode}")


def step_payload_from_item(item: UploadItem) -> dict:
    return {
        "external_id": item.external_id,
        "category_path": item.category_path,
        "brand_name": item.brand_name,
        "product_name": item.product_name,
    }
