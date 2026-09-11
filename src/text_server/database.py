import sqlite3
from pathlib import Path


class Database:
    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._connection = sqlite3.connect(self._db_path)

    def initialize(self) -> None:
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS lines (
                id INTEGER PRIMARY KEY,
                content TEXT NOT NULL
            )
            """
        )
        self._connection.commit()

    def insert_line(self, content: str) -> None:
        self._connection.execute(
            "INSERT INTO lines (content) VALUES (?)",
            (content,),
        )
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()