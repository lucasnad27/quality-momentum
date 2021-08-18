import arrow
import pandas as pd
import pytest

from quality_momentum.equities import client, historical


def test_get_daily_price_history(s3_client, s3_bucket, tickers, expected_aapl_msft_price_history):
    start_date = arrow.get("1995-01-01")
    end_date = arrow.get("1995-02-01")
    history = historical.get_daily_price_history(
        s3_client, s3_bucket, tickers, start_date=start_date, end_date=end_date
    )

    pd.testing.assert_frame_equal(expected_aapl_msft_price_history, history)


def test_get_price(s3_client, s3_bucket):
    expected_closing_price = 0.3281
    closing_price = historical.get_price(s3_client, s3_bucket, "AAPL", arrow.get("1995-09-01"))
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
