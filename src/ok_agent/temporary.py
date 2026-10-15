import tempfile
from pathlib import Path


class Temporary:
    def __init__(self):
        self._temp_files: list[Path] = []

    def create_temp_file(self) -> Path:
        with tempfile.NamedTemporaryFile(delete=False) as temp:
            temp_file = Path(temp.name)
            self._temp_files.append(temp_file)
            return temp_file

    def remove_temp_files(self) -> None:
        for file in self._temp_files:
            file.unlink(missing_ok=True)

        self._temp_files.clear()


temporary = Temporary()
