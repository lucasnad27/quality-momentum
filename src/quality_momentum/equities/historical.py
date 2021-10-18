"""Provides historical daily price data."""
import functools
import os
from typing import List, Optional

import arrow
import exchange_calendars as ec
import pandas as pd
from mypy_boto3_s3.client import S3Client
from tenacity import retry, wait


# LOCAL_S3_CACHE_DIR = os.environ["LOCAL_S3_CACHE_DIR"]
LOCAL_S3_CACHE_DIR = "../../s3_data"


def is_valid_trading_day(trading_day: arrow.arrow.Arrow) -> bool:
    """Decides if a given trading day is valid and returns a boolean."""
    trading_day_formatted = trading_day.format("YYYY-MM-DD")
    is_valid = False
    nyse = ec.get_calendar("NYSE")
    nasdaq = ec.get_calendar("NASDAQ")
    if nyse.is_session(trading_day_formatted) and nasdaq.is_session(trading_day_formatted):
        is_valid = True
    return is_valid


def get_eod_prices(s3_client: S3Client, s3_bucket: str, trading_day: arrow.arrow.Arrow) -> pd.DataFrame:
    """Gets the EOD price for all tickers on the given trading day."""

    @functools.lru_cache(maxsize=500)
    @retry(wait=wait.wait_random_exponential(multiplier=1, max=3))
    def get_price(trading_day):
        trading_day_formatted = trading_day.format("YYYY/MM/DD")
        s3_path = f"{trading_day_formatted}/prices/us.csv"
        # attempt to grab a file locally, if it can't find it, grab it from S3
        local_path = os.path.join(LOCAL_S3_CACHE_DIR, s3_path)
        if os.path.exists(local_path):
            df = pd.read_csv(local_path, index_col=0)
        else:
            raise RuntimeError("unable to find local path")
            # print('reading EOD prices from s3')
            # s3_response = s3_client.get_object(Bucket=s3_bucket, Key=s3_path)
            # df = pd.read_csv(s3_response["Body"], index_col=0)
        df["Ticker"] = df.index
        return df

    return get_price(trading_day)


def get_price(
    s3_client: S3Client, s3_bucket: str, ticker: str, trading_day: arrow.arrow.Arrow, stack_calls: int = 0
) -> Optional[float]:
    """
    Returns the adjusted close for a ticker on the date.

    If trading_day is not a valid trading day on the NYSE, the most recent
    day, up to `trading_day` is used.
    """
    stack_calls += 1
    max_stack_calls = 50
    if stack_calls > max_stack_calls:
        raise RuntimeError(
            f"stack_calls exceeded max_stack_calls: {max_stack_calls} for {ticker} on {trading_day.format('YYYY-MM-DD')}"
        )

    while not is_valid_trading_day(trading_day):
        trading_day = trading_day.shift(days=-1)

    df = get_eod_prices(s3_client, s3_bucket, trading_day)
    price = None
    try:
        price = df.loc[ticker]["adjusted_close"]
    except KeyError:
        # unable to get price for given ticker. Rewind day until we retrieve valid price
        price = get_price(s3_client, s3_bucket, ticker, trading_day.shift(days=-1), stack_calls)
    return price


def get_daily_price_history(
    s3_client: S3Client,
    s3_bucket: str,
    tickers: List[str],
    start_date: arrow.arrow.Arrow,
    end_date: arrow.arrow.Arrow = None,
) -> pd.DataFrame:
    """Gets daily price history for a given equity."""
    if not end_date:
        end_date = arrow.utcnow()

    nyse = ec.get_calendar("NYSE")
    trading_sessions = nyse.sessions_in_range(start_date.datetime, end_date.datetime)
    history_df = pd.DataFrame(
        columns=[
            "name",
            "type",
            "exchange_short_name",
            "Beta",
            "open",
            "high",
            "low",
            "close",
            "adjusted_close",
            "volume",
            "ema_50d",
            "ema_200d",
            "hi_250d",
            "lo_250d",
            "avgvol_14d",
            "avgvol_50d",
            "Ticker",
            "outstanding_shares",
            "market_cap",
        ]
    )
    for session in trading_sessions:
        session_date = arrow.get(session.date())
        df = get_eod_prices(s3_client, s3_bucket, session_date)
        # remove tickers from the dataframe that aren't in the list of tickers
        df = df[df["Ticker"].isin(tickers)]
        # convert date to a datetime and set as index
        with pd.option_context("mode.chained_assignment", None):
            # removing a warning, dragons ahead!
            df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)
        history_df = history_df.append(df)

    history_df.rename(columns={"Ticker": "ticker", "MarketCapitalization": "market_cap"}, inplace=True)
    # zero out any obnoxious NaN market cap values
    history_df["market_cap"] = history_df["market_cap"].fillna(0).astype("int64")
    history_df["ema_50d"] = history_df["ema_50d"].astype("int64")
    history_df["ema_200d"] = history_df["ema_200d"].astype("int64")
    history_df["hi_250d"] = history_df["hi_250d"].astype("int64")
    history_df["lo_250d"] = history_df["lo_250d"].astype("int64")
    history_df["avgvol_14d"] = history_df["avgvol_14d"].astype("int64")
    history_df["avgvol_50d"] = history_df["avgvol_50d"].astype("int64")
    return history_df
