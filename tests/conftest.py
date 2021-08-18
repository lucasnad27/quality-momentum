import json
import os
import sys

import arrow
import boto3
import pandas as pd
import pytest
from moto import mock_s3

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
def sample_date_2017():
    return arrow.get("2017-12-04")


@pytest.fixture(scope="session")
def sample_date_1995():
    return arrow.get("1995-09-01")


@pytest.fixture(scope="session")
def sample_ticker():
    return "AAPL"


@pytest.fixture
def ticker_with_daily_returns():
    return pd.read_csv("./tests/fixtures/ticker_with_daily_returns.csv")


@pytest.fixture
def aapl_price_history_2019():
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


@pytest.fixture(scope="module")
def aws_credentials():
    os.environ["AWS_ACCESS_KEY_ID"] = "dummy"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "dummy"
    os.environ["AWS_SESSION_TOKEN"] = "dummy"
    os.environ["AWS_SECURITY_TOKEN"] = "dummy"


@pytest.fixture(scope="module")
def s3_client(aws_credentials, s3_bucket):
    """Mock S3 client based on env vars"""
    with mock_s3():
        client = boto3.client("s3", region_name="us-east-1")
        _load_eod_data(client, s3_bucket)
        yield client


@pytest.fixture(scope="module")
def expected_aapl_msft_price_history():
    return pd.read_csv("./tests/fixtures/expected_outputs/aapl_msft_1995.csv", index_col=0, parse_dates=True)


@pytest.fixture(scope="module")
def expected_monthly_momentum_1995():
    return pd.read_csv("./tests/fixtures/expected_outputs/monthly_momentum_1995.csv", index_col=0)


@pytest.fixture(scope="module")
def tickers():
    return ["AAPL", "MSFT"]


@pytest.fixture(scope="module")
def s3_bucket():
    return "test-stock-universe"


def _load_eod_data(s3_client, s3_bucket):
    # iterate through the ./tests/fixtures/s3 directory and load each file to S3
    fixture_dir = "./tests/fixtures/s3/"

    def transform_file_to_s3_key(dir_path, file):
        # NOTE: this is fragile, but the worst it will do is break tests 🤷🏼‍♂️
        return os.path.join(dir_path.replace(fixture_dir, ""), file)

    s3_client.create_bucket(Bucket=s3_bucket)
    for root, _, files in os.walk(fixture_dir):
        for file in files:
            if file.endswith(".csv"):
                with open(os.path.join(root, file)) as f:
                    s3_client.put_object(
                        Bucket=s3_bucket,
                        Key=transform_file_to_s3_key(root, file),
                        Body=f.read(),
                        ContentType="text/csv",
                    )
