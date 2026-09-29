import hashlib
import os
import tempfile
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import get_settings


@dataclass
class Upload:
    data: bytes
    content_type: str
    filename: str

    @cached_property
    def sha256(self) -> str:
        return hashlib.sha256(self.data).hexdigest()


def read_upload(file: UploadFile, max_bytes: int) -> Upload:
    """Read an upload fully, rejecting it with 413 if it is over max_bytes."""
    data = file.file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail=f"{file.filename} is larger than {max_bytes} bytes")
    return Upload(
        data=data,
        content_type=file.content_type or "application/octet-stream",
        filename=file.filename or "",
    )


def media_path(sha256: str) -> Path:
    return Path(get_settings().media_dir) / sha256[:2] / sha256


def write_media(upload: Upload) -> str:
    """Write bytes under their SHA-256, durably. Idempotent: same bytes, same file.

    An existing file is trusted only if its size matches; a truncated one (e.g. from a
    crash on a filesystem that reordered writes) is rewritten.
    """
    sha = upload.sha256
    path = media_path(sha)
    if path.exists() and path.stat().st_size == len(upload.data):
        return sha
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write to a temp file in the same directory, fsync it, then rename atomically and
    # fsync the directory, so after a crash the final name holds either nothing or all
    # the bytes, and the rename itself survives a power loss.
    fd, tmp = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(upload.data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    _fsync_dir(path.parent)
    return sha


def _fsync_dir(directory: Path) -> None:
    fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
