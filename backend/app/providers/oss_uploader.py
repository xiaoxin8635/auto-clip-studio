from __future__ import annotations

from pathlib import Path

import oss2


class OssSignerUploader:
    """Upload media through Aliyun OSS and return a temporary download URL."""

    def __init__(
        self,
        bucket: str,
        endpoint: str,
        access_key_id: str,
        access_key_secret: str,
        expires_in_seconds: int = 3600,
        timeout: int | None = None,
    ):
        if not bucket or not endpoint or not access_key_id or not access_key_secret:
            raise ValueError("OSS uploader requires bucket, endpoint, access key id, and secret")
        auth = oss2.Auth(access_key_id, access_key_secret)
        normalized_endpoint = endpoint.removeprefix("https://").removesuffix("/")
        if not normalized_endpoint.startswith("http://") and not normalized_endpoint.startswith("https://"):
            normalized_endpoint = f"https://{normalized_endpoint}"
        self.bucket_client = oss2.Bucket(auth, normalized_endpoint, bucket, connect_timeout=timeout)
        self.expires_in_seconds = expires_in_seconds

    def upload(self, source: Path, destination_name: str) -> str:
        object_key = destination_name.replace("\\", "/").strip("/")
        if not object_key:
            raise ValueError("OSS object key cannot be empty")
        self.bucket_client.put_object_from_file(
            object_key,
            source,
            headers={"Content-Type": "application/octet-stream"},
        )
        return self.bucket_client.sign_url(
            "GET",
            object_key,
            self.expires_in_seconds,
            slash_safe=True,
        )

    def delete(self, destination_name: str) -> None:
        object_key = destination_name.replace("\\", "/").strip("/")
        if not object_key:
            raise ValueError("OSS object key cannot be empty")
        self.bucket_client.delete_object(object_key)
