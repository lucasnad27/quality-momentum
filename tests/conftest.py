import sys

import arrow
import pandas as pd
import pytest

sys.path.append("./src")


@pytest.fixture(scope="module")
def vcr_config():
    return {
        "filter_headers": [("authorization", "DUMMY")],
        "filter_query_parameters": [("api_key", "DUMMY")],
        "match_on": ["method", "scheme", "host", "port", "path", "query", "headers", "body"],
    }


@pytest.fixture(scope="session")
def vcr_cassette_dir(request):
    return "./tests/fixtures/cassettes/"


@pytest.fixture(scope="session")
def sample_date():
    return arrow.get("2017-12-03")


@pytest.fixture(scope="session")
def sample_ticker():
    return "AMC"


@pytest.fixture
def ticker_with_daily_returns():
    return pd.read_csv("./tests/fixtures/ticker_with_daily_returns.csv")
