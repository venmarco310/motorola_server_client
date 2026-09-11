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

    def insert_lines(self, lines: list[str]) -> None:
        self._connection.executemany(
            "INSERT INTO lines (content) VALUES (?)",
            [(line,) for line in lines],
        )
        self._connection.commit()

    def sample_lines(self, count: int) -> list[str]:
        if count <= 0:
            return []

        cursor = self._connection.cursor()

        try:
            cursor.execute("BEGIN IMMEDIATE")

            rows = cursor.execute(
                """
                SELECT id, content
                FROM lines
                ORDER BY RANDOM()
                LIMIT ?
                """,
                (count,),
            ).fetchall()

            if rows:
                ids = [row[0] for row in rows]
                placeholders = ",".join("?" for _ in ids)

                cursor.execute(
                    f"DELETE FROM lines WHERE id IN ({placeholders})",
                    ids,
                )

            self._connection.commit()

            return [row[1] for row in rows]

        except Exception:
            self._connection.rollback()
            raise

    def count_lines(self) -> int:
        result = self._connection.execute(
            "SELECT COUNT(*) FROM lines"
        ).fetchone()

        return result[0]

    def close(self) -> None:
        self._connection.close()