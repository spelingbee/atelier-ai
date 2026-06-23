"""
AtelierAI — Storage (NEW FILE, additive).

Единый интерфейс хранилища. Для MVP — LocalStorage (пишет в папку на диске).
Для production — S3Storage (boto3, ленивый импорт). Оба дают put()/url().
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path


class LocalStorage:
    """Хранит файлы локально и отдаёт file:// или /static URL. Без зависимостей."""

    def __init__(self, root: str = "/data/skirt/storage",
                 base_url: str | None = None):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        if base_url is None:
            base_url = os.getenv("STORAGE_BASE_URL", "http://localhost:8000/files")
        self.base_url = base_url.rstrip("/")

    def put_file(self, key: str, src_path: str) -> str:
        dst = self.root / key
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src_path, dst)
        return key

    def put_bytes(self, key: str, data: bytes) -> str:
        dst = self.root / key
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
        return key

    def url(self, key: str, expires: int = 3600) -> str:
        return f"{self.base_url}/{key}"

    def local_path(self, key: str) -> str:
        return str(self.root / key)


class S3Storage:
    """S3/MinIO. boto3 импортируется лениво — модуль работает без boto3, если не используется."""

    def __init__(self, bucket: str | None = None, endpoint: str | None = None):
        import boto3  # ленивый импорт
        self.bucket = bucket or os.environ["S3_BUCKET"]
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint or os.getenv("S3_ENDPOINT"),
            aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
            aws_secret_access_key=os.getenv("S3_SECRET_KEY"),
        )

    def put_file(self, key: str, src_path: str) -> str:
        self.client.upload_file(src_path, self.bucket, key)
        return key

    def put_bytes(self, key: str, data: bytes) -> str:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data)
        return key

    def url(self, key: str, expires: int = 3600) -> str:
        return self.client.generate_presigned_url(
            "get_object", Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires)


def get_storage():
    """Фабрика: STORAGE_BACKEND=s3|local (дефолт local для MVP)."""
    if os.getenv("STORAGE_BACKEND", "local") == "s3":
        return S3Storage()
    return LocalStorage()
