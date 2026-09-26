import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import get_settings


@dataclass
class Upload:
    data: bytes
    content_type: str
    filename: str

    @property
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
    """Write bytes under their SHA-256. Idempotent: same bytes, same file."""
    sha = upload.sha256
    path = media_path(sha)
    if path.exists():
        return sha
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write to a temp file in the same directory, then rename atomically,
    # so a crash never leaves a half-written file under the final name.
    fd, tmp = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(upload.data)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return sha
