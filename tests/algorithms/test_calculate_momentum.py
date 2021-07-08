import arrow
import pytest

from quality_momentum.algorithms import calculate_momentum as cm


def test_calculate_lookback_window():
    now = arrow.get("2020-01-20")
    lookback_period = 12
    expected_lookback_period = cm.LookbackPeriod(start=arrow.get("2019-01-01"), end=arrow.get("2019-12-01"))
    lookback_period = cm.calculate_lookback_window(now, lookback_period)

    assert expected_lookback_period == lookback_period


def test_positive_return_fips_number(ticker_with_daily_returns):
    cumulative_return = 0.123
    fips_number = cm.calculate_fips_number(ticker_with_daily_returns, cumulative_return)
    expected_fips_number = -0.18534482758620696

    assert fips_number == expected_fips_number


def test_negative_return_fips_number(ticker_with_daily_returns):
    cumulative_return = -0.123
    fips_number = cm.calculate_fips_number(ticker_with_daily_returns, cumulative_return)
    expected_fips_number = 0.18534482758620696

    assert fips_number == expected_fips_number


@pytest.mark.vcr()
def test_get_monthly_momentum(td_client, sample_date):
    metric = cm.get_monthly_momentum(td_client, "BA", sample_date)
    expected_metric = cm.QualityMomentumMetric(0.7134697130711996, fip=-0.18534482758620696, ticker="BA")

    assert metric == expected_metric


parameterized_data = [(1, ["BA"]), (3, ["BA", "AAPL", "FB"]), (5, ["BA", "AAPL", "FB", "MCD", "INTC"])]


@pytest.mark.parametrize("num_equities,expected_stocks", parameterized_data)
@pytest.mark.vcr()
def test_get_quality_momentum_stocks(td_client, num_equities, expected_stocks, sample_date):
    quality_stocks = cm.get_quality_momentum_stocks(td_client, sample_date, num_equities)

    assert quality_stocks == expected_stocks


def test_get_quality_momentum_stocks_in_future(td_client, sample_date, freezer):
    trading_day = sample_date.shift(days=+1)
    freezer.move_to(sample_date.datetime)
    with pytest.raises(AssertionError):
        quality_stocks = cm.get_quality_momentum_stocks(td_client, trading_day, 5)