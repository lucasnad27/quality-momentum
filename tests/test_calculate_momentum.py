import arrow
import pytest

from quality_momentum import calculate_momentum as cm


def test_calculate_lookback_window():
    now = arrow.get("2020-01-20")
    lookback_period = 12
    expected_lookback_period = cm.LookbackPeriod(start=arrow.get("2019-01-01"), end=arrow.get("2019-12-01"))
    lookback_period = cm.calculate_lookback_window(now, lookback_period)

    assert expected_lookback_period == lookback_period
