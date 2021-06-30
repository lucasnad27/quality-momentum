"""Provides access to td ameritade client."""
import os
import tda


class TdClient(tda.client.synchronous.Client):
    """
    Provides a td ameritrade client for the user.

    Uses locally stored td_token.json to authenticate and provide a client. If one does not exist,
    instructs user to authenticate through tdameritrade and persists a json file for future use
    """

    _instance = None

    def __new__(cls):
        """Provides a nice singleton wrapper for the client."""
        if cls._instance is None:
            cls._instance = cls._get_client()
        return cls._instance

    @classmethod
    def _get_client(cls) -> tda.client.synchronous.Client:
        api_key = os.environ["TD_API_KEY"]
        token_path = "td_token.json"
        redirect_url = "http://127.0.0.1:8000"
        try:
            client = tda.auth.client_from_token_file(token_path, api_key, asyncio=False)
        except FileNotFoundError:
            client = tda.auth.client_from_manual_flow(api_key, redirect_url, token_path)

        return client
