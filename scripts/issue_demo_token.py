from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta

import boto3  # type: ignore[import-untyped]
import jwt


def issue(profile: str | None, region: str, secret_id: str, ibu_id: str, role: str) -> str:
    session = boto3.Session(profile_name=profile or None, region_name=region)
    secret = json.loads(
        session.client("secretsmanager")
        .get_secret_value(SecretId=secret_id)["SecretString"]
    )
    now = datetime.now(UTC)
    return str(
        jwt.encode(
            {
                "officer_id": "hackathon-demo-officer",
                "role": role,
                "ibu_id": ibu_id,
                "iss": "tradesentry",
                "aud": "tradesentry-dashboard",
                "iat": now,
                "exp": now + timedelta(minutes=30),
                "token_type": "access",
            },
            secret["JWT_PRIVATE_KEY"],
            algorithm="RS256",
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Issue a 30-minute synthetic demo JWT")
    parser.add_argument("--profile")
    parser.add_argument("--region", default="ap-south-1")
    parser.add_argument("--secret-id", required=True)
    parser.add_argument("--ibu-id", choices=("IBU-A", "IBU-B", "IBU-C"), default="IBU-A")
    parser.add_argument("--role", choices=("OFFICER", "AUDITOR", "ADMIN"), default="OFFICER")
    args = parser.parse_args()
    print(issue(args.profile, args.region, args.secret_id, args.ibu_id, args.role))
