import arrow
import pandas as pd
import pytest

from quality_momentum.equities import client, historical


@pytest.mark.vcr()
def test_get_daily_price_history(td_client, aapl_price_history):
    start_date = arrow.get("2020-01-01")
    end_date = arrow.get("2020-02-01")
    expected_history = aapl_price_history
    history = historical.get_daily_price_history(td_client, "AAPL", start_date=start_date, end_date=end_date)

    pd.testing.assert_frame_equal(expected_history, history)


@pytest.mark.vcr()
def test_get_price(td_client):
    expected_closing_price = 125.06
    closing_price = historical.get_price(td_client, "AAPL", arrow.get("2021-06-02"))
    assert closing_price == expected_closing_price


@pytest.mark.parametrize(
    "trading_day,expected_value",
    [
        (arrow.get("2021-01-01"), False),
        (arrow.get("2021-07-02"), True),
        (arrow.get("1998-05-23"), False),
        (arrow.get("1998-05-22"), True),
        (arrow.get("2021-01-29"), True),
        (arrow.get("2021-01-31"), False),
    ],
)
def test_valid_trading_days(trading_day, expected_value):
    assert historical.is_valid_trading_day(trading_day) == expected_value
