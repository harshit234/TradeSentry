from __future__ import annotations

import json
import os
from statistics import median
from time import perf_counter

import boto3  # type: ignore[import-untyped]
from boto3.dynamodb.conditions import Key  # type: ignore[import-untyped]


def main() -> None:
    table = boto3.resource(
        "dynamodb",
        region_name=os.getenv("AWS_REGION", "ap-south-1"),
        endpoint_url=os.getenv("DYNAMODB_ENDPOINT_URL"),
    ).Table(os.getenv("CROSS_IBU_TABLE_NAME", "TradeFinanceRegistry"))
    expression = Key("bl_number_normalized").eq("BL789456")
    table.query(IndexName="gsi_bl_number", KeyConditionExpression=expression)
    timings: list[float] = []
    for _ in range(10):
        started = perf_counter()
        table.query(IndexName="gsi_bl_number", KeyConditionExpression=expression)
        timings.append((perf_counter() - started) * 1000)
    print(
        json.dumps(
            {
                "queries": len(timings),
                "min_ms": round(min(timings), 3),
                "median_ms": round(median(timings), 3),
                "max_ms": round(max(timings), 3),
                "all_under_50ms": max(timings) < 50,
            }
        )
    )


if __name__ == "__main__":
    main()
