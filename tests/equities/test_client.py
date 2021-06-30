import pytest

from quality_momentum.equities import client


def test_client_no_file(mocker):
    mocker.patch("tda.auth.client_from_token_file", side_effect=FileNotFoundError)
    mock_manual_flow = mocker.patch("tda.auth.client_from_manual_flow")

    td_client = client.TdClient()
    mock_manual_flow.assert_called_once


def test_client_from_file(mocker):
    mock_from_token_file = mocker.patch("tda.auth.client_from_token_file")
    td_client = client.TdClient()
    assert mock_from_token_file.not_called
