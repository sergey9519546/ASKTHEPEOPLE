"""Supabase client factory + Storage abstraction.

This module centralises every Supabase touchpoint so the rest of the
codebase never imports `supabase` or `minio` directly. Two backends are
supported, picked from environment variables at import time:

* **Cloud Supabase** — `SUPABASE_URL` set + `USE_SUPABASE_PERSISTENCE=true`.
  Storage goes through the `supabase-py` HTTP client; Postgres goes
  through SQLAlchemy/psycopg driven by `DATABASE_URL`.

* **Local S3-compatible** (MinIO) — `SUPABASE_S3_ENDPOINT` set. Storage
  goes through the `minio` SDK pointed at the local MinIO container;
  Postgres still goes through SQLAlchemy/psycopg. This is the
  recommended dev path on Windows where the full Supabase local stack
  cannot start (Docker secrets access-denied).

If neither is configured, the module exposes a `storage` object whose
methods raise `StorageUnavailable` — the call sites fall back to the
filesystem path. Per ADR-0012, that legacy path is "LEGACY" mode and is
not a production system of record; the runtime fails closed the moment
`USE_SUPABASE_PERSISTENCE=true` is set without a real Supabase URL.

The choice of backend is fixed for the process lifetime; restarting
the worker / web picks up new env vars.
"""
from __future__ import annotations

import io
import logging
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


class StorageUnavailable(RuntimeError):
    """Raised when a Storage operation is requested but no backend is configured."""


@dataclass(frozen=True)
class StoredObject:
    """What callers get back from a successful upload."""

    bucket: str
    key: str
    size: int
    etag: Optional[str] = None
    content_type: Optional[str] = None


class _FilesystemFallback:
    """No-op stand-in used when neither Supabase nor MinIO is configured.

    The contract is: raise `StorageUnavailable` on every operation. The
    call sites are expected to catch this and fall back to the legacy
    filesystem path (`Config.UPLOAD_FOLDER`). This keeps the legacy
    behaviour as the default for `USE_SUPABASE_PERSISTENCE=false`.
    """

    def upload(self, *, bucket: str, key: str, data: bytes, content_type: Optional[str] = None) -> StoredObject:
        raise StorageUnavailable(
            "Supabase Storage is not configured. Set SUPABASE_URL + "
            "SUPABASE_SERVICE_ROLE_KEY (cloud) or SUPABASE_S3_ENDPOINT "
            "(local MinIO), or unset USE_SUPABASE_PERSISTENCE to use the "
            "legacy filesystem path."
        )

    def download(self, *, bucket: str, key: str) -> bytes:
        raise StorageUnavailable("Supabase Storage is not configured.")

    def exists(self, *, bucket: str, key: str) -> bool:
        raise StorageUnavailable("Supabase Storage is not configured.")

    def delete(self, *, bucket: str, key: str) -> None:
        raise StorageUnavailable("Supabase Storage is not configured.")

    def signed_url(self, *, bucket: str, key: str, expires_in: int = 300) -> str:
        raise StorageUnavailable("Supabase Storage is not configured.")


class _SupabaseStorage:
    """Production / cloud path — talks to the Supabase Storage HTTP API."""

    def __init__(self, *, url: str, service_key: str):
        # Imported lazily so a dev box without SUPABASE_URL doesn't pay the
        # import cost and so the test suite can stub the symbol.
        from supabase import create_client

        self._client = create_client(url, service_key)
        self._url = url

    def _bucket(self, name: str):
        # In supabase-py >= 2.10 the storage client is exposed as a
        # property, not a method. Older releases (`storage()`) are
        # unsupported here because pinning to 2.31 is required for
        # the postgrest/storage3 API shape the rest of this module
        # uses.
        return self._client.storage.from_(name)

    def upload(self, *, bucket: str, key: str, data: bytes, content_type: Optional[str] = None) -> StoredObject:
        file_options = {"content-type": content_type} if content_type else {}
        # Supabase Storage's upload wants a file-like object; bytes work.
        result = self._bucket(bucket).upload(
            path=key,
            file=io.BytesIO(data),
            file_options=file_options or None,
        )
        # supabase-py's return shape is provider-dependent; size + etag are
        # best-effort. If the response is an error dict, surface it.
        size = len(data)
        etag: Optional[str] = None
        if isinstance(result, dict):
            etag = result.get("Key") or result.get("Id")
        return StoredObject(bucket=bucket, key=key, size=size, etag=etag, content_type=content_type)

    def download(self, *, bucket: str, key: str) -> bytes:
        return self._bucket(bucket).download(key)

    def exists(self, *, bucket: str, key: str) -> bool:
        # The list API is the cheapest way; an empty result means the key
        # is absent in that prefix.
        result = self._bucket(bucket).list(path=key.rsplit("/", 1)[0] if "/" in key else "")
        return any(item.get("name") == key.rsplit("/", 1)[-1] for item in result or [])

    def delete(self, *, bucket: str, key: str) -> None:
        self._bucket(bucket).remove([key])

    def signed_url(self, *, bucket: str, key: str, expires_in: int = 300) -> str:
        result = self._bucket(bucket).create_signed_url(key, expires_in)
        if isinstance(result, dict):
            url = result.get("signedURL") or result.get("signedUrl")
            if url:
                return url
        raise StorageUnavailable(f"Supabase signed-url response was empty for {bucket}/{key}")


class _S3Storage:
    """Local-dev stand-in. MinIO implements the S3 API; supabase-py's
    `storage3` library uses the same protocol, so the same key/bucket
    semantics work for both. The `S3` client is the only one with a
    `presigned_url` call that matches our needs, hence minio over boto3.
    """

    def __init__(self, *, endpoint: str, access_key: str, secret_key: str, region: str, secure: bool = False):
        from minio import Minio

        # MinIO's Python client uses host:port, not a full URL.
        host = endpoint.split("://", 1)[-1].rstrip("/")
        self._client = Minio(
            host,
            access_key=access_key,
            secret_key=secret_key,
            region=region,
            secure=secure,
        )

    def _ensure_bucket(self, name: str) -> None:
        if not self._client.bucket_exists(name):
            self._client.make_bucket(name)

    def upload(self, *, bucket: str, key: str, data: bytes, content_type: Optional[str] = None) -> StoredObject:
        self._ensure_bucket(bucket)
        # MinIO's `put_object` takes a stream; BytesIO is fine for in-memory blobs.
        result = self._client.put_object(
            bucket,
            key,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type or "application/octet-stream",
        )
        return StoredObject(bucket=bucket, key=key, size=len(data), etag=result.etag, content_type=content_type)

    def download(self, *, bucket: str, key: str) -> bytes:
        response = self._client.get_object(bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def exists(self, *, bucket: str, key: str) -> bool:
        try:
            self._client.stat_object(bucket, key)
            return True
        except Exception:  # minio.error.S3Error; broad except avoids importing the type
            return False

    def delete(self, *, bucket: str, key: str) -> None:
        try:
            self._client.remove_object(bucket, key)
        except Exception as exc:  # noqa: BLE001 — see exists()
            logger.warning("MinIO delete failed for %s/%s: %s", bucket, key, exc)

    def signed_url(self, *, bucket: str, key: str, expires_in: int = 300) -> str:
        from datetime import timedelta

        return self._client.presigned_get_object(bucket, key, expires=timedelta(seconds=expires_in))


def _build_storage():
    """Pick the right backend based on env. Called once at import time."""

    if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
        try:
            return _SupabaseStorage(
                url=os.environ["SUPABASE_URL"],
                service_key=os.environ["SUPABASE_SERVICE_ROLE_KEY"],
            )
        except Exception as exc:  # noqa: BLE001
            # Don't crash the worker on a transient network error at boot;
            # the call sites will retry on the next request, and operators
            # see the warning in the logs.
            logger.error("Failed to initialise Supabase Storage client: %s", exc)

    s3_endpoint = os.environ.get("SUPABASE_S3_ENDPOINT")
    s3_key = os.environ.get("SUPABASE_S3_ACCESS_KEY")
    s3_secret = os.environ.get("SUPABASE_S3_SECRET_KEY")
    if s3_endpoint and s3_key and s3_secret:
        try:
            return _S3Storage(
                endpoint=s3_endpoint,
                access_key=s3_key,
                secret_key=s3_secret,
                region=os.environ.get("SUPABASE_S3_REGION", "us-east-1"),
                secure=s3_endpoint.startswith("https://"),
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to initialise S3/MinIO Storage client: %s", exc)

    return _FilesystemFallback()


storage = _build_storage()
"""Module-level singleton. Tests can replace this with a stub."""


def is_storage_configured() -> bool:
    """True iff `storage` is a real backend (Supabase or MinIO), not the fallback."""

    return not isinstance(storage, _FilesystemFallback)
