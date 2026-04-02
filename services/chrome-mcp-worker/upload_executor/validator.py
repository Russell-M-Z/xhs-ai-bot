from __future__ import annotations

from typing import Any

from .models import UploadItem

REQUIRED_FIELDS = [
    "external_id",
    "product_name",
    "short_name",
    "brand_name",
    "category_path",
    "spec_name_1",
    "spec_value_1",
    "barcode",
    "price",
    "original_price",
    "main_images",
    "desc_text",
]


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _parse_price(field_name: str, value: str, errors: list[str]) -> float:
    try:
        parsed = float(value)
    except ValueError:
        errors.append(f"{field_name} is not a valid number")
        return 0.0
    if parsed < 0:
        errors.append(f"{field_name} must be >= 0")
    return parsed


def parse_main_images(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def validate_row(row: dict[str, Any], row_number: int) -> tuple[UploadItem | None, list[str]]:
    errors: list[str] = []

    for field in REQUIRED_FIELDS:
        if not _clean(row.get(field)):
            errors.append(f"{field} is required")

    if errors:
        return None, errors

    price = _parse_price("price", _clean(row["price"]), errors)
    original_price = _parse_price("original_price", _clean(row["original_price"]), errors)

    if original_price and price and original_price < price:
        errors.append("original_price should be >= price")

    short_name = _clean(row["short_name"])
    if len(short_name) > 15:
        errors.append("short_name should be <= 15 characters")

    main_images = parse_main_images(_clean(row["main_images"]))
    if not main_images:
        errors.append("main_images should include at least one URL")

    if errors:
        return None, errors

    item = UploadItem(
        external_id=_clean(row["external_id"]),
        product_name=_clean(row["product_name"]),
        short_name=short_name,
        brand_name=_clean(row["brand_name"]),
        category_path=_clean(row["category_path"]),
        spec_name_1=_clean(row["spec_name_1"]),
        spec_value_1=_clean(row["spec_value_1"]),
        barcode=_clean(row["barcode"]),
        price=price,
        original_price=original_price,
        main_images=main_images,
        desc_text=_clean(row["desc_text"]),
        row_number=row_number,
    )
    return item, []
