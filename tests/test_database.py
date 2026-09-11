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

    rows = db._connection.execute(
        "SELECT content FROM lines ORDER BY id"
    ).fetchall()

    db.close()

    assert rows == [
        ("first line",),
        ("second line",),
        ("third line",),
    ]