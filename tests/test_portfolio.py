import arrow
import pytest

from quality_momentum import portfolio as pf


@pytest.mark.parametrize(
    "trading_day,expected_value",
    [
        (arrow.get("2020-05-31"), False),
        (arrow.get("2020-02-29"), False),
        (arrow.get("2021-02-26"), True),
        (arrow.get("2020-08-31"), True),
        (arrow.get("2020-11-30"), True),
        (arrow.get("2020-03-15"), False),
        (arrow.get("2020-11-29"), False),
        (arrow.get("2020-12-31"), False),
    ],
)
def test_eligible_for_rebalance(trading_day, expected_value):
    ret_value = pf.eligible_for_rebalance(trading_day)
    assert ret_value == expected_value
