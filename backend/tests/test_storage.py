import hashlib

from app.storage import Upload, media_path, write_media


def test_media_is_content_addressed_and_idempotent():
    upload = Upload(data=b"same bytes", content_type="audio/webm", filename="a.webm")

    sha = write_media(upload)
    assert sha == hashlib.sha256(b"same bytes").hexdigest()
    assert write_media(upload) == sha

    path = media_path(sha)
    assert path.read_bytes() == b"same bytes"
    assert [p.name for p in path.parent.iterdir()] == [sha]  # no temp files left behind
