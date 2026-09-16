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

    sampled_lines = client.sample(32767)

    print("\nSampled 32767 lines:\n")
    # for line in sampled_lines:
    #     print(f"  {line}")

    remaining_sample = client.sample(32767)

    print(
        f"\nSecond sample returned \n"
        f"{len(remaining_sample)} lines"
    )
    print(type(remaining_sample))

    # print("\nRemaining sample lines:\n")
    # for line in remaining_sample:
    #     print(f"  {line}")


    print("Sampled lines are the same?")
    common = set(sampled_lines) & set(remaining_sample)

    print(f"Overlap between samples: {len(common)}")

    if common:
        print("WARNING: duplicate lines were sampled")
    else:
        print("No duplicate lines were sampled")


finally:
    client.close()
    server.shutdown()
    server_thread.join(timeout=1)