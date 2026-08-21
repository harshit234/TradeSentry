from __future__ import annotations

import argparse
import json
from urllib.parse import quote

import boto3  # type: ignore[import-untyped]
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def _key_pair() -> tuple[str, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return private_pem, public_pem


def configure(
    profile: str | None,
    region: str,
    application_secret_arn: str,
    rds_master_secret_arn: str,
    rds_endpoint: str,
    redis_endpoint: str,
) -> None:
    session = boto3.Session(profile_name=profile or None, region_name=region)
    client = session.client("secretsmanager")
    master = json.loads(
        client.get_secret_value(SecretId=rds_master_secret_arn)["SecretString"]
    )
    private_pem, public_pem = _key_pair()
    username = quote(str(master["username"]), safe="")
    password = quote(str(master["password"]), safe="")
    payload = {
        "DATABASE_URL": (
            f"postgresql+asyncpg://{username}:{password}@{rds_endpoint}:5432/"
            "tradesentry?ssl=require"
        ),
        "REDIS_URL": f"rediss://{redis_endpoint}:6379/0?ssl_cert_reqs=required",
        "JWT_PUBLIC_KEY": public_pem,
        "JWT_PRIVATE_KEY": private_pem,
    }
    client.put_secret_value(
        SecretId=application_secret_arn,
        SecretString=json.dumps(payload),
    )
    print("Configured encrypted staging runtime secret without writing credentials to disk")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Configure the encrypted AWS staging secret")
    parser.add_argument("--profile")
    parser.add_argument("--region", default="ap-south-1")
    parser.add_argument("--application-secret-arn", required=True)
    parser.add_argument("--rds-master-secret-arn", required=True)
    parser.add_argument("--rds-endpoint", required=True)
    parser.add_argument("--redis-endpoint", required=True)
    args = parser.parse_args()
    configure(
        args.profile,
        args.region,
        args.application_secret_arn,
        args.rds_master_secret_arn,
        args.rds_endpoint,
        args.redis_endpoint,
    )
