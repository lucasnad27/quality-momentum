"""Module used to manage portfolio performance and actions."""

import dataclasses
import math
from enum import Enum

import arrow
import numpy as np
import pandas as pd
import pandas_datareader as pdr
from arrow.arrow import Arrow
from typing import Generator

from quality_momentum import calculate_momentum


class WeightType(Enum):
    """Portfolio weighting options."""

    equal_weighted = "equal_weighted"
    value_weighted = "value_weighted"


def liquidate_positions(positions: pd.DataFrame) -> pd.DataFrame:
    """Liquidate all open positions."""
    if not positions.empty:
        return


def trading_days_through_period(start_date: Arrow, end_date: Arrow) -> Generator[Arrow, None, None]:
    """Generates all trading days in a given time period and returns an arrow date."""
    current_time = start_date
    while current_time <= end_date:
        yield current_time
        current_time = current_time.shift(days=+1)


def eligible_for_rebalance(trading_day: Arrow) -> bool:
    """Decides if a given trading day should trigger a rebalance and returns a boolean."""
    is_eligible = False
    eligible_months = [2, 5, 8, 11]
    # consider using trading-calendars lib to identify if we are in the last trading day of the month
    # for now, we are doing something dumb with arrow and it won't work if this is a weekend or trading holiday
    last_day_of_month = trading_day.date() == trading_day.ceil("month").date()
    if trading_day.month in eligible_months and last_day_of_month:
        is_eligible = True

    return is_eligible


def get_adjusted_close(ticker: str, trading_day: Arrow) -> float:
    """Returns the closing price for a symbol on a given day."""
    print(ticker)
    df = pdr.quandl.QuandlReader(
        ticker, trading_day.format("YYYY-MM-DD"), trading_day.shift(days=+1).format("YYYY-MM-DD")
    ).read()
    return df["AdjClose"].array[0]


def update_positions(transactions: pd.DataFrame, trading_day) -> pd.DataFrame:
    """Calculates positions based on new transactions and returns a dataframe with the current positions sizes."""

    # TODO Include stock splits & dividends into position calculation
    # TODO Include cash as a "symbol"
    df = transactions.groupby(["symbol"])["amount"].sum().to_frame()
    df["date"] = trading_day

    # move the ticker from index to the symbol column
    df = df.reset_index().set_index("date").query("amount>0")
    df["price"] = df.apply(lambda x: get_adjusted_close(x["symbol"], trading_day), axis=1)
    df["value"] = df["price"] * df["amount"]
    return df.pivot_table(index="date", columns="symbol", values="value")


def calculate_returns(positions: pd.DataFrame) -> pd.Series:
    """
    Calculates daily returns over the same time period and returns a Series.

    > NOTE: Return calculations will mirror the date range of `positions`
    """
    return positions.sum(axis=1).pct_change().fillna(0)


def purchase_new_shares(
    trading_day: Arrow, available_cash: float, num_holdings: int, weight_type: WeightType
) -> pd.Series:
    """
    TODO: Update this docstring

    Index: DatetimeIndex
    Columns: Index(['amount', 'price', 'symbol', 'txn_dollars'], dtype='object')
    """
    tickers = calculate_momentum.get_quality_momentum_stocks(trading_day, num_holdings)
    if weight_type == WeightType.value_weighted:
        # Consider Sharadar data from quandl to pull in market cap data
        # https://www.quandl.com/databases/SF1/data
        raise NotImplementedError("Need to grab trading_day market cap to determine size of position")

    data = [(x, math.floor(available_cash / len(tickers))) for x in tickers]
    df = pd.DataFrame(data, columns=["symbol", "position_size"])
    df["price"] = df.apply(lambda x: get_adjusted_close(x["symbol"], trading_day), axis=1)
    df["amount"] = (df["position_size"] / df["price"]).apply(np.floor)
    df["txn_dollars"] = df["price"] * df["amount"]
    df["date"] = trading_day
    df.set_index("date", inplace=True)
    del df["position_size"]
    return df


class Portfolio:
    """Used for backtesting strategies and taking actions through time."""

    def __init__(self, **kwargs):
        """TODO: Add kwargs."""
        start_date = kwargs["start_date"]
        end_date = kwargs["end_date"]
        capital_allocation = kwargs["capital_allocation"]
        weighting = kwargs["weighting"]
        num_holdings = kwargs.get("num_holdings", 20)
        assert isinstance(start_date, arrow.arrow.Arrow)
        assert isinstance(end_date, arrow.arrow.Arrow)
        assert isinstance(capital_allocation, float)
        assert isinstance(weighting, WeightType)
        assert isinstance(num_holdings, int)

        self.capital_allocation = capital_allocation
        self.start_date = start_date
        self.end_date = end_date
        self.weighting = weighting
        self.num_holdings = num_holdings
        self._transactions = pd.DataFrame()
        self._returns = pd.DataFrame()
        self._positions = pd.DataFrame()
        self._shares = None

    @property
    def transactions(self):
        """Records all transactions through portfolio's existence period."""
        if self._transactions.empty:
            self.run()
        return self._transactions

    @property
    def returns(self):
        """TODO: Describe purpose of transactions."""
        if self._returns.empty:
            self.run()
        return self._returns

    @property
    def positions(self):
        """TODO: Describe purpose of positions."""
        if self._positions.empty:
            self.run()
        return self._positions

    def run(self):
        """
        Iterates through each day of the portfolio time period.

        Add record to positions dataframe and returns series identify if action should be taken if so.
        pull data for equity universe and identify top n stocks
        calculate position size for each stock and number of stocks to purchase
        liquidate all existing positions (add to transactions dataframe)
        enter new positions (add to transactions dataframe)
        Rebalance quarterly, before quarter ending months: end of February, May, August, and November.
        """
        day_0 = self.start_date
        day_1 = self.start_date.shift(days=+1)
        # purchase shares, regardless of eligibility for rebalance
        self._transactions = purchase_new_shares(day_0, self.capital_allocation, self.num_holdings, self.weighting)
        # initialize positions based on first day's transactions
        updated_positions = update_positions(self._transactions, day_0)
        # assign rows to the `day_0` self._positions index
        self._positions = self._positions.append(updated_positions)
        for trading_day in trading_days_through_period(day_1, self.end_date):
            updated_positions = update_positions(self._transactions, trading_day)
            self._positions = self._positions.append(updated_positions)
            if eligible_for_rebalance(trading_day):
                # TODO: Implement liquidation and share purchasing
                pass
            # kill the backtest until remainder of data layer functionality and rebalancing is complete
            break

        # calculate returns based on positions df, after iterating through trading days
        self._returns = calculate_returns(self._positions)
