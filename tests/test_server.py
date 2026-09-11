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

def test_server_returns_error_when_sample_count_is_missing(tmp_path):
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
            "action": "sample",
        }

        client_file.write(json.dumps(request) + "\n")
        client_file.flush()

        response = json.loads(client_file.readline())

        client_file.close()

    server.shutdown()

    assert response == {
        "status": "error",
        "message": "Missing field: count",
    }

def test_server_returns_error_when_load_path_is_missing(tmp_path):
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
            "action": "load",
        }

        client_file.write(json.dumps(request) + "\n")
        client_file.flush()

        response = json.loads(client_file.readline())

        client_file.close()

    server.shutdown()

    assert response == {
        "status": "error",
        "message": "Missing field: path",
    }

def test_server_returns_error_for_invalid_sample_count(tmp_path):
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
            "action": "sample",
            "count": "five",
        }

        client_file.write(json.dumps(request) + "\n")
        client_file.flush()

        response = json.loads(client_file.readline())

        client_file.close()

    server.shutdown()

    assert response == {
        "status": "error",
        "message": "count must be a non-negative integer",
    }

def test_server_returns_error_for_negative_sample_count(tmp_path):
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
            "action": "sample",
            "count": -1,
        }

        client_file.write(json.dumps(request) + "\n")
        client_file.flush()

        response = json.loads(client_file.readline())

        client_file.close()

    server.shutdown()

    assert response == {
        "status": "error",
        "message": "count must be a non-negative integer",
    }

def test_server_stops_after_shutdown(tmp_path):
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
    )
    server_thread.start()

    server.shutdown()

    server_thread.join(timeout=1)

    assert not server_thread.is_alive()

def test_server_loads_and_samples_file(tmp_path):
    db_path = tmp_path / "test.db"
    input_path = tmp_path / "input.txt"

    input_path.write_text(
        "first line\n"
        "second line\n"
        "third line\n",
        encoding="utf-8",
    )

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

        load_request = {
            "action": "load",
            "path": str(input_path),
        }

        client_file.write(json.dumps(load_request) + "\n")
        client_file.flush()

        load_response = json.loads(client_file.readline())

        sample_request = {
            "action": "sample",
            "count": 2,
        }

        client_file.write(json.dumps(sample_request) + "\n")
        client_file.flush()

        sample_response = json.loads(client_file.readline())

        client_file.close()

    server.shutdown()

    assert load_response == {
        "status": "ok",
        "count": 3,
    }

    assert sample_response["status"] == "ok"
    assert len(sample_response["lines"]) == 2
    assert set(sample_response["lines"]).issubset(
        {
            "first line",
            "second line",
            "third line",
        }
    )

def test_server_returns_error_for_non_object_json(tmp_path):
    db_path = tmp_path / "test.db"

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

    try:
        with socket.create_connection((host, port)) as client:
            client.sendall(b'["sample", 10]\n')

            response = client.makefile(
                "r",
                encoding="utf-8",
            ).readline()

            response = json.loads(response)

            assert response == {
                "status": "error",
                "message": "Request must be a JSON object",
            }
    finally:
        server.shutdown()
        server_thread.join(timeout=1)


def test_server_returns_error_when_file_does_not_exist(tmp_path):
    db_path = tmp_path / "test.db"

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

    try:
        with socket.create_connection((host, port)) as client:
            request = {
                "action": "load",
                "path": str(tmp_path / "does_not_exist.txt"),
            }

            client.sendall(
                (json.dumps(request) + "\n").encode("utf-8")
            )

            response = client.makefile(
                "r",
                encoding="utf-8",
            ).readline()

            response = json.loads(response)

            assert response == {
                "status": "error",
                "message": "File not found",
            }
    finally:
        server.shutdown()
        server_thread.join(timeout=1)