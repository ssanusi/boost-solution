from __future__ import annotations

from datetime import datetime
from typing import Any, Union

import attrs


@attrs.define(frozen=True, slots=True)
class ExportRecord:
    """Structured data model for export records using attrs.

    This provides:
    - Runtime validation
    - Type safety
    - Immutability (frozen=True)
    - Better performance (slots=True)
    - Clear field documentation

    Example:
        >>> record = ExportRecord(
        ...     event_type="Receive",
        ...     location_name="Warehouse",
        ...     sku_name="Product ABC",
        ...     quantity=10,
        ...     value=1000,
        ...     created_at=datetime.now()
        ... )
    """
    event_type: str = attrs.field(validator=attrs.validators.instance_of(str))
    location_name: str = attrs.field(validator=attrs.validators.instance_of(str))
    sku_name: str = attrs.field(validator=attrs.validators.instance_of(str))
    quantity: Union[int, float] = attrs.field(validator=attrs.validators.instance_of((int, float)))
    value: Union[int, float] = attrs.field(validator=attrs.validators.instance_of((int, float)))
    created_at: datetime = attrs.field(validator=attrs.validators.instance_of(datetime))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for export compatibility."""
        return attrs.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExportRecord:
        """Create from dictionary with validation."""
        return cls(**data)


def validate_and_convert_records(
    data: list[dict[str, Any]],
    strict: bool = False
) -> list[dict[str, Any]] | list[ExportRecord]:
    """Validate and optionally convert records using attrs.

    This demonstrates using attrs for structured data validation and conversion,
    which is a common pattern in Boost codebases.

    For strict mode, we manually convert to ExportRecord objects to handle Union types
    properly.

    Args:
        data: List of dictionaries to validate/convert
        strict: If True, convert to ExportRecord objects. If False, validate but return dicts.

    Returns:
        Validated data (either dicts or ExportRecord objects)

    Raises:
        TypeError: If validation fails (from attrs validators)
        ValueError: If data structure is invalid

    Example:
        >>> records = validate_and_convert_records(raw_data, strict=True)
        >>> # Now you have validated ExportRecord objects
    """
    if strict:
        # Convert to structured ExportRecord objects using attrs directly
        # This provides better control and handles Union types correctly
        try:
            return [ExportRecord.from_dict(item) for item in data]
        except (TypeError, KeyError) as e:
            raise ValueError(f"Failed to convert to ExportRecord: {e}") from e
    else:
        # Validate structure by attempting to create ExportRecord objects
        # but return original dicts (backward compatible)
        try:
            for item in data:
                # Validate by creating (but not storing) ExportRecord
                ExportRecord.from_dict(item)
            return data
        except (TypeError, KeyError) as e:
            raise ValueError(f"Validation failed: {e}") from e

