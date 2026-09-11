import json
import socket
from pathlib import Path


class ServerError(Exception):
    """Raised when the server returns an error response."""


class TextClient:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 5000,
    ) -> None:
        self._host = host
        self._port = port
        self._socket: socket.socket | None = None
        self._file = None

    def connect(self) -> None:
        if self._socket is not None:
            raise RuntimeError("Client is already connected")

        self._socket = socket.create_connection(
            (self._host, self._port)
        )

        self._file = self._socket.makefile(
            "rw",
            encoding="utf-8",
        )

    def load(self, file_path: str | Path) -> int:
        response = self._request({
            "action": "load",
            "path": str(file_path),
        })

        return response["count"]

    def sample(self, count: int) -> list[str]:
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise ValueError("count must be a non-negative integer")

        response = self._request({
            "action": "sample",
            "count": count,
        })

        return response["lines"]

    def close(self) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None

        if self._socket is not None:
            self._socket.close()
            self._socket = None

    def _request(self, request: dict) -> dict:
        if self._file is None:
            raise RuntimeError("Client is not connected")

        self._file.write(json.dumps(request) + "\n")
        self._file.flush()

        response_line = self._file.readline()

        if not response_line:
            raise ConnectionError("Server closed the connection")

        response = json.loads(response_line)

        if response.get("status") == "error":
            raise ServerError(response.get("message", "Unknown server error"))

        return response