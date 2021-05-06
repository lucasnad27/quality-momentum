import dataclasses
from typing import List

import arrow
import pandas as pd
import pandas_datareader as pdr
import matplotlib.pyplot as plt
import numpy as np


@dataclasses.dataclass
class LookbackPeriod:
    start: arrow.arrow.Arrow
    end: arrow.arrow.Arrow


@dataclasses.dataclass
class QualityMomentumMetric:
    momentum: float
    fip: float
    ticker: str


def calculate_lookback_window(now: arrow.arrow.Arrow, lookback_months: int) -> LookbackPeriod:
    # calculate lookback period for momentum
    # start period defined as the first day of the month, 13 months ago, enabling us to get initial value to compare
    start_period = now.shift(months=-lookback_months).replace(day=1)
    # end period excludes the most recent full month, (exclusive)
    end_period = now.shift(months=-1).replace(day=1)
    return LookbackPeriod(start_period, end_period)


def calculate_fips_number(ticker: pd.DataFrame, cumulative_return: float):
    # for more information on frog-in-the-pan (FIPs) see this publication:
    # Frog in the Pan: Continuous Information and Momentum
    # https://www3.nd.edu/~zda/Frog.pdf
    num_days = len(ticker)
    percent_positive_return = len(ticker[ticker["daily_returns"] > 0]) / num_days
    percent_negative_return = len(ticker[ticker["daily_returns"] < 0]) / num_days
    sgn_pret = 1 if cumulative_return > 0 else -1
    return sgn_pret * (percent_negative_return - percent_positive_return)


def get_monthly_momentum(ticker: str, now: arrow.arrow.Arrow = None, num_lookback_months=12) -> QualityMomentumMetric:
    if not now:
        now = arrow.utcnow()
    lookback_period = calculate_lookback_window(now, lookback_months=12)
    df = (
        pdr.quandl.QuandlReader(
            ticker, lookback_period.start.format("YYYY-MM-DD"), lookback_period.end.format("YYYY-MM-DD")
        )
        .read()
        .sort_index()
    )
    df["daily_returns"] = df["AdjClose"].pct_change()
    # calculate gross returns by month
    monthly_returns = df["daily_returns"].resample("M").apply(lambda x: ((x + 1).cumprod()).last("D"))
    cumulative_return = np.prod(monthly_returns) - 1
    # calculate FIP
    fip = calculate_fips_number(df, cumulative_return)
    return QualityMomentumMetric(ticker=ticker, momentum=cumulative_return, fip=fip)


def get_quality_momentum_stocks(trading_day: arrow.arrow.Arrow, num_equities: int) -> List[str]:
    """
    DISCLAIMER: num_equities and weight_type are currently vaporware, need to get a bigger universe of stocks to test this out. For now defaults to top decile of quality momentum, then taking top half based on FIPS
    returns a list of top quality momentum stocks for any given trading day
    """
    equities = get_universe_of_equities(trading_day)
    momentum_measures = [get_monthly_momentum(e, trading_day) for e in equities]
    df = pd.DataFrame.from_records([dataclasses.asdict(x) for x in momentum_measures], index="ticker")
    # df["quantile_rank"] = pd.qcut(df["momentum"], 10, labels=False)
    # top_decile_momentum_equities = df[df["quantile_rank"] == 9]
    top_momentum_equities = df.nlargest(num_equities * 2, "momentum")
    top_quality_momentum = pd.qcut(top_momentum_equities["fip"], 2, labels=["high_quality", "low_quality"])
    top_momentum_equities = top_momentum_equities.assign(quality_momentum=top_quality_momentum.values)
    equities_to_buy = top_momentum_equities[top_momentum_equities["quality_momentum"] == "high_quality"]
    return equities_to_buy.index.tolist()


def get_universe_of_equities(trading_day: arrow.arrow.Arrow) -> List[str]:
    return [
        "AAPL",
        "INTC",
        "TSLA",
        "MSFT",
        "NFLX",
        "FB",
        "AMZN",
        "SIRI",
        "GM",
        "F",
        "HD",
        "DIS",
        "BA",
        "MMM",
        "PFE",
        "NKE",
        "JNJ",
        "MCD",
        "INTC",
    ]
