import threading

from text_server.database import Database


def test_database_creates_lines_table(tmp_path):
    db_path = tmp_path / "test.db"

    db = Database(db_path)
    db.initialize()

    result = db._connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name = 'lines'
        """
    ).fetchone()

    db.close()

    assert result is not None


def test_insert_lines(tmp_path):
    db_path = tmp_path / "test.db"

    db = Database(db_path)
    db.initialize()

    db.insert_lines([
        "first line",
        "second line",
        "third line",
    ])

    assert db.count_lines() == 3

    db.close()


def test_sample_lines_removes_sampled_lines(tmp_path):
    db_path = tmp_path / "test.db"

    db = Database(db_path)
    db.initialize()

    db.insert_lines([
        "first line",
        "second line",
        "third line",
    ])

    sampled = db.sample_lines(2)

    assert len(sampled) == 2
    assert db.count_lines() == 1

    db.close()


def test_sample_lines_returns_all_available_when_request_is_too_large(tmp_path):
    db_path = tmp_path / "test.db"

    db = Database(db_path)
    db.initialize()

    db.insert_lines([
        "first line",
        "second line",
    ])

    sampled = db.sample_lines(10)

    assert len(sampled) == 2
    assert db.count_lines() == 0

    db.close()


def test_sample_lines_returns_empty_when_database_is_empty(tmp_path):
    db_path = tmp_path / "test.db"

    db = Database(db_path)
    db.initialize()

    sampled = db.sample_lines(10)

    assert sampled == []
    assert db.count_lines() == 0

    db.close()


def test_sample_lines_handles_duplicate_content(tmp_path):
    db_path = tmp_path / "test.db"

    db = Database(db_path)
    db.initialize()

    db.insert_lines([
        "hello",
        "hello",
        "world",
    ])

    sampled = db.sample_lines(2)

    assert len(sampled) == 2
    assert db.count_lines() == 1

    db.close()

def test_concurrent_sampling_does_not_return_duplicate_rows(tmp_path):
    db_path = tmp_path / "test.db"

    setup_database = Database(db_path)
    setup_database.initialize()

    lines = [f"line {i}" for i in range(100)]
    setup_database.insert_lines(lines)
    setup_database.close()

    results = []

    def sample_lines():
        database = Database(db_path)
        database.initialize()

        sampled = database.sample_lines(50)
        results.append(sampled)

        database.close()

    thread1 = threading.Thread(target=sample_lines)
    thread2 = threading.Thread(target=sample_lines)

    thread1.start()
    thread2.start()

    thread1.join()
    thread2.join()

    sampled_lines = results[0] + results[1]

    assert len(sampled_lines) == 100
    assert len(set(sampled_lines)) == 100

    verification_database = Database(db_path)
    verification_database.initialize()

    assert verification_database.count_lines() == 0

    verification_database.close()