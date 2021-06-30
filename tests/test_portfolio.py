import arrow
import pytest

from quality_momentum import portfolio as pf


def test_trading_days_through_period():
    pass


@pytest.mark.parametrize(
    "trading_day,expected_value",
    [
        (arrow.get("2020-05-31"), True),
        (arrow.get("2020-02-29"), True),
        (arrow.get("2021-02-28"), True),
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


@pytest.mark.vcr()
def test_get_adjusted_close(td_client, sample_date, sample_ticker):
    adjusted_close = pf.get_adjusted_close(td_client, sample_ticker, sample_date)
    expected_close = 12.75
    assert adjusted_close == expected_close
