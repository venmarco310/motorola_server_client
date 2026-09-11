from text_sampler.database import Database


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