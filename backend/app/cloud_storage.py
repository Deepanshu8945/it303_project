"""Private Supabase object storage; credentials never leave the backend."""

from dataclasses import dataclass
from datetime import datetime
from urllib.parse import quote

import httpx

from .config import settings


def request(method, path, **kwargs):
    config = settings()
    headers = {
        "apikey": config.supabase_service_role_key,
        "Authorization": "Bearer " + config.supabase_service_role_key,
        **kwargs.pop("headers", {}),
    }
    return httpx.request(
        method,
        config.supabase_url.rstrip("/") + "/storage/v1/" + path,
        headers=headers,
        timeout=30,
        **kwargs,
    )


def bucket_path():
    return quote(settings().supabase_storage_bucket, safe="")


def validate_bucket():
    response = request("GET", "bucket/" + bucket_path())
    response.raise_for_status()
    if response.json().get("public", True):
        raise RuntimeError("The converter storage bucket must be private.")


@dataclass(frozen=True)
class CloudFile:
    name: str

    @property
    def object_path(self):
        return "object/" + bucket_path() + "/" + quote(self.name, safe="")

    def exists(self):
        response = request("HEAD", self.object_path)
        if response.status_code == 404:
            return False
        response.raise_for_status()
        return True

    def read_bytes(self):
        response = request("GET", self.object_path)
        response.raise_for_status()
        return response.content

    def write_bytes(self, content):
        response = request(
            "POST",
            self.object_path,
            content=content,
            headers={"Content-Type": "application/octet-stream", "x-upsert": "true"},
        )
        response.raise_for_status()

    def unlink(self, missing_ok=False):
        response = request("DELETE", "object/" + bucket_path(), json={"prefixes": [self.name]})
        if missing_ok and response.status_code == 404:
            return
        response.raise_for_status()


def remove_orphans(valid_ids, current_time):
    # Finish pagination before deleting: removing entries would shift later offsets.
    orphan_names, offset = [], 0
    while True:
        response = request(
            "POST",
            "object/list/" + bucket_path(),
            json={
                "prefix": "",
                "limit": 100,
                "offset": offset,
                "sortBy": {"column": "name", "order": "asc"},
            },
        )
        response.raise_for_status()
        items = response.json()
        for item in items:
            name = item["name"]
            if name.split(".")[0] in valid_ids or not item.get("created_at"):
                continue
            created = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
            if (current_time - created).total_seconds() > 60:
                orphan_names.append(name)
        if len(items) < 100:
            break
        offset += 100
    for start in range(0, len(orphan_names), 100):
        response = request(
            "DELETE",
            "object/" + bucket_path(),
            json={"prefixes": orphan_names[start : start + 100]},
        )
        response.raise_for_status()
