from http import HTTPStatus
import json
import logging

from flask import jsonify, g

from interfaces.stockfish import Stockfish
from managers import ChessGameManager

LOGGER = logging.getLogger(__name__)
CHESS_GAME_MANAGER = ChessGameManager()


def create_game(chess_game):
    """API Create Endpoint"""
    CHESS_GAME_MANAGER.create(chess_game)

    return jsonify({"msg": g.request_id}), HTTPStatus.CREATED


def get_game_by_id(game_id):
    """API Get Endpoint"""
    chess_game = CHESS_GAME_MANAGER.get(game_id=game_id)

    return jsonify(chess_game), HTTPStatus.OK


def list_games():
    """API List Endpoint"""
    chess_games = CHESS_GAME_MANAGER.list()

    return jsonify(chess_games), HTTPStatus.OK


def delete_game(game_id):
    """API Delete Endpoint"""
    CHESS_GAME_MANAGER.delete(game_id=game_id)

    return jsonify({"msg": "deleted"}), HTTPStatus.OK


def make_move(game_id, fen):
    """API Put Move Endpoint"""
    stockfish = Stockfish(fen)
    LOGGER.debug(
        f"{g.request_id} Beginning processing for FEN:\n{json.dumps(fen, indent=2)}"
    )
    stockfish_move = stockfish.calculate()

    # Assuming the frontend always provides a valid
    # fen string. We can ignore manually updating the
    # fen with stockfish's move and can just use the
    # incoming fen string.
    CHESS_GAME_MANAGER.set_fen(game_id=game_id, fen=fen)

    return jsonify({"msg": stockfish_move}), HTTPStatus.OK
