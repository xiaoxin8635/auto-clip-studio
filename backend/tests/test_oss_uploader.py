from pathlib import Path

import pytest

from app.providers.oss_uploader import OssSignerUploader


def test_oss_uploader_rejects_incomplete_configuration():
    with pytest.raises(ValueError, match="requires"):
        OssSignerUploader("", "endpoint", "id", "secret")


def test_oss_uploader_builds_bucket_and_signs_download_url(tmp_path, monkeypatch):
    media = tmp_path / "video.mp4"
    media.write_bytes(b"media")
    captured = {}

    class FakeBucket:
        def __init__(self, auth, endpoint, bucket, **kwargs):
            captured["endpoint"] = endpoint
            captured["bucket"] = bucket

        def put_object_from_file(self, key, source, headers=None):
            captured["key"] = key
            captured["source"] = source
            captured["headers"] = headers

        def sign_url(self, method, key, expires, headers=None, slash_safe=False):
            captured["method"] = method
            captured["url_key"] = key
            return f"https://signed.test/{key}"

        def delete_object(self, key):
            captured["deleted_key"] = key

    monkeypatch.setattr("app.providers.oss_uploader.oss2.Bucket", FakeBucket)
    uploader = OssSignerUploader("bucket", "endpoint", "id", "secret", expires_in_seconds=60)

    download_url = uploader.upload(media, "video.mp4")

    assert captured["endpoint"] == "https://endpoint"
    assert captured["key"] == "video.mp4"
    assert captured["method"] == "GET"
    assert download_url == "https://signed.test/video.mp4"
    uploader.delete("video.mp4")
    assert captured["deleted_key"] == "video.mp4"
