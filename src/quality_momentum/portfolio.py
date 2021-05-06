import math
from enum import Enum

import arrow
import pyfolio as pf
import pandas as pd
from arrow.arrow import Arrow
from typing import Generator

from quality_momentum import calculate_momentum


class WeightType(Enum):
    equal_weighted = "equal_weighted"
    value_weighted = "value_weighted"


def liquidate_positions(positions: pd.DataFrame) -> pd.DataFrame:
    pass


def trading_days_through_period(start_date: Arrow, end_date: Arrow) -> Generator[Arrow, None, None]:
    current_time = start_date
    while current_time <= end_date:
        yield current_time
        current_time = current_time.shift(days=+1)


def eligible_for_rebalance(trading_day: Arrow) -> bool:
    # Rebalance quarterly, before quarter ending months: end of February, May, August, and November
    is_eligible = False
    eligible_months = [2, 5, 8, 11]
    # consider using trading-calendars lib to identify if we are in the last trading day of the month
    # for now, we are doing something dumb with arrow and it won't work if this is a weekend or trading holiday
    last_day_of_month = trading_day.date() == trading_day.ceil("month").date()
    if trading_day.month in eligible_months and last_day_of_month:
        is_eligible = True

    return is_eligible


def purchase_new_shares(
    trading_day: Arrow, available_cash: float, num_holdings: int, weight_type: WeightType
) -> pd.Series:
    """
    returns a series representing transactions for the given date (will always be `trading_day`)
    Index: DatetimeIndex
    Columns: Index(['amount', 'price', 'sid', 'symbol', 'txn_dollars'], dtype='object')
    """
    tickers = calculate_momentum.get_quality_momentum_stocks(trading_day, num_holdings)
    if weight_type == WeightType.value_weighted:
        # Consider Sharadar data from quandl to pull in market cap data
        # https://www.quandl.com/databases/SF1/data
        raise NotImplementedError("Need to grab trading_day market cap to determine size of position")

    data = {x: math.floor(available_cash / len(tickers)) for x in tickers}
    df = pd.DataFrame.from_dict(data, orient="index", columns=["position_size"])
    return df


class Portfolio:
    def __init__(self, **kwargs):
        start_date = kwargs["start_date"]
        end_date = kwargs["start_date"]
        capital_allocation = kwargs["capital_allocation"]
        weighting = kwargs["weighting"]
        num_holdings = kwargs.get("num_holdings", 20)
        assert isinstance(start_date, arrow.arrow.Arrow)
        assert isinstance(end_date, arrow.arrow.Arrow)
        assert isinstance(capital_allocation, float)
        assert isinstance(weighting, WeightType)
        assert isinstance(num_holdings, int)

        self.capital = capital
        self.start_date = kwargs["start_date"]
        self.end_date = kwargs["end_date"]
        self.weighting = weighting
        self._transactions = pd.DataFrame
        self._returns = None
        self._positions = None
        self._shares = None

    @property
    def transactions(self):
        if not self._transactions:
            print("time to make the donuts")
            self.run()
        return self._transactions

    @property
    def returns(self):
        if not self._returns:
            print("time to make the donuts")
            self.run()
        return self._returns

    @property
    def positions(self):
        if not self._positions:
            print("time to make the donuts")
            self.run()
        return self._positions

    def run(self):
        # iterate through each day of the portfolio time period
        # add record to positions dataframe and returns series
        # identify if action should be taken if so...
        # pull data for equity universe and identify top n stocks
        # calculate position size for each stock and number of stocks to purchase
        # liquidate all existing positions (add to transactions dataframe)
        # enter new positions (add to transactions dataframe)
        # Rebalance quarterly, before quarter ending months: end of February, May, August, and November.

        for trading_day in trading_days_through_period(self.start_date, self.end_date):
            # sum positions from previous day, psuedocode...
            # previous_portfolio_value = np.sum(self._positions[trading_day])
            # skip these two functions for now, until we determine what positions DF looks like
            # calculate_current_positions()
            # calculate_latest_daily_return()
            if eligible_for_rebalance(trading_day):
                self._positions[trading_day] = liquidate_positions(self._positions[trading_day])
                available_cash = self._positions[trading_day]["cash"]
                purchased_shares = purchase_new_shares(trading_day, available_cash, self.num_holdings, self.weighting)
                # ***************************** #

        self._transactions = "donuts"
        self._returns = "more donuts?"
        self._positions = "yes, more donuts"
