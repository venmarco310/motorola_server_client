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

    assert line_count == 3
    assert database.count_lines() == 3

    database.close()


def test_sample_returns_requested_number_of_lines(tmp_path):
    db_path = tmp_path / "test.db"

    database = Database(db_path)
    database.initialize()

    sampler = TextSampler(database)

    database.insert_lines([
        "first line",
        "second line",
        "third line",
        "fourth line",
        "fifth line",
    ])

    sampled = sampler.sample(3)

    assert len(sampled) == 3

    database.close()


def test_sample_consumes_lines(tmp_path):
    db_path = tmp_path / "test.db"

    database = Database(db_path)
    database.initialize()

    sampler = TextSampler(database)

    database.insert_lines([
        "first line",
        "second line",
        "third line",
    ])

    first_sample = sampler.sample(2)
    second_sample = sampler.sample(2)

    database.close()

    assert len(first_sample) == 2
    assert len(second_sample) == 1