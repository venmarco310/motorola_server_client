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


def test_server_handles_concurrent_clients(tmp_path):
    db_path = tmp_path / "test.db"

    database = Database(db_path)
    database.initialize()

    database.insert_lines(
        [f"line {i}" for i in range(100)]
    )

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

    results = []

    def sample_lines():
        with socket.create_connection((host, port)) as client:
            client_file = client.makefile(
                "rw",
                encoding="utf-8",
            )

            request = {
                "action": "sample",
                "count": 50,
            }

            client_file.write(json.dumps(request) + "\n")
            client_file.flush()

            response = json.loads(client_file.readline())

            results.append(response)

            client_file.close()

    client_threads = [
        threading.Thread(target=sample_lines)
        for _ in range(2)
    ]

    for thread in client_threads:
        thread.start()

    for thread in client_threads:
        thread.join()

    server.shutdown()

    assert len(results) == 2

    assert all(
        response["status"] == "ok"
        for response in results
    )

    sampled_lines = [
        line
        for response in results
        for line in response["lines"]
    ]

    assert len(sampled_lines) == 100
    assert len(set(sampled_lines)) == 100

    verification_database = Database(db_path)
    verification_database.initialize()

    assert verification_database.count_lines() == 0

    verification_database.close()

def test_server_returns_error_for_unknown_action(tmp_path):
    db_path = tmp_path / "test.db"

    database = Database(db_path)
    database.initialize()
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
            "action": "invalid",
        }

        client_file.write(json.dumps(request) + "\n")
        client_file.flush()

        response = json.loads(client_file.readline())

        client_file.close()

    server.shutdown()

    assert response == {
        "status": "error",
        "message": "Unknown action: invalid",
    }

def test_server_returns_error_for_malformed_json(tmp_path):
    db_path = tmp_path / "test.db"

    database = Database(db_path)
    database.initialize()
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

        client_file.write("{not valid json}\n")
        client_file.flush()

        response = json.loads(client_file.readline())

        client_file.close()

    server.shutdown()

    assert response["status"] == "error"

def test_server_continues_after_malformed_request(tmp_path):
    db_path = tmp_path / "test.db"

    database = Database(db_path)
    database.initialize()
    database.insert_lines(["test line"])
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

        client_file.write("{not valid json}\n")
        client_file.flush()

        error_response = json.loads(client_file.readline())

        client_file.write(
            json.dumps({
                "action": "sample",
                "count": 1,
            }) + "\n"
        )
        client_file.flush()

        success_response = json.loads(client_file.readline())

        client_file.close()

    server.shutdown()

    assert error_response == {
        "status": "error",
        "message": "Invalid JSON",
    }

    assert success_response == {
        "status": "ok",
        "lines": ["test line"],
    }