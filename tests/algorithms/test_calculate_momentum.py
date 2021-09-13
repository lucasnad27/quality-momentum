import arrow
import pandas as pd
import pytest

from quality_momentum.algorithms import calculate_momentum as cm


def test_calculate_lookback_window():
    now = arrow.get("2020-01-20")
    lookback_period = 12
    expected_lookback_period = cm.LookbackPeriod(start=arrow.get("2019-01-01"), end=arrow.get("2019-12-01"))
    lookback_period = cm.calculate_lookback_window(now, lookback_period)

    assert expected_lookback_period == lookback_period


def test_get_monthly_momentum(s3_client, s3_bucket, sample_tickers, sample_date_1995, expected_monthly_momentum_1995):
    df = cm.get_monthly_momentum(s3_client, s3_bucket, sample_tickers, sample_date_1995, num_lookback_months=6)
    pd.testing.assert_frame_equal(expected_monthly_momentum_1995, df)


def test_get_quality_momentum_stocks_in_future(s3_client, s3_bucket, sample_date_1995, freezer):
    trading_day = sample_date_1995.shift(days=+1)
    freezer.move_to(sample_date_1995.datetime)
    with pytest.raises(AssertionError):
        quality_stocks = cm.get_quality_momentum_stocks(s3_client, s3_bucket, trading_day, 5)


def test_get_universe_of_equities(s3_client, s3_bucket, sample_date_1995, mock_equity_universe, ticker_universe):
    tickers = cm.get_universe_of_equities(s3_client, s3_bucket, sample_date_1995, 40)
    assert ticker_universe == tickers
