import json
import os
import sys

import arrow
import pandas as pd
import pytest

sys.path.append("./src")


from quality_momentum.equities import client


@pytest.fixture(scope="module")
def vcr_config():
    return {
        "filter_headers": [("authorization", "DUMMY")],
        "filter_post_data_parameters": [("refresh_token", "DUMMY")],
        "filter_query_parameters": [("api_key", "DUMMY"), ("apikey", "DUMMY")],
        "match_on": ["method", "scheme", "host", "port", "path", "query", "headers", "body"],
    }


@pytest.fixture(scope="session")
def vcr_cassette_dir(request):
    return "./tests/fixtures/cassettes/"


@pytest.fixture(scope="session")
def sample_date():
    return arrow.get("2017-12-04")


@pytest.fixture(scope="session")
def sample_ticker():
    return "AMC"


@pytest.fixture
def ticker_with_daily_returns():
    return pd.read_csv("./tests/fixtures/ticker_with_daily_returns.csv")


@pytest.fixture
def aapl_price_history():
    return pd.read_csv("./tests/fixtures/get_daily_price_history_aapl.csv", index_col=["Date"], parse_dates=["Date"])


@pytest.fixture(scope="session")
def token_data():
    now = arrow.utcnow()
    return json.dumps(
        {
            "creation_timestamp": int(now.timestamp()),
            "token": {
                "access_token": "DUMMY",
                "scope": "PlaceTrades AccountAccess MoveMoney",
                "expires_in": 1800,
                "token_type": "Bearer",
                "expires_at": int(now.shift(minutes=+30).timestamp()),
                "refresh_token": "DUMMY-REFRESH",
            },
        }
    )


@pytest.fixture()
def td_client(mocker, token_data):
    # do I need to specify exactly where the `open` gets called from? May need to go look at the source code for tdapi
    token_path = "./td_token.json"
    test_vcr_record = os.getenv("TEST_VCR_RECORD", "false").lower() == "true"
    if not test_vcr_record:
        with open(token_path, "w") as w:
            w.write(token_data)

    yield client.TdClient()

    if not test_vcr_record:
        os.remove(token_path)
