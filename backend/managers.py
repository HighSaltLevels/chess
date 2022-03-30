import hashlib
from http import HTTPStatus
import logging
import os

from flask import g
import gevent
import kubernetes.client
from kubernetes.client.rest import ApiException
import werkzeug

from interfaces.stockfish import DEFAULT_FEN

LOGGER = logging.getLogger(__name__)

SA_TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"
CA_CERT_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"


def retry_k8s(retries=1, delay_seconds=1):
    """Decorator for retrying communication with k8s."""

    def decorator(func):
        """Decorator"""

        def wrapper(*args, **kwargs):
            """Wrapper"""
            for retry in range(retries):
                try:
                    return func(*args, **kwargs)
                except ApiException as error:
                    if error.status == HTTPStatus.NOT_FOUND:
                        # Try to get game_id from kwargs.
                        # Omit the ID if we can't get it.
                        game_id = kwargs.get("game_id", "")

                        raise werkzeug.exceptions.NotFound(f"No such game {game_id}")

                    LOGGER.error(f"{g.request_id}: Unexpected exception {error}")
                    LOGGER.error(f"{g.request_id}: Retry number: {retry+1}")
                    gevent.sleep(delay_seconds)

            raise werkzeug.exceptions.InternalServerError("Unexpected Error")

        return wrapper

    return decorator


class ChessGameManager:
    """Kubernetes Interface via ServiceAccount token"""

    GROUP = "chess.greeson.xyz"
    API_VERSION = "v1"
    NAMESPACE = "chess"
    PLURAL = "chess-games"

    def __init__(self):
        with open(SA_TOKEN_PATH) as _file:
            token = _file.read().strip()

        host = os.getenv("KUBERNETES_SERVICE_HOST")
        port = os.getenv("KUBERNETES_SERVICE_PORT")
        url = f"https://{host}:{port}"
        configuration = kubernetes.client.Configuration(url)
        configuration.ssl_ca_cert = CA_CERT_PATH
        configuration.api_key["authorization"] = token
        configuration.api_key_prefix["authorization"] = "Bearer"
        with kubernetes.client.ApiClient(configuration) as api_client:
            self.__api = kubernetes.client.CustomObjectsApi(api_client)

    @retry_k8s()
    def create(self, chess_game):
        """Create a chess-game Custom Resource"""
        name = self._get_name(g.request_id)

        # Initialize the game history to a blank string.
        body = {
            "apiVersion": "chess.greeson.xyz/v1",
            "kind": "ChessGame",
            "metadata": {"name": name},
            "spec": {
                "id": g.request_id,
                "whitePlayerName": chess_game["whitePlayerName"],
                "blackPlayerName": chess_game["blackPlayerName"],
                "gameType": chess_game["gameType"],
                "fen": DEFAULT_FEN,
            },
        }

        resp = self.__api.create_namespaced_custom_object(
            self.GROUP, self.API_VERSION, self.NAMESPACE, self.PLURAL, body
        )

    @retry_k8s()
    def get(self, game_id):
        """Get the chess game CR by rehashing the ID"""
        name = self._get_name(game_id)
        resp = self.__api.get_namespaced_custom_object(
            self.GROUP, self.API_VERSION, self.NAMESPACE, self.PLURAL, name
        )
        return resp["spec"]

    @retry_k8s()
    def list(self):
        """List all chess games"""
        resp = self.__api.list_namespaced_custom_object(
            self.GROUP, self.API_VERSION, self.NAMESPACE, self.PLURAL
        )
        return [item["spec"] for item in resp["items"]]

    @retry_k8s()
    def delete(self, game_id):
        """Delete the chess game CR"""
        name = self._get_name(game_id)
        resp = self.__api.delete_namespaced_custom_object(
            self.GROUP, self.API_VERSION, self.NAMESPACE, self.PLURAL, name
        )

    @retry_k8s()
    def set_fen(self, game_id, fen):
        """Set the history of the game to {history}"""
        name = self._get_name(game_id)
        patch = {"spec": {"fen": fen}}

        resp = self.__api.patch_namespaced_custom_object(
            self.GROUP, self.API_VERSION, self.NAMESPACE, self.PLURAL, name, patch
        )

    @staticmethod
    def _get_name(game_id):
        """Get an md5 hash of the id and return only the first 8 chars"""
        md5 = hashlib.md5(game_id.encode("utf-8")).hexdigest()[:8]
        return f"game-{md5}"
