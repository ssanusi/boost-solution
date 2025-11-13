"""Tests for attrs models demonstrating Boost's preferred validation approach."""

from __future__ import annotations

from datetime import datetime

import attrs
import pytest

from boost_exporter import ExportRecord, validate_and_convert_records


def test_export_record_creation() -> None:
    """Test creating ExportRecord with attrs validation."""
    record = ExportRecord(
        event_type="Receive",
        location_name="Warehouse",
        sku_name="Product ABC",
        quantity=10,
        value=1000,
        created_at=datetime(2024, 1, 15, 10, 30, 0)
    )

    assert record.event_type == "Receive"
    assert record.quantity == 10
    assert record.value == 1000


def test_export_record_immutability() -> None:
    """Test that ExportRecord is frozen (immutable)."""
    record = ExportRecord(
        event_type="Receive",
        location_name="Warehouse",
        sku_name="Product ABC",
        quantity=10,
        value=1000,
        created_at=datetime(2024, 1, 15, 10, 30, 0)
    )

    # Should raise AttributeError since frozen=True
    with pytest.raises(attrs.exceptions.FrozenInstanceError):
        record.quantity = 20


def test_export_record_validation() -> None:
    """Test that attrs validates field types."""
    # Invalid type for quantity (should be int/float, not str)
    with pytest.raises(TypeError):
        ExportRecord(
            event_type="Receive",
            location_name="Warehouse",
            sku_name="Product ABC",
            quantity="invalid",  # type: ignore[arg-type]
            value=1000,
            created_at=datetime(2024, 1, 15, 10, 30, 0)
        )


def test_export_record_to_dict() -> None:
    """Test converting ExportRecord to dictionary."""
    record = ExportRecord(
        event_type="Receive",
        location_name="Warehouse",
        sku_name="Product ABC",
        quantity=10,
        value=1000,
        created_at=datetime(2024, 1, 15, 10, 30, 0)
    )

    result = record.to_dict()
    assert isinstance(result, dict)
    assert result["event_type"] == "Receive"
    assert result["quantity"] == 10
    assert isinstance(result["created_at"], datetime)


def test_export_record_from_dict() -> None:
    """Test creating ExportRecord from dictionary."""
    data = {
        "event_type": "Receive",
        "location_name": "Warehouse",
        "sku_name": "Product ABC",
        "quantity": 10,
        "value": 1000,
        "created_at": datetime(2024, 1, 15, 10, 30, 0)
    }

    record = ExportRecord.from_dict(data)
    assert isinstance(record, ExportRecord)
    assert record.event_type == "Receive"
    assert record.quantity == 10


def test_validate_and_convert_records_strict() -> None:
    """Test conversion to ExportRecord objects."""
    data = [
        {
            "event_type": "Receive",
            "location_name": "Warehouse",
            "sku_name": "Product ABC",
            "quantity": 10,
            "value": 1000,
            "created_at": datetime(2024, 1, 15, 10, 30, 0)
        },
        {
            "event_type": "Ship",
            "location_name": "Store",
            "sku_name": "Product XYZ",
            "quantity": 5,
            "value": 500,
            "created_at": datetime(2024, 1, 16, 14, 0, 0)
        }
    ]

    records = validate_and_convert_records(data, strict=True)
    assert len(records) == 2
    assert all(isinstance(r, ExportRecord) for r in records)
    assert records[0].event_type == "Receive"
    assert records[1].event_type == "Ship"


def test_validate_and_convert_records_non_strict() -> None:
    """Test validation without conversion (backward compatible)."""
    data = [
        {
            "event_type": "Receive",
            "location_name": "Warehouse",
            "sku_name": "Product ABC",
            "quantity": 10,
            "value": 1000,
            "created_at": datetime(2024, 1, 15, 10, 30, 0)
        }
    ]

    result = validate_and_convert_records(data, strict=False)
    assert len(result) == 1
    assert isinstance(result, list)
    assert isinstance(result[0], dict)  # Still dicts, but validated
    assert result[0]["event_type"] == "Receive"


def test_validate_and_convert_records_invalid_data() -> None:
    """Test that validation raises errors for invalid data."""
    invalid_data = [
        {
            "event_type": "Receive",
            "location_name": "Warehouse",
            "sku_name": "Product ABC",
            "quantity": "invalid",  # Should be int/float
            "value": 1000,
            "created_at": datetime(2024, 1, 15, 10, 30, 0)
        }
    ]

    # Validation will raise TypeError from attrs validators
    with pytest.raises((TypeError, ValueError)):
        validate_and_convert_records(invalid_data, strict=True)

    # Non-strict mode also validates structure
    with pytest.raises((TypeError, ValueError)):
        validate_and_convert_records(invalid_data, strict=False)


def test_validate_and_convert_records_missing_fields() -> None:
    """Test validation with missing required fields."""
    incomplete_data = [
        {
            "event_type": "Receive",
            # Missing other required fields
        }
    ]

    # Validation will raise TypeError for missing required fields
    with pytest.raises((TypeError, KeyError, ValueError)):
        validate_and_convert_records(incomplete_data, strict=True)


def test_exporter_with_validation() -> None:
    """Test DataExporter with validation enabled."""
    from boost_exporter import DataExporter, ExportFormat

    valid_data = [
        {
            "event_type": "Receive",
            "location_name": "Warehouse",
            "sku_name": "Product ABC",
            "quantity": 10,
            "value": 1000,
            "created_at": datetime(2024, 1, 15, 10, 30, 0)
        }
    ]

    # Exporter with validation enabled
    exp = DataExporter(validate_input=True)
    result = exp.export(valid_data, ExportFormat.JSON)
    assert result is not None
    assert "Receive" in result


def test_exporter_with_validation_invalid() -> None:
    """Test DataExporter validation catches invalid data."""
    from boost_exporter import DataExporter, ExportFormat

    invalid_data = [
        {
            "event_type": "Receive",
            "location_name": "Warehouse",
            "sku_name": "Product ABC",
            "quantity": "invalid",  # Wrong type
            "value": 1000,
            "created_at": datetime(2024, 1, 15, 10, 30, 0)
        }
    ]

    exp = DataExporter(validate_input=True)
    # Validation will catch the invalid type
    with pytest.raises((TypeError, ValueError)):
        exp.export(invalid_data, ExportFormat.JSON)


def test_exporter_without_validation_backward_compatible() -> None:
    """Test that exporter without validation still works (backward compatible)."""
    from boost_exporter import DataExporter, ExportFormat

    # Any dict structure works when validation is disabled
    data = [
        {"any": "structure", "works": True, "number": 42}
    ]

    exp = DataExporter(validate_input=False)
    result = exp.export(data, ExportFormat.JSON)
    assert result is not None
    assert "any" in result

