from text_server.database import Database
from text_server.sampler import TextSampler


def test_load_file(tmp_path):
    db_path = tmp_path / "test.db"
    file_path = tmp_path / "sample.txt"

    file_path.write_text(
        "first line\n"
        "second line\n"
        "third line\n",
        encoding="utf-8",
    )

    database = Database(db_path)
    database.initialize()

    sampler = TextSampler(database)

    line_count = sampler.load(file_path)

    rows = database._connection.execute(
        "SELECT content FROM lines ORDER BY id"
    ).fetchall()

    database.close()

    assert line_count == 3
    assert rows == [
        ("first line",),
        ("second line",),
        ("third line",),
    ]