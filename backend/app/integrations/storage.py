"""Private object storage behind one small interface.

Two backends:
- LocalStorage: files under IC_STORAGE_DIR (development and tests).
- S3Storage: an S3-compatible bucket (Neon Object Storage in the demo deployment).
  Use it wherever the server's disk is not permanent, e.g. Render's free plan.

Pick with IC_STORAGE_BACKEND=local|s3. For s3, set IC_S3_BUCKET plus the standard AWS
variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_ENDPOINT_URL_S3, AWS_REGION),
which `neon env pull` writes; settings read them from the environment or .env.
Objects are never public: the API reads them and streams them to signed-in users.
"""

from functools import lru_cache
from pathlib import Path
from typing import Protocol

from app.config.settings import get_settings


class Storage(Protocol):
    def put(self, key: str, data: bytes) -> None: ...
    def get(self, key: str) -> bytes: ...  # raises FileNotFoundError for a missing key
    def delete(self, key: str) -> None: ...


class LocalStorage:
    def __init__(self, root: str):
        self.root = Path(root).resolve()

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("storage key escapes the storage root")
        return path

    def put(self, key: str, data: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)


class S3Storage:
    def __init__(self, bucket: str, client=None):
        if client is None:
            import boto3
            from botocore.config import Config

            settings = get_settings()
            # Neon (and most S3-compatible services) need path-style addressing and SigV4.
            client = boto3.client(
                "s3",
                endpoint_url=settings.s3_endpoint_url or None,
                region_name=settings.s3_region or None,
                aws_access_key_id=settings.s3_access_key_id or None,
                aws_secret_access_key=settings.s3_secret_access_key or None,
                config=Config(s3={"addressing_style": "path"}, signature_version="s3v4",
                              retries={"max_attempts": 3, "mode": "standard"}),
            )
        self.bucket = bucket
        self.client = client

    @staticmethod
    def _check(key: str) -> str:
        if not key or key.startswith("/") or ".." in key.split("/"):
            raise ValueError("invalid storage key")
        return key

    def put(self, key: str, data: bytes) -> None:
        self.client.put_object(Bucket=self.bucket, Key=self._check(key), Body=data)

    def get(self, key: str) -> bytes:
        from botocore.exceptions import ClientError

        try:
            response = self.client.get_object(Bucket=self.bucket, Key=self._check(key))
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("NoSuchKey", "404", "NotFound"):
                raise FileNotFoundError(key) from exc
            raise
        return response["Body"].read()

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=self._check(key))  # missing key: no error in S3


@lru_cache
def _s3(bucket: str) -> S3Storage:
    return S3Storage(bucket)  # one client per process; boto3 clients are thread-safe


def get_storage() -> Storage:
    settings = get_settings()
    if settings.storage_backend == "s3":
        if not settings.s3_bucket:
            raise RuntimeError("IC_S3_BUCKET must be set when IC_STORAGE_BACKEND=s3")
        return _s3(settings.s3_bucket)
    return LocalStorage(settings.storage_dir)
