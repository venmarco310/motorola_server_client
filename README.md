# motorola_server_client
# Text Server / Client

A concurrent text sampling service built in Python.

The server maintains a persistent pool of text lines. Clients can load text files into the pool and request random samples. Once a line is returned to a client, it is permanently removed from the pool and cannot be returned again.

## Features

* Load text files into a persistent SQLite-backed cache
* Stream files line-by-line to support files larger than available RAM
* Sample random lines from the cache
* Sampled lines are permanently consumed
* Multiple clients can connect concurrently
* Thread-safe sampling across concurrent clients
* Persistent TCP connections supporting multiple requests
* Newline-delimited JSON (NDJSON) request/response protocol
* UTF-8 text with Latin-1 fallback
* Automated unit, integration, and concurrency tests

## Architecture

```text
                    ┌──────────────────┐
                    │     Client 1     │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │     Client 2     │
                    └────────┬─────────┘
                             │
                           TCP
                             │
                    ┌────────▼─────────┐
                    │      Server      │
                    │                  │
                    │ Thread per       │
                    │ client           │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │   TextSampler    │
                    │                  │
                    │ load() / sample()│
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │     Database     │
                    │                  │
                    │ SQLite           │
                    └──────────────────┘
```

### Components

**`TextServer`**

Handles TCP connections and request/response processing. Each connected client is handled by a separate thread.

**`TextClient`**

Provides a simple Python interface for connecting to the server and calling `load()` and `sample()`.

**`TextSampler`**

Contains the application-level behavior for loading files and sampling lines.

**`Database`**

Provides SQLite persistence and atomic line sampling/consumption.

## Requirements

* Python 3.12+
* SQLite (included with Python)
* pytest for running tests

## Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the project:

```powershell
python -m pip install -e .
```

Install test dependencies:

```powershell
python -m pip install -e ".[test]"
```

## Running the Tests

Run the complete test suite:

```powershell
pytest
```

The test suite covers:

* Database operations
* File loading
* Sampling and consumption behavior
* Duplicate content
* Concurrent database sampling
* TCP server request handling
* Persistent client connections
* Client/server error handling
* Concurrent clients

## Run with Real Data

The implementation was tested with the [Cornell Movie-Dialogs Corpus](https://www.cs.cornell.edu/~cristian/Cornell_Movie-Dialogs_Corpus.html).

### Cornell Movie-Quotes Corpus

Download and extract the dataset. Place the extracted `cornell_movie_quotes_corpus` directory in the project root:

```text
motorola_server_client/
├── cornell_movie_quotes_corpus/
├── manual_test.py
├── generate_numbers_txt.py
├── src/
├── tests/
└── README.md
```

With the Python virtual environment activated, run:

```powershell
python .\manual_test.py
```

This script:

* Loads the `moviequotes.scripts.txt` dataset into the server.
* Reports the number of lines loaded and the load time.
* Samples lines from the dataset.
* Performs a second sample to verify that previously sampled lines are consumed and not returned again.

The dataset contains approximately **894,000 lines** and is approximately **126 MB**.

### Large Synthetic Dataset

A second manual test can be performed using `generate_numbers_txt.py`. This script generates a text file containing a configurable number of lines.

The number of generated lines can be adjusted in the script. The implementation has been manually tested with files containing up to **15 million lines**.

Generate the test file:

```powershell
python .\generate_numbers_txt.py
```

This creates a new text file in the project directory.

Next, open `manual_test.py` and update the file path on line 9 to point to the generated file.

Then run:

```powershell
python .\manual_test.py
```

This provides a simple way to test loading and sampling behavior with substantially larger datasets.


## Using the Server

The server can be started from Python:

```python
import threading

from text_server.server import TextServer


server = TextServer(
    database_path="text_server.db",
    host="127.0.0.1",
    port=5000,
)

server.start()

server_thread = threading.Thread(
    target=server.serve_forever,
    daemon=True,
)

server_thread.start()
```

The server listens for TCP connections and supports multiple clients concurrently.

## Using the Client

Create a client and connect to the server:

```python
from text_server.client import TextClient


client = TextClient(
    host="127.0.0.1",
    port=5000,
)

client.connect()

try:
    loaded = client.load("example.txt")
    print(f"Loaded {loaded} lines")

    lines = client.sample(10)

    for line in lines:
        print(line)
finally:
    client.close()
```

Multiple requests can be made over the same connection:

```python
client.connect()

try:
    client.load("example.txt")

    first_sample = client.sample(10)
    second_sample = client.sample(10)
finally:
    client.close()
```

## Protocol

The client and server communicate using newline-delimited JSON over TCP.

### Load

Request:

```json
{"action":"load","path":"example.txt"}
```

Response:

```json
{"status":"ok","count":100}
```

### Sample

Request:

```json
{"action":"sample","count":10}
```

Response:

```json
{
  "status": "ok",
  "lines": [
    "first sampled line",
    "second sampled line"
  ]
}
```

If fewer lines are available than requested, the server returns all remaining lines.

If no lines are available, the server returns an empty list.

## Concurrency and Thread Safety

The server creates a separate handler thread for each connected client.

Each client handler creates its own SQLite database connection. This avoids sharing a SQLite connection across threads.

Sampling is performed as an atomic database operation:

1. Begin an immediate transaction.
2. Select random rows.
3. Delete the selected rows.
4. Commit the transaction.
5. Return the selected lines.

This prevents two concurrent clients from consuming the same database rows.

The test suite includes a concurrency test with 10 clients sampling simultaneously and verifies that every returned line is unique.

## Large Files

Files are processed incrementally rather than read entirely into memory.

During `load()`, the file is:

1. Read line-by-line.
2. Grouped into batches of 1,000 lines.
3. Inserted into SQLite.
4. Cleared from memory before processing the next batch.

This keeps application memory usage relatively constant as file size increases.

For example, a file larger than available RAM can still be processed because the application does not create an in-memory representation of the entire file.

## Text Encoding

The loader first attempts to read the file as UTF-8.

If the file is not valid UTF-8, it falls back to Latin-1.

This supports modern UTF-8 text files while also handling legacy Western-European text files such as the Cornell Movie-Quotes corpus used during manual testing.

The loader does not use `errors="ignore"` or silently discard invalid characters.

## Design Decisions

### SQLite

SQLite was chosen because the assignment requires persistent shared state, while the server and clients run on the same host.

It provides:

* Persistent storage
* Transaction support
* Atomic updates
* Multiple connections
* No external database service
* Standard-library support through Python's `sqlite3` module

The database also means the entire line cache does not need to remain in RAM.

### TCP

TCP provides a reliable, ordered byte stream and works naturally with the request/response model.

The implementation uses a persistent TCP connection so a client can send multiple requests without reconnecting.

UDP was not used because it would require additional handling for reliability, ordering, and retransmission.

### NDJSON

Newline-delimited JSON provides simple message framing over the TCP byte stream.

Each request and response occupies one line, allowing the server to process multiple requests on the same connection without introducing a more complicated protocol.

### Random Sampling

The current implementation uses SQLite's:

```sql
ORDER BY RANDOM()
```

This keeps the implementation straightforward and provides random sampling while maintaining the required consume-on-read behavior.

For extremely large datasets, this approach can become expensive because SQLite may need to process many rows to produce a random ordering. A production implementation at very large scale could use a different sampling strategy, such as maintaining additional metadata or selecting from randomly generated row identifiers.

### Thread-per-Client

A thread-per-client model keeps the implementation simple and is appropriate for the assignment's requirement to support several concurrent clients.

For a system expected to handle thousands of simultaneous connections, an asynchronous/event-driven architecture or worker pool would be more appropriate.

## Project Structure

```text
motorola_server_client/
├── src/
│   └── text_server/
│       ├── __init__.py
│       ├── client.py
│       ├── database.py
│       ├── sampler.py
│       └── server.py
├── tests/
│   ├── __init__.py
│   ├── test_client.py
│   ├── test_database.py
│   ├── test_sampler.py
│   └── test_server.py
├── .gitignore
├── pyproject.toml
└── README.md
```

## Limitations / Future Improvements

The implementation intentionally favors simplicity and correctness for the assignment.

Potential improvements for a production-scale implementation include:

* More efficient random sampling for very large SQLite tables
* Connection pooling or a different storage engine for higher concurrency
* Graceful management of client handler threads during shutdown
* Configurable batch sizes
* More comprehensive encoding detection
* Authentication and authorization if exposed beyond localhost
* Metrics for load and sampling throughput
* A command-line interface for starting the server and interacting with it

