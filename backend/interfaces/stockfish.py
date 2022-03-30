import logging
import re
import time

from flask import g
import gevent
from gevent.lock import RLock
import werkzeug

from interfaces.tmux import TMUX

LOGGER = logging.getLogger(__name__)
CALC_TIMEOUT_SEC = 60
DEFAULT_FEN = {
    "pos": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR",
    "turn": "w",
    "castle": "KQkq",
    "enPassant": "-",
    "halfmove": 0,
    "fullmove": 0,
}


class Stockfish:
    """Interface to stockfish to calculate moves"""

    BUFFER = f"/tmp/stockfish-{TMUX.id}.log"

    def __init__(self, fen=DEFAULT_FEN):
        self._fen = self.fen_to_str(fen)
        self.__lock = RLock()

    @staticmethod
    def fen_to_str(fen):
        """Convert the fen dict to a string"""
        return (
            f'{fen["pos"]} {fen["turn"]} {fen["castle"]} '
            f'{fen["enPassant"]} {fen["halfmove"]} {fen["fullmove"]}'
        )

    def calculate(self):
        """Send the move to stockfish and return the next move"""

        self.__lock.acquire()
        self._clear_buffer()
        self.health_check()

        TMUX.message("ucinewgame")
        self._set_pos()
        self._start_calculation()

        best_move = self._get_best_move()
        self.__lock.release()

        return best_move

    def health_check(self):
        """Send an isready and verify we get a readyok"""
        for retry in range(3):
            TMUX.message("isready")
            if "readyok" in self._read_buffer():
                self._clear_buffer()
                return

            LOGGER.error(f"{g.request_id} stockfish was not ready")
            LOGGER.error(f"{g.request_id} starting retry {retry+1}")

        else:
            raise werkzeug.exceptions.InternalServerError("Unknown Error")

    def _set_pos(self):
        """Set the fen string"""
        msg = f"position fen {self._fen}"
        TMUX.message(msg)

    def _start_calculation(self):
        """Send the command to start calculating"""
        msg = "go wtime 120000 btime 120000, winc, 2000, binc 2000"
        TMUX.message(msg)

    def _get_best_move(self):
        """Keep reading the buffer until we get 'best move'"""
        LOGGER.debug(
            f"{g.request_id} Begin watching buffer {self.BUFFER} for best move"
        )
        start_time = time.time()
        while time.time() < start_time + CALC_TIMEOUT_SEC:
            resp = self._read_buffer()
            match = re.search("bestmove [a-h][1-8][a-h][1-8]", resp)
            if match:
                best_move = match.group().split(" ")[1]
                LOGGER.debug(f"{g.request_id} Stockfish replied with {best_move}")
                return best_move

            gevent.sleep(1)

        raise werkzeug.exceptions.InternalServerError(
            "Stockfish took too long to respond"
        )

    def _clear_buffer(self):
        """Clear the stockfish message buffer"""
        LOGGER.debug(f"{g.request_id} Clearing buffer {self.BUFFER}")
        with open(self.BUFFER, "w"):
            pass

    def _read_buffer(self):
        """Read all data from the buffer"""
        with open(self.BUFFER) as resp:
            return resp.read()
