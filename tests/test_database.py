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