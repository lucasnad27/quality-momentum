"""Module used to manage portfolio performance and actions."""

import math
from enum import Enum

import arrow
import exchange_calendars as ec
import numpy as np
import pandas as pd
from alive_progress import alive_bar
from arrow.arrow import Arrow
from typing import Generator

import quality_momentum as qm


class WeightType(Enum):
    """Portfolio weighting options."""

    equal_weighted = "equal_weighted"
    value_weighted = "value_weighted"


def trading_days_through_period(start_date: Arrow, end_date: Arrow) -> Generator[Arrow, None, None]:
    """Generates all trading days in a given time period and returns an arrow date."""
    current_time = start_date
    while current_time <= end_date:
        if qm.equities.historical.is_valid_trading_day(current_time):
            yield current_time
        current_time = current_time.shift(days=+1)


def eligible_for_rebalance(trading_day: Arrow) -> bool:
    """Decides if a given trading day should trigger a rebalance and returns a boolean."""
    is_eligible = False
    eligible_months = [2, 5, 8, 11]
    nyse = ec.get_calendar("NYSE")

    def _is_last_trading_day_in_month(_trading_day):
        last_date_in_month = pd.Timestamp(_trading_day.ceil("month").datetime)

        return nyse.previous_close(last_date_in_month).date() == _trading_day.date()

    if trading_day.month in eligible_months and _is_last_trading_day_in_month(trading_day):
        is_eligible = True

    return is_eligible


def get_adjusted_close(client: qm.equities.client.TdClient, ticker: str, trading_day: Arrow) -> float:
    """Returns the closing price for a symbol on a given day."""
    return qm.equities.historical.get_price(client, ticker, trading_day)


def update_positions(
    client: qm.equities.client.TdClient, transactions: pd.DataFrame, trading_day: Arrow, cash: float
) -> pd.DataFrame:
    """Calculates positions based on new transactions and returns a dataframe with the current positions sizes."""
    df = transactions.groupby(["symbol"])["amount"].sum().to_frame()
    df["date"] = pd.to_datetime(trading_day.naive)
    # move the ticker from index to the symbol column
    df = df.reset_index().set_index("date").query("amount!=0")
    df.index = df.index.tz_localize("UTC")
    df["price"] = df.apply(lambda x: get_adjusted_close(client, x["symbol"], trading_day), axis=1)
    df["value"] = df["price"] * df["amount"]
    cash_df = pd.DataFrame(
        {"symbol": "cash", "value": cash}, index=[pd.to_datetime(trading_day.naive).tz_localize("UTC")]
    )
    df = df.append(cash_df)
    return df.pivot_table(index=df.index, columns="symbol", values="value")


def calculate_returns(positions: pd.DataFrame) -> pd.Series:
    """
    Calculates daily returns over the same time period and returns a Series.

    > NOTE: Return calculations will mirror the date range of `positions`
    """
    return positions.sum(axis=1).pct_change().fillna(0)


def liquidate_shares(
    client: qm.equities.client.TdClient, trading_day: Arrow, transactions: pd.DataFrame
) -> pd.DataFrame:
    """Sells all current positions in portfolio, based on current positions"""
    if transactions.empty:
        return
    # use ONLY the transactions dataframe to identify what stocks to liquidate
    # all_positions = transactions.groupby('symbol').amount.sum()
    # df = all_positions[all_positions >= 0].to_frame()
    stock_positions = transactions.groupby("symbol").amount.sum()
    # filter out the rows with amount = 0
    df = stock_positions[stock_positions >= 0].to_frame()
    df["symbol"] = df.index
    df["amount"] = df["amount"] * -1
    df["price"] = df.apply(lambda x: get_adjusted_close(client, x["symbol"], trading_day), axis=1)
    df["txn_dollars"] = df["price"] * df["amount"] * -1
    df["date"] = pd.to_datetime(arrow.get(trading_day.date()).datetime)
    df.set_index("date", inplace=True)

    return df


def purchase_new_shares(
    client: qm.equities.client.TdClient,
    trading_day: Arrow,
    available_cash: float,
    num_holdings: int,
    weight_type: WeightType,
) -> pd.DataFrame:
    """
    Purchases shares of quality momentum stocks.

    Index: DatetimeIndex
    Columns: Index(['amount', 'price', 'symbol', 'txn_dollars'], dtype='object')
    """
    tickers = qm.algorithms.calculate_momentum.get_quality_momentum_stocks(client, trading_day, num_holdings)
    if weight_type == WeightType.value_weighted:
        raise NotImplementedError("Need to grab trading_day market cap to determine size of position")

    data = [(x, float(math.floor(available_cash / len(tickers)))) for x in tickers]
    df = pd.DataFrame(data, columns=["symbol", "position_size"])
    df["price"] = df.apply(lambda x: get_adjusted_close(client, x["symbol"], trading_day), axis=1)
    df["amount"] = (df["position_size"] / df["price"]).apply(np.floor).astype(int)
    df["txn_dollars"] = df["price"] * df["amount"] * -1
    df["date"] = pd.to_datetime(arrow.get(trading_day.date()).datetime)
    df.set_index("date", inplace=True)
    del df["position_size"]

    return df


class Portfolio:
    """Used for backtesting strategies and taking actions through time."""

    def __init__(self, **kwargs):
        """
        Creates a new immutable portfolio.

        Options include
        start_date --> arrow.Arrow
        end_date --> arrow.Arrow
        capital_allocation --> float
        weighting --> WeightType
        num_holdings --> integer
        """
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
        self.available_cash = capital_allocation
        self.start_date = start_date
        self.end_date = end_date
        self.weighting = weighting
        self.num_holdings = num_holdings
        self._transactions = pd.DataFrame()
        self._returns = pd.Series()
        self._positions = pd.DataFrame()
        self.td_client = qm.equities.client.TdClient()

    @property
    def transactions(self):
        """Records all transactions through portfolio's existence period."""
        if self._transactions.empty:
            self.run()
        return self._transactions

    @property
    def returns(self):
        """Returns a dataframe providing the returns over the lifetime of the portfolio."""
        if self._returns.empty:
            self.run()
        return self._returns

    @property
    def positions(self):
        """Returns a dataframe representing all positions through the lifetime of the portfolio."""
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
        # ensure that day_0 is a valid trading days, bump day forward until this is true
        while True:
            if qm.equities.historical.is_valid_trading_day(day_0):
                # day_0 is a valid trading day
                break
            day_0 = day_0.shift(days=+1)
        day_1 = day_0.shift(days=+1)

        # purchase shares, regardless of eligibility for rebalance
        self._transactions = purchase_new_shares(
            self.td_client, day_0, self.capital_allocation, self.num_holdings, self.weighting
        )
        # updates available cash, this looks odd because the txn_dollars amount is negative if we have purchased a stock
        # it's positive when we've sold a stock
        self.available_cash = self.capital_allocation + self._transactions.loc[day_0.datetime]["txn_dollars"].sum()
        # initialize positions based on first day's transactions
        updated_positions = update_positions(self.td_client, self._transactions, day_0, self.available_cash)
        # assign rows to the `day_0` self._positions index
        self._positions = self._positions.append(updated_positions)
        nyse = ec.get_calendar("NYSE")
        with alive_bar(len(nyse.sessions_in_range(self.start_date.datetime, self.end_date.datetime))) as bar:
            for trading_day in trading_days_through_period(day_1, self.end_date):
                if eligible_for_rebalance(trading_day):
                    self._transactions = self._transactions.append(
                        liquidate_shares(self.td_client, trading_day, self._transactions)
                    )
                    # filters out any purchased shares from this day
                    self.available_cash = (
                        self.available_cash
                        + self._transactions.loc[trading_day.datetime].query("txn_dollars>0")["txn_dollars"].sum()
                    )
                    self._transactions = self._transactions.append(
                        purchase_new_shares(
                            self.td_client, trading_day, self.available_cash, self.num_holdings, self.weighting
                        )
                    )
                    # filters out any sold shares from this day
                    self.available_cash = (
                        self.available_cash
                        + self._transactions.loc[trading_day.datetime].query("txn_dollars<0")["txn_dollars"].sum()
                    )

                updated_positions = update_positions(
                    self.td_client, self._transactions, trading_day, self.available_cash
                )
                self._positions = self._positions.append(updated_positions)
                bar()
        self._returns = calculate_returns(self._positions)
