from __future__ import annotations

import httpx


class HttpPutUploader:
    """Upload media using a signed PUT URL template."""

    def __init__(self, upload_url_template: str, timeout: float = 300):
        if "{name}" not in upload_url_template:
            raise ValueError("Upload URL template must contain {name}")
        self.upload_url_template = upload_url_template
        self.timeout = timeout

    def upload(self, source, destination_name: str) -> str:
        from pathlib import Path

        source = Path(source)
        safe_name = destination_name.replace("/", "-")
        url = self.upload_url_template.format(name=safe_name)
        with source.open("rb") as media, httpx.Client(timeout=self.timeout) as client:
            response = client.put(
                url,
                content=media,
                headers={
                    "Content-Type": "application/octet-stream",
                    "Content-Disposition": f'attachment; filename="{safe_name}"',
                },
            )
            response.raise_for_status()
        return url
