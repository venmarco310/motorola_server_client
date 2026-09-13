import logging
from pathlib import Path

from text_server.database import Database


logger = logging.getLogger(__name__)


class TextSampler:
    def __init__(self, database: Database) -> None:
        self._database = database

    @staticmethod
    def _detect_encoding(file_path: Path) -> str:
        try:
            with file_path.open("r", encoding="utf-8") as file:
                for _ in file:
                    pass

            return "utf-8"

        except UnicodeDecodeError:
            return "latin-1"

    def load(self, file_path: str | Path) -> int:
        file_path = Path(file_path)
        encoding = self._detect_encoding(file_path)

        logger.info(
            "Loading file: %s using encoding %s",
            file_path,
            encoding,
        )

        line_count = 0
        batch = []
        batch_size = 1000

        with file_path.open("r", encoding=encoding) as file:
            for line in file:
                batch.append(line.rstrip("\r\n"))
                line_count += 1

                if len(batch) >= batch_size:
                    self._database.insert_lines(batch)
                    batch.clear()

        if batch:
            self._database.insert_lines(batch)

        logger.info(
            "Loaded %d lines from %s",
            line_count,
            file_path,
        )

        return line_count

    def sample(self, count: int) -> list[str]:
        sampled = self._database.sample_lines(count)

        logger.info(
            "Sampled %d lines (requested %d)",
            len(sampled),
            count,
        )

        return sampled