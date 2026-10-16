
import pytest
from diagnostics_worker.tasks.cleanup import (
    parse_dry_run,
    parse_retention_days,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, 90),
        ("90", 90),
        ("1", 1),
        ("365", 365),
    ],
)
def test_parse_retention_days_valid(value, expected):
    assert parse_retention_days(value) == expected


@pytest.mark.parametrize(
    "value",
    ["0", "-1", "abc", "1.5"],
)
def test_parse_retention_days_invalid(value):
    with pytest.raises(ValueError):
        parse_retention_days(value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, True),
        ("true", True),
        ("YES", True),
        ("1", True),
        ("false", False),
        ("NO", False),
        ("0", False),
    ],
)
def test_parse_dry_run_valid(value, expected):
    assert parse_dry_run(value) is expected


@pytest.mark.parametrize(
    "value",
    ["maybe", "enabled", ""],
)
def test_parse_dry_run_invalid(value):
    with pytest.raises(ValueError):
        parse_dry_run(value)
