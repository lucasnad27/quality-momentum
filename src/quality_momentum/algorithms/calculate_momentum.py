"""Functionality to calculate high-quality momentum stocks."""
import dataclasses
from typing import List

import arrow
import pandas as pd
from mypy_boto3_s3.client import S3Client

import quality_momentum as qm


@dataclasses.dataclass
class LookbackPeriod:
    """Sets the time period to look back against."""

    start: arrow.arrow.Arrow
    end: arrow.arrow.Arrow


@dataclasses.dataclass
class QualityMomentumMetric:
    """Quality Momentum metrics."""

    momentum: float
    fip: float
    ticker: str


def calculate_lookback_window(now: arrow.arrow.Arrow, lookback_months: int) -> LookbackPeriod:
    """
    Calculate lookback period for momentum.

    start period defined as the first day of the month, 13 months ago, enabling us to get initial value to compare
    """
    start_period = now.shift(months=-lookback_months).replace(day=1)
    # end period excludes the most recent full month, (exclusive)
    end_period = now.shift(months=-1).replace(day=1)
    return LookbackPeriod(start_period, end_period)


def get_monthly_momentum(
    s3_client: S3Client, s3_bucket: str, tickers: List[str], now: arrow.arrow.Arrow = None, num_lookback_months=12
) -> pd.DataFrame:
    """Calculates quality momentum metric for a given stock."""
    if not now:
        now = arrow.utcnow()
    lookback_period = calculate_lookback_window(now, lookback_months=num_lookback_months)
    df = qm.equities.historical.get_daily_price_history(
        s3_client, s3_bucket, tickers, lookback_period.start, lookback_period.end
    )
    df["daily_returns"] = df.groupby("ticker")["adjusted_close"].pct_change()
    # calculate gross returns by month
    monthly_returns = df.groupby("ticker")["daily_returns"].resample("M").apply(lambda x: ((x + 1).cumprod()).last("D"))
    mo_data = {}
    # use to_numeric to ensure that we have a column of type float
    mo_data["momentum"] = pd.to_numeric(monthly_returns.groupby("ticker").prod() - 1)
    """
    Calculates Frog-In-The-Pan metric.

    For more information on frog-in-the-pan (FIPs) see this publication:
    Frog in the Pan: Continuous Information and Momentum https://www3.nd.edu/~zda/Frog.pdf

    As this value approaches 1, the more "discrete" the returns are, whereas most days are losers with a few outsized
    winners indicating high volatily. As this value approaches -1, this indicates that almost every day had a positive
    return, indicating a smooth path to positive returns, aka the frog slowly boiling in water.
    """
    # calculate percentage of trading days with positive and negative returns
    mo_data["percent_positive_returns"] = df.groupby("ticker")["daily_returns"].apply(lambda x: len(x[x >= 0]) / len(x))
    mo_data["percent_negative_returns"] = df.groupby("ticker")["daily_returns"].apply(lambda x: len(x[x < 0]) / len(x))
    mo_df = pd.concat(mo_data, axis=1)
    mo_df["sgn_pret"] = mo_df["momentum"].apply(lambda x: 1 if x > 0 else -1)
    mo_df["fips"] = mo_df["sgn_pret"] * (mo_df["percent_negative_returns"] - mo_df["percent_positive_returns"])
    return mo_df


def get_quality_momentum_stocks(
    s3_client: S3Client, s3_bucket: str, trading_day: arrow.arrow.Arrow, num_equities: int
) -> List[str]:
    """
    Calculates quality momentum and returns a list of top quality momentum stocks.

    DISCLAIMER: num_equities and weight_type are currently vaporware, need to get a bigger universe of stocks to test
    this out. For now defaults to top decile of quality momentum, then taking top half based on FIPS
    returns a list of top quality momentum stocks for any given trading day
    """
    assert trading_day <= arrow.utcnow(), "Unable to get momentum stocks for future dates"

    equities = get_universe_of_equities(s3_client, s3_bucket, trading_day, 40)
    assert len(equities) > 30, f"Unable to get enough equities to get quality momentum: {len(equities)} found"
    df = get_monthly_momentum(s3_client, s3_bucket, equities, trading_day)
    # df["quantile_rank"] = pd.qcut(df["momentum"], 10, labels=False)
    # top_decile_momentum_equities = df[df["quantile_rank"] == 9]
    top_momentum_equities = df.nlargest(num_equities * 2, "momentum")
    top_quality_momentum = pd.qcut(top_momentum_equities["fips"], 2, labels=["high_quality", "low_quality"])
    top_momentum_equities = top_momentum_equities.assign(quality_momentum=top_quality_momentum.values)
    equities_to_buy = top_momentum_equities[top_momentum_equities["quality_momentum"] == "high_quality"]
    # sort equities by momentum, avoids including too many results when equities share the same FIPS number
    return equities_to_buy.sort_values("momentum", ascending=False).head(num_equities).index.tolist()


def get_universe_of_equities(
    s3_client: S3Client, s3_bucket: str, trading_day: arrow.arrow.Arrow, percentile: int
) -> List[str]:
    """Return equities based on the top percentile market cap."""
    df = qm.equities.historical.get_eod_prices(s3_client, s3_bucket, trading_day)
    # return top percentile based on market cap
    return df.nlargest(int(len(df) * percentile / 100), "market_cap").index.tolist()
