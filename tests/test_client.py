import threading

import pytest

from text_server.client import ServerError, TextClient
from text_server.server import TextServer


def start_server(tmp_path):
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

    return server, server_thread


def test_client_loads_and_samples_file(tmp_path):
    file_path = tmp_path / "sample.txt"

    file_path.write_text(
        "first line\n"
        "second line\n"
        "third line\n",
        encoding="utf-8",
    )

    server, server_thread = start_server(tmp_path)

    host, port = server.address
    client = TextClient(host, port)

    try:
        client.connect()

        loaded_count = client.load(file_path)
        sampled_lines = client.sample(2)

        assert loaded_count == 3
        assert len(sampled_lines) == 2
        assert all(
            line in {
                "first line",
                "second line",
                "third line",
            }
            for line in sampled_lines
        )
    finally:
        client.close()
        server.shutdown()
        server_thread.join(timeout=1)


def test_client_supports_multiple_requests_on_same_connection(tmp_path):
    file_path = tmp_path / "sample.txt"

    file_path.write_text(
        "first line\n"
        "second line\n"
        "third line\n",
        encoding="utf-8",
    )

    server, server_thread = start_server(tmp_path)

    host, port = server.address
    client = TextClient(host, port)

    try:
        client.connect()

        assert client.load(file_path) == 3

        first_sample = client.sample(1)
        second_sample = client.sample(1)
        third_sample = client.sample(1)

        sampled_lines = (
            first_sample
            + second_sample
            + third_sample
        )

        assert len(sampled_lines) == 3
        assert len(set(sampled_lines)) == 3
    finally:
        client.close()
        server.shutdown()
        server_thread.join(timeout=1)


def test_client_raises_server_error(tmp_path):
    server, server_thread = start_server(tmp_path)

    host, port = server.address
    client = TextClient(host, port)

    try:
        client.connect()

        with pytest.raises(ServerError, match="Unknown action"):
            client._request({"action": "invalid"})
    finally:
        client.close()
        server.shutdown()
        server_thread.join(timeout=1)


def test_client_rejects_invalid_sample_count(tmp_path):
    server, server_thread = start_server(tmp_path)

    host, port = server.address
    client = TextClient(host, port)

    try:
        client.connect()

        with pytest.raises(ValueError):
            client.sample(-1)

        with pytest.raises(ValueError):
            client.sample("five")
    finally:
        client.close()
        server.shutdown()
        server_thread.join(timeout=1)