import vpk
from pathlib import Path
from tempfile import NamedTemporaryFile

class File:
    input_root: Path
    path: Path

    def __init__(self, input_root: Path, path: Path):
        self.input_root = input_root
        self.path = path

    @property
    def is_real(self):
        return True

    # Maybe rename this... Files in vpks won't have paths that correspond to real paths on the system.
    def obtain_real_file_path(self) -> Path:
        return self.path

class VPKFile(File):
    input_root = Path("/")

    # Oof, type name conflicts. Oh well
    file: vpk.VPKFile
    def __init__(self, file: vpk.VPKFile, path: Path):
        self.file = file
        self.path = self.input_root.joinpath(path)
        self.backing_file = None

    @property
    def is_real(self):
        return False

    def obtain_real_file_path(self) -> Path:
        if self.backing_file is not None:
            return Path(self.backing_file.name)

        self.backing_file = NamedTemporaryFile("w+b", suffix=self.path.suffix, prefix=self.path.stem)
        
        self.backing_file.truncate(self.file.length)

        for chunk in iter(lambda: self.file.read(8192), b''):
            self.backing_file.write(chunk)

        self.backing_file.flush()

        return Path(self.backing_file.name)

