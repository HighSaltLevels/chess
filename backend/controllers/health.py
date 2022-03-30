from http import HTTPStatus

from flask import jsonify

from interfaces.stockfish import Stockfish


def check():
    """Perform a simple health check"""
    return jsonify({"msg": "healthy"}), HTTPStatus.OK


def deep_check():
    """Perform a deep health check of dependent services"""
    stockfish = Stockfish()
    # If communication fails with stockfish, intercept the
    # InternalServerError and re-raise with a specific message.
    try:
        stockfish.health_check()
        return jsonify({"msg": "healthy"}), HTTPStatus.OK
    except werkzeug.exceptions.InternalServerError as error:
        raise werkzeug.exceptions.InternalServerError(
            "Stockfish is unhealthy"
        ) from error
