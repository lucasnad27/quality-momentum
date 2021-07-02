"""Provides historical daily price data."""
import arrow
import pandas as pd
import tda
import trading_calendars as tc


PRICE_CACHE = pd.DataFrame()


def is_valid_trading_day(trading_day: arrow.arrow.Arrow) -> bool:
    """Decides if a given trading day is valid and returns a boolean."""
    trading_day_formatted = trading_day.format("YYYY-MM-DD")
    is_valid = False
    nyse = tc.get_calendar("NYSE")
    nasdaq = tc.get_calendar("NASDAQ")
    if nyse.is_session(trading_day_formatted) and nasdaq.is_session(trading_day_formatted):
        is_valid = True
    return is_valid


def get_daily_price_history(
    client: tda.client.synchronous.Client,
    ticker: str,
    start_date: arrow.arrow.Arrow,
    end_date: arrow.arrow.Arrow = None,
) -> pd.DataFrame:
    """Gets daily price history for a given equity."""
    if not end_date:
        end_date = arrow.utcnow()

    history_response = client.get_price_history(
        ticker,
        period_type=client.PriceHistory.PeriodType.YEAR,
        period=client.PriceHistory.Period.TWENTY_YEARS,
        frequency_type=client.PriceHistory.FrequencyType.DAILY,
        frequency=client.PriceHistory.Frequency.EVERY_MINUTE,
        end_datetime=end_date.datetime,
        start_datetime=start_date.datetime,
    )
    history_response.raise_for_status()
    df = pd.DataFrame(history_response.json()["candles"])
    # apply isn't ideal here, as it is essentially iterating through all rows, but I don't know of a better alternative
    # for the size of this dataset I think this is a reasonable hit to take on performance
    df["Date"] = df.apply(lambda x: arrow.get(x["datetime"]).date(), axis=1)
    df["Date"] = pd.to_datetime(df["Date"])

    # Using Quandl's format as inspiration for how this dataframe _should_ look like
    # Moving from raw api response to a dataframe will be a best opportunity to transform
    # data from numerous APIs into a canonical format, which for now is just like Quandl :)
    new_column_names = {"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"}
    df = df.drop(["datetime"], axis=1).set_index("Date").rename(columns=new_column_names)
    return df


def get_price(client: tda.client.synchronous.Client, ticker: str, date: arrow.arrow.Arrow) -> float:
    """Gets the closing price for an equity on the given date."""
    global PRICE_CACHE

    floored_date = date.floor("day")
    trading_day_index = date.format("YYYY-MM-DD")

    cache_check = PRICE_CACHE.empty or trading_day_index not in PRICE_CACHE.index
    if cache_check or PRICE_CACHE.loc[[trading_day_index]].query(f"Ticker == '{ticker}'").empty:
        # go out a year and grab the data
        df = get_daily_price_history(client, ticker, floored_date.shift(years=-1), floored_date.shift(years=1))
        df["Ticker"] = ticker
        PRICE_CACHE = PRICE_CACHE.append(df)
    return PRICE_CACHE.loc[[trading_day_index]].query(f"Ticker == '{ticker}'").at[trading_day_index, "Close"]
