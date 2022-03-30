import subprocess
import uuid

from flask import g
import werkzeug


class Tmux:
    """Tmux command enumeration class"""

    def __init__(self):
        self._id = str(uuid.uuid4())
        self._prefix = f"tmux send-keys -t stockfish-{self._id}".split(" ")
        self._msg = self._prefix + ["-l"]
        self._enter = self._prefix + ["enter"]

        self._start()

    def _start(self):
        """Start the tmux session"""
        session_name = f"stockfish-{self.id}"
        start_tmux = ["tmux", "new-session", "-d", "-s", session_name]
        start_stockfish = self._msg + [f"stockfish | tee /tmp/{session_name}.log"]

        self._send(start_tmux, enter=False)
        self._send(start_stockfish)

    @property
    def id(self):
        return self._id

    def message(self, msg):
        """Send a message through tmux stdin"""
        full_msg = self._msg + [msg]
        self._send(full_msg)

    def _send(self, msg_list, enter=True):
        try:
            subprocess.run(
                msg_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
            )
            if enter:
                subprocess.run(
                    self._enter,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True,
                )

        except subprocess.CalledProcessError as error:
            LOGGER.error(f"{g.request_id}: TMUX failed with {error}")
            LOGGER.error(f"{g.request_id}: starting retry {retry+1}")
            raise


TMUX = Tmux()
