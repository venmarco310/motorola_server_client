import json
import socket
import threading

from text_server.database import Database
from text_server.server import TextServer


def test_server_handles_sample_request(tmp_path):
    db_path = tmp_path / "test.db"

    database = Database(db_path)
    database.initialize()

    database.insert_lines([
        "first line",
        "second line",
        "third line",
    ])

    database.close()

    server = TextServer(
        database_path=str(db_path),
        host="127.0.0.1",
        port=0,
    )

    server.start()

    server_thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )
    server_thread.start()

    host, port = server.address

    with socket.create_connection((host, port)) as client:
        client_file = client.makefile(
            "rw",
            encoding="utf-8",
        )

        request = {
            "action": "sample",
            "count": 2,
        }

        client_file.write(json.dumps(request) + "\n")
        client_file.flush()

        response = json.loads(client_file.readline())

        client_file.close()

    server.shutdown()

    assert response["status"] == "ok"
    assert len(response["lines"]) == 2

    verification_database = Database(db_path)
    verification_database.initialize()

    assert verification_database.count_lines() == 1

    verification_database.close()