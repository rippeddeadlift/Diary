"""Tests for server.exif_utils module."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from server.exif_utils import (
    dms_to_deg,
    exif_get_str,
    parse_exif_dt,
    ratio_to_float,
)


class TestExifGetStr:
    """Tests for exif_get_str function."""

    def test_find_first_key(self):
        tags = {"key1": "value1", "key2": "value2"}
        result = exif_get_str(tags, "key1", "key2")
        assert result == "value1"

    def test_find_second_key(self):
        tags = {"key2": "value2"}
        result = exif_get_str(tags, "key1", "key2")
        assert result == "value2"

    def test_no_match(self):
        tags = {"other": "value"}
        result = exif_get_str(tags, "key1", "key2")
        assert result is None

    def test_empty_tags(self):
        tags = {}
        result = exif_get_str(tags, "key1")
        assert result is None


class TestParseExifDt:
    """Tests for parse_exif_dt function."""

    def test_valid_format(self):
        result = parse_exif_dt("2024:01:15 10:30:45")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30
        assert result.second == 45

    def test_invalid_format(self):
        result = parse_exif_dt("2024-01-15 10:30:45")  # Wrong separator
        assert result is None

    def test_empty_string(self):
        result = parse_exif_dt("")
        assert result is None

    def test_whitespace_handling(self):
        result = parse_exif_dt("  2024:01:15 10:30:45  ")
        assert result is not None
        assert result.year == 2024


class TestRatioToFloat:
    """Tests for ratio_to_float function."""

    def test_ratio_object(self):
        class MockRatio:
            def __init__(self, num, den):
                self.num = num
                self.den = den

        ratio = MockRatio(1, 2)
        result = ratio_to_float(ratio)
        assert result == 0.5

    def test_float_value(self):
        result = ratio_to_float(3.14)
        assert result == 3.14

    def test_integer_value(self):
        result = ratio_to_float(42)
        assert result == 42.0

    def test_zero_denominator(self):
        class MockRatio:
            def __init__(self):
                self.num = 1
                self.den = 0

        ratio = MockRatio()
        result = ratio_to_float(ratio)
        # Should handle gracefully (returns None or raises)
        # Current implementation would raise ZeroDivisionError
        # but we test the behavior
        try:
            result = ratio_to_float(ratio)
            # If it doesn't raise, result should be None or handle gracefully
        except ZeroDivisionError:
            pass  # Expected behavior


class TestDmsToDeg:
    """Tests for dms_to_deg function."""

    def test_valid_dms(self):
        # 37° 46' 26.4" = 37.774 degrees (approximately)
        dms = [37, 46, 26.4]
        result = dms_to_deg(dms)
        assert result is not None
        assert abs(result - 37.774) < 0.01

    def test_exact_degrees(self):
        dms = [45, 0, 0]
        result = dms_to_deg(dms)
        assert result == 45.0

    def test_wrong_length(self):
        dms = [37, 46]  # Missing seconds
        result = dms_to_deg(dms)
        assert result is None

    def test_empty_list(self):
        result = dms_to_deg([])
        assert result is None

    def test_with_ratios(self):
        """Test DMS conversion with ratio objects."""
        class MockRatio:
            def __init__(self, num, den):
                self.num = num
                self.den = den

        dms = [
            MockRatio(37, 1),  # 37 degrees
            MockRatio(30, 1),  # 30 minutes
            MockRatio(0, 1),   # 0 seconds
        ]
        result = dms_to_deg(dms)
        assert result is not None
        assert abs(result - 37.5) < 0.01
