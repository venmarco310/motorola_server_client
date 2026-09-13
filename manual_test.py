import threading
import time

from text_server.client import TextClient
from text_server.server import TextServer


DATABASE_PATH = "manual_test.db"
FILE_PATH = r"cornell_movie_quotes_corpus\moviequotes.scripts.txt"


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

client = TextClient(
    host=host,
    port=port,
)

try:
    print(f"Server running at {host}:{port}")
    print(f"Loading: {FILE_PATH}")

    start_time = time.perf_counter()

    client.connect()

    loaded_count = client.load(FILE_PATH)

    load_time = time.perf_counter() - start_time

    print(f"Loaded {loaded_count:,} lines")
    print(f"Load time: {load_time:.2f} seconds")

    sampled_lines = client.sample(10000)

    print("\nSampled 10000 lines:\n")
    # for line in sampled_lines:
    #     print(f"  {line}")

    remaining_sample = client.sample(10000)

    print(
        f"\nSecond sample returned \n"
        f"{len(remaining_sample)} lines"
    )
    print(type(remaining_sample))

    # print("\nRemaining sample lines:\n")
    # for line in remaining_sample:
    #     print(f"  {line}")


    print("Sampled lines are the same?")
    # print(remaining_sample == sampled_lines)
    common = list(set(sampled_lines) & set(remaining_sample))
    print(common)


finally:
    client.close()
    server.shutdown()
    server_thread.join(timeout=1)