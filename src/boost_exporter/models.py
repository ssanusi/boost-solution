from __future__ import annotations

from datetime import datetime
from typing import Any, Union

import attrs


# Custom validators for business logic
def validate_positive(instance: Any, attribute: attrs.Attribute, value: Union[int, float]) -> None:
    """Validate that a numeric value is positive (> 0)."""
    if value <= 0:
        raise ValueError(f"{attribute.name} must be positive, got {value}")


def validate_non_negative(instance: Any, attribute: attrs.Attribute, value: Union[int, float]) -> None:
    """Validate that a numeric value is non-negative (>= 0)."""
    if value < 0:
        raise ValueError(f"{attribute.name} must be non-negative, got {value}")


def validate_event_type(instance: Any, attribute: attrs.Attribute, value: str) -> None:
    """Validate that event_type is one of the allowed values."""
    allowed_types = {"Receive", "Ship", "Adjust", "Transfer", "Return"}
    if value not in allowed_types:
        raise ValueError(
            f"{attribute.name} must be one of {allowed_types}, got '{value}'"
        )


# Converters for automatic type conversion
def convert_to_numeric(value: Any) -> Union[int, float]:
    """Convert value to int or float, handling string inputs."""
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        # Try int first, then float
        try:
            if "." in value or "e" in value.lower():
                return float(value)
            return int(value)
        except ValueError:
            raise TypeError(f"Cannot convert '{value}' to numeric type")
    raise TypeError(f"Cannot convert {type(value).__name__} to numeric type")


def convert_to_datetime(value: Any) -> datetime:
    """Convert value to datetime, handling string inputs in ISO format."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            # Try parsing ISO format datetime string
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            raise ValueError(f"Cannot parse datetime from string: '{value}'")
    raise TypeError(f"Cannot convert {type(value).__name__} to datetime")


@attrs.define(
    frozen=True,
    slots=True,
    repr=True,
    eq=True,
    order=False,  # Can be enabled if ordering is needed
)
class ExportRecord:
    """Structured data model for export records using attrs.

    This class demonstrates attrs' philosophy: "concise and correct software
    without slowing down your code." With just a decorator and field definitions,
    attrs automatically generates:
    - __init__() with validation and type conversion
    - __repr__() for readable string representation
    - __eq__() for equality comparison
    - __hash__() (via frozen=True) for use in sets/dicts

    All without writing a single dunder method! This eliminates ~50+ lines of
    boilerplate while maintaining performance (slots=True) and safety (frozen=True).

    This enhanced implementation demonstrates advanced attrs features:
    - Runtime validation with custom business logic validators
    - Automatic type conversion using converters
    - Type safety with instance validators
    - Immutability (frozen=True) - ensures data integrity
    - Better performance (slots=True) - reduces memory overhead
    - Field metadata for documentation and processing hints
    - Support for string-to-type conversion (flexible input handling)

    Example:
        >>> record = ExportRecord(
        ...     event_type="Receive",
        ...     location_name="Warehouse",
        ...     sku_name="Product ABC",
        ...     quantity=10,
        ...     value=1000,
        ...     created_at=datetime.now()
        ... )
        >>> # Also works with string inputs (automatic conversion)
        >>> record2 = ExportRecord.from_dict({
        ...     "event_type": "Ship",
        ...     "location_name": "Store",
        ...     "sku_name": "Product XYZ",
        ...     "quantity": "5",  # String converted to int
        ...     "value": "500.50",  # String converted to float
        ...     "created_at": "2024-01-15T10:30:00"  # String converted to datetime
        ... })
    """
    event_type: str = attrs.field(
        validator=validate_event_type,
        metadata={
            "description": "Type of inventory event",
            "allowed_values": ["Receive", "Ship", "Adjust", "Transfer", "Return"],
        },
    )
    location_name: str = attrs.field(
        validator=attrs.validators.instance_of(str),
        metadata={"description": "Name of the warehouse or location"},
    )
    sku_name: str = attrs.field(
        validator=attrs.validators.instance_of(str),
        metadata={"description": "Stock Keeping Unit name"},
    )
    quantity: Union[int, float] = attrs.field(
        converter=convert_to_numeric,
        validator=[
            attrs.validators.instance_of((int, float)),
            validate_positive,
        ],
        metadata={
            "description": "Quantity of items (must be positive)",
            "unit": "items",
        },
    )
    value: Union[int, float] = attrs.field(
        converter=convert_to_numeric,
        validator=[
            attrs.validators.instance_of((int, float)),
            validate_non_negative,
        ],
        metadata={
            "description": "Monetary value (must be non-negative)",
            "unit": "currency",
        },
    )
    created_at: datetime = attrs.field(
        converter=convert_to_datetime,
        validator=attrs.validators.instance_of(datetime),
        metadata={"description": "Timestamp when the event was created"},
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for export compatibility.

        Uses attrs.asdict() which respects field metadata and handles
        nested structures properly.
        """
        return attrs.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExportRecord:
        """Create from dictionary with validation and automatic type conversion.

        This method leverages attrs converters to automatically convert
        string inputs to appropriate types (e.g., "10" -> 10, "2024-01-15T10:30:00" -> datetime).

        Args:
            data: Dictionary with record data. Supports both native types and strings
                  that will be automatically converted.

        Returns:
            Validated ExportRecord instance.

        Raises:
            TypeError: If type conversion fails
            ValueError: If validation fails (e.g., invalid event_type, negative quantity)

        Example:
            >>> record = ExportRecord.from_dict({
            ...     "event_type": "Receive",
            ...     "location_name": "Warehouse",
            ...     "sku_name": "Product ABC",
            ...     "quantity": "10",  # String will be converted to int
            ...     "value": 1000,
            ...     "created_at": "2024-01-15T10:30:00"  # String will be converted to datetime
            ... })
        """
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

