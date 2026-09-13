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

def test_two_clients_sample_concurrently_without_duplicate_lines(tmp_path):
    file_path = tmp_path / "sample.txt"

    lines = [f"line {i}" for i in range(100)]
    file_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    server, server_thread = start_server(tmp_path)

    host, port = server.address

    client1 = TextClient(host, port)
    client2 = TextClient(host, port)

    barrier = threading.Barrier(2)
    results = []

    def sample_with_client(client):
        client.connect()

        try:
            barrier.wait()

            sampled = client.sample(50)
            results.append(sampled)
        finally:
            client.close()

    thread1 = threading.Thread(
        target=sample_with_client,
        args=(client1,),
    )

    thread2 = threading.Thread(
        target=sample_with_client,
        args=(client2,),
    )

    try:
        # Load the data before starting the concurrent sampling.
        loader = TextClient(host, port)

        try:
            loader.connect()
            assert loader.load(file_path) == 100
        finally:
            loader.close()

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        sampled_lines = results[0] + results[1]

        assert len(sampled_lines) == 100
        assert len(set(sampled_lines)) == 100

    finally:
        server.shutdown()
        server_thread.join(timeout=1)

def test_ten_clients_sample_concurrently_without_duplicate_lines(tmp_path):
    file_path = tmp_path / "sample.txt"

    lines = [f"line {i}" for i in range(100)]
    file_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    server, server_thread = start_server(tmp_path)

    host, port = server.address

    barrier = threading.Barrier(10)
    results = []
    results_lock = threading.Lock()

    def sample_with_client():
        client = TextClient(host, port)

        try:
            client.connect()

            barrier.wait()

            sampled = client.sample(10)

            with results_lock:
                results.append(sampled)

        finally:
            client.close()

    threads = [
        threading.Thread(target=sample_with_client)
        for _ in range(10)
    ]

    try:
        loader = TextClient(host, port)

        try:
            loader.connect()
            assert loader.load(file_path) == 100
        finally:
            loader.close()

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        sampled_lines = [
            line
            for result in results
            for line in result
        ]

        assert len(sampled_lines) == 100
        assert len(set(sampled_lines)) == 100

    finally:
        server.shutdown()
        server_thread.join(timeout=1)
