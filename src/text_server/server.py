import json
import logging
import socket
import threading

from text_server.database import Database
from text_server.sampler import TextSampler


logger = logging.getLogger(__name__)


class TextServer:
    def __init__(
        self,
        database_path: str,
        host: str = "127.0.0.1",
        port: int = 5000,
    ) -> None:
        self._database_path = database_path
        self._host = host
        self._port = port
        self._server_socket: socket.socket | None = None
        self._running = False

    @property
    def address(self) -> tuple[str, int]:
        if self._server_socket is None:
            raise RuntimeError("Server has not started")

        return self._server_socket.getsockname()

    def start(self) -> None:
        if self._server_socket is not None:
            raise RuntimeError("Server has already started")

        server_socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM,
        )

        server_socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1,
        )

        server_socket.bind((self._host, self._port))
        server_socket.listen()

        self._server_socket = server_socket
        self._running = True

        logger.info(
            "Server listening on %s:%d",
            self.address[0],
            self.address[1],
        )

    def serve_forever(self) -> None:
        if self._server_socket is None:
            raise RuntimeError("Server has not started")

        while self._running:
            try:
                client_socket, client_address = self._server_socket.accept()
            except OSError:
                break

            logger.info("Client connected: %s", client_address)

            client_thread = threading.Thread(
                target=self._handle_client,
                args=(client_socket,),
                daemon=True,
            )

            client_thread.start()

    def shutdown(self) -> None:
        self._running = False

        if self._server_socket is not None:
            logger.info("Shutting down server")

            self._server_socket.close()
            self._server_socket = None

    def _handle_client(self, client_socket: socket.socket) -> None:
        database = Database(self._database_path)
        database.initialize()

        sampler = TextSampler(database)

        try:
            with client_socket:
                file = client_socket.makefile(
                    "r",
                    encoding="utf-8",
                )

                output = client_socket.makefile(
                    "w",
                    encoding="utf-8",
                )

                for line in file:
                    try:
                        request = json.loads(line)
                        response = self._handle_request(
                            request,
                            sampler,
                        )
                    except json.JSONDecodeError:
                        response = {
                            "status": "error",
                            "message": "Invalid JSON",
                        }

                    output.write(json.dumps(response) + "\n")
                    output.flush()

        finally:
            database.close()

    def _handle_request(
        self,
        request: dict,
        sampler: TextSampler,
    ) -> dict:
        action = request.get("action")

        if action == "load":
            count = sampler.load(request["path"])

            return {
                "status": "ok",
                "count": count,
            }

        if action == "sample":
            lines = sampler.sample(request["count"])

            return {
                "status": "ok",
                "lines": lines,
            }

        return {
            "status": "error",
            "message": f"Unknown action: {action}",
        }