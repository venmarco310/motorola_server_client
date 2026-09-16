import threading
import time

from text_server.client import TextClient
from text_server.server import TextServer


DATABASE_PATH = "concurrency_test.db"
FILE_PATH = r"cornell_movie_quotes_corpus\numbers.txt"

CLIENT_COUNT = 1
SAMPLE_SIZE = 10


server = TextServer(
    database_path=DATABASE_PATH,
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

barrier = threading.Barrier(CLIENT_COUNT)

results = []
errors = []

results_lock = threading.Lock()


def sample_with_client(client_number):
    client = TextClient(
        host=host,
        port=port,
    )

    try:
        client.connect()

        print(f"Client {client_number}: connected")

        # Wait until all clients are connected.
        barrier.wait()

        print(f"Client {client_number}: sampling")

        start_time = time.perf_counter()

        sampled = client.sample(SAMPLE_SIZE)

        elapsed = time.perf_counter() - start_time

        with results_lock:
            results.append(sampled)

        print(
            f"Client {client_number}: "
            f"received {len(sampled)} lines "
            f"in {elapsed:.2f}s"
        )

    except Exception as exc:
        with results_lock:
            errors.append((client_number, exc))

        print(
            f"Client {client_number}: ERROR: {exc}"
        )

    finally:
        client.close()


try:
    print(f"Server running at {host}:{port}")
    print(f"Loading: {FILE_PATH}")
    print()

    loader = TextClient(
        host=host,
        port=port,
    )

    try:
        loader.connect()

        start_time = time.perf_counter()

        loaded_count = loader.load(FILE_PATH)

        load_time = time.perf_counter() - start_time

        print(
            f"Loaded {loaded_count:,} lines "
            f"in {load_time:.2f}s"
        )

    finally:
        loader.close()

    print()
    print(
        f"Starting {CLIENT_COUNT} concurrent clients..."
    )
    print()

    threads = [
        threading.Thread(
            target=sample_with_client,
            args=(i,),
        )
        for i in range(1, CLIENT_COUNT + 1)
    ]

    start_time = time.perf_counter()

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join(timeout=60)

    total_time = time.perf_counter() - start_time

    print()
    print("========== RESULTS ==========")

    print(f"Total time: {total_time:.2f}s")
    print(f"Successful clients: {len(results)}")
    print(f"Errors: {len(errors)}")

    sampled_lines = [
        line
        for result in results
        for line in result
    ]

    print(f"Total sampled lines: {len(sampled_lines)}")
    print(f"Unique sampled lines: {len(set(sampled_lines))}")

    if errors:
        print()
        print("Errors:")

        for client_number, error in errors:
            print(
                f"  Client {client_number}: "
                f"{type(error).__name__}: {error}"
            )

    print()

    if (
        not errors
        and len(results) == CLIENT_COUNT
        and len(sampled_lines) == CLIENT_COUNT * SAMPLE_SIZE
        and len(set(sampled_lines)) == len(sampled_lines)
    ):
        print("PASS: all clients completed successfully.")
        print("PASS: no duplicate lines were sampled.")
    else:
        print("FAIL: concurrency test did not pass.")

finally:
    server.shutdown()
    server_thread.join(timeout=1)