import logging
import os
import time
import uuid

import connexion
from flask import g, request

# Developers can optionally set the "DEBUG" env var to
# enable debug logging.
LOG_LEVEL = logging.DEBUG if os.getenv("DEBUG") else logging.INFO

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=LOG_LEVEL)


def app():
    """Create the connexion app"""
    app = connexion.FlaskApp("Chess Server")
    app.add_api("server/api.yml")

    @app.app.before_request
    def create_id():
        """Create a request ID to be used throughout the request"""
        g.request_id = str(uuid.uuid4())
        g.start_time = time.time()

    @app.app.after_request
    def inject_id(response):
        """Inject the request ID into the headers"""
        response.headers["requestId"] = g.request_id

        request_time = time.time() - g.start_time
        LOGGER.info(f"{g.request_id}: {request.path} took {request_time}s")

        return response

    return app
