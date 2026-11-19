"""Durability facilities for an app-owned, local, path-backed filesystem."""

import os
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO, IO, Protocol


class StorageFiles(Protocol):
    def sync(self, stream: IO) -> None: ...
    def sync_directory(self, folder: Path) -> None: ...
    def replace(self, staged: Path, target: Path) -> None: ...
    def free_bytes(self, folder: Path) -> int: ...
    def temporary_file(self, folder: Path) -> BinaryIO: ...
    def temporary_path(self, folder: Path, *, prefix: str, suffix: str) -> Path: ...


class LocalFiles:
    """Standard Python implementation for an fsync-capable local filesystem."""

    def sync(self, stream):
        stream.flush()
        os.fsync(stream.fileno())

    def sync_directory(self, folder):
        descriptor = os.open(folder, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def replace(self, staged, target):
        # Staging and target must be on the same filesystem.
        os.replace(staged, target)

    def free_bytes(self, folder):
        return shutil.disk_usage(folder).free

    def temporary_file(self, folder):
        return tempfile.TemporaryFile(dir=folder)

    def temporary_path(self, folder, *, prefix, suffix):
        descriptor, name = tempfile.mkstemp(dir=folder, prefix=prefix, suffix=suffix)
        os.close(descriptor)
        return Path(name)


LOCAL_FILES = LocalFiles()


@contextmanager
def staging_path(
    files: StorageFiles, target: Path, *, suffix: str = ".tmp",
) -> Iterator[Path]:
    """Reserve a unique adjacent path and clean it up after publication/failure."""
    staged = files.temporary_path(target.parent, prefix=f".{target.stem}-", suffix=suffix)
    try:
        yield staged
    finally:
        staged.unlink(missing_ok=True)
