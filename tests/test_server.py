import json
import socket
import threading

from text_server.database import Database
from text_server.server import TextServer


def test_server_handles_multiple_requests_on_same_connection(tmp_path):
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

        first_request = {
            "action": "sample",
            "count": 2,
        }

        client_file.write(json.dumps(first_request) + "\n")
        client_file.flush()

        first_response = json.loads(client_file.readline())

        second_request = {
            "action": "sample",
            "count": 2,
        }

        client_file.write(json.dumps(second_request) + "\n")
        client_file.flush()

        second_response = json.loads(client_file.readline())

        client_file.close()

    server.shutdown()

    assert first_response["status"] == "ok"
    assert len(first_response["lines"]) == 2

    assert second_response["status"] == "ok"
    assert len(second_response["lines"]) == 1

    sampled_lines = (
        first_response["lines"]
        + second_response["lines"]
    )

    assert len(set(sampled_lines)) == 3

    verification_database = Database(db_path)
    verification_database.initialize()

    assert verification_database.count_lines() == 0

    verification_database.close()