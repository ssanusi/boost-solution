from __future__ import annotations

from enum import Enum


class ExportFormat(Enum):
    """Supported export formats."""

    CSV = "csv"
    JSON = "json"
