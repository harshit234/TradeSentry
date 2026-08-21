from typing import Any, Protocol, cast

import boto3  # type: ignore[import-untyped]


class Storage(Protocol):
    async def check(self) -> bool: ...
    async def close(self) -> None: ...
    async def upload(self, file_bytes: bytes, key: str, metadata: dict[str, str]) -> str: ...
    async def download(self, key: str) -> bytes: ...
    async def presigned_url(self, key: str, expires: int = 900) -> str: ...
    async def delete(self, key: str) -> None: ...


class S3Storage:
    def __init__(
        self,
        bucket: str,
        region: str,
        kms_key_id: str,
        endpoint_url: str | None = None,
        public_endpoint_url: str | None = None,
    ) -> None:
        self.bucket = bucket
        self.kms_key_id = kms_key_id
        self.client: Any = boto3.client("s3", region_name=region, endpoint_url=endpoint_url)
        self.public_client: Any = (
            boto3.client("s3", region_name=region, endpoint_url=public_endpoint_url)
            if public_endpoint_url
            else self.client
        )

    async def check(self) -> bool:
        self.client.head_bucket(Bucket=self.bucket)
        return True

    async def upload(self, file_bytes: bytes, key: str, metadata: dict[str, str]) -> str:
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=file_bytes,
            Metadata=metadata,
            ServerSideEncryption="aws:kms",
            SSEKMSKeyId=self.kms_key_id,
        )
        return key

    async def download(self, key: str) -> bytes:
        return cast(bytes, self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read())

    async def presigned_url(self, key: str, expires: int = 900) -> str:
        safe_expiry = min(max(expires, 1), 900)
        return str(
            self.public_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=safe_expiry,
            )
        )

    async def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)

    async def close(self) -> None:
        return None


class InMemoryStorage:
    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    async def check(self) -> bool:
        return True

    async def upload(self, file_bytes: bytes, key: str, metadata: dict[str, str]) -> str:
        del metadata
        self._objects[key] = file_bytes
        return key

    async def download(self, key: str) -> bytes:
        return self._objects[key]

    async def presigned_url(self, key: str, expires: int = 900) -> str:
        safe_expiry = min(max(expires, 1), 900)
        return f"memory://{key}?expires={safe_expiry}"

    async def delete(self, key: str) -> None:
        self._objects.pop(key, None)

    async def close(self) -> None:
        return None
