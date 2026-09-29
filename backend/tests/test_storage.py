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


def test_truncated_media_file_is_rewritten():
    upload = Upload(data=b"the complete recording bytes", content_type="audio/webm", filename="a.webm")
    path = media_path(upload.sha256)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"the compl")  # e.g. left behind by a crash

    write_media(upload)
    assert path.read_bytes() == b"the complete recording bytes"


def test_sha256_is_computed_once():
    upload = Upload(data=b"x" * 10, content_type="audio/webm", filename="a")
    assert upload.sha256 is upload.sha256
