from pathlib import Path

from text_server.database import Database


class TextSampler:
    def __init__(self, database: Database) -> None:
        self._database = database

    def load(self, file_path: str | Path) -> int:
        file_path = Path(file_path)
        line_count = 0

        with file_path.open("r", encoding="utf-8") as file:
            for line in file:
                content = line.rstrip("\r\n")
                self._database.insert_line(content)
                line_count += 1

        return line_count