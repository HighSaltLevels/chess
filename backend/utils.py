import logging

from flask import g
import werkzeug

LOGGER = logging.getLogger(__name__)


def create_fen_obj(fen_str):
    """Convert the {fen_str} to a dict mapping"""
    LOGGER.info(f'Parsing FEN "{fen_str}"')
    fields = fen_str.split(" ")
    try:
        return {
            "pos": str(fields[0]),
            "turn": str(fields[1]),
            "castle": str(fields[2]),
            "en_passant": str(fields[3]),
            "halfmove": int(fields[4]),
            "fullmove": int(fields[5]),
        }

    except (IndexError, ValueError, TypeError) as error:
        LOGGER.error(f"{g.request_id}: {type(error)}: {error}")
        raise werkzeug.exceptions.BadRequest("Invalid FEN String")
