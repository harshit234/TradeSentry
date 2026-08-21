from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol

import boto3  # type: ignore[import-untyped]
from boto3.dynamodb.conditions import Key  # type: ignore[import-untyped]

from cross_ibu.matcher import matching_config
from cross_ibu.registry import registration_from_signal
from models.cross_ibu import RegistryRegistration, RegistrySignal


class CrossIBURegistry(Protocol):
    async def register(
        self, signal: RegistrySignal, registered_at: datetime
    ) -> RegistryRegistration: ...
    async def find_candidates(self, signal: RegistrySignal) -> list[RegistryRegistration]: ...
    async def list_all(self) -> list[RegistryRegistration]: ...


class InMemoryCrossIBURegistry:
    def __init__(self) -> None:
        self.items: dict[tuple[str, str], RegistryRegistration] = {}

    async def register(
        self, signal: RegistrySignal, registered_at: datetime
    ) -> RegistryRegistration:
        registration = registration_from_signal(
            signal, registered_at, int(matching_config()["ttl_days"])
        )
        self.items[(signal.ibu_id, signal.dna_fingerprint)] = registration
        return registration

    async def find_candidates(self, signal: RegistrySignal) -> list[RegistryRegistration]:
        return [
            item
            for item in self.items.values()
            if item.ibu_id != signal.ibu_id
            and (
                item.dna_fingerprint == signal.dna_fingerprint
                or bool(
                    signal.bl_number_normalized
                    and item.bl_number_normalized == signal.bl_number_normalized
                )
                or bool(
                    signal.vessel_normalized and item.vessel_normalized == signal.vessel_normalized
                )
                or bool(
                    signal.exporter_normalized
                    and item.exporter_normalized == signal.exporter_normalized
                )
            )
        ]

    async def list_all(self) -> list[RegistryRegistration]:
        return sorted(self.items.values(), key=lambda item: item.registration_id)


class DynamoDBCrossIBURegistry:
    def __init__(self, table_name: str, region: str, endpoint_url: str | None) -> None:
        resource = boto3.resource("dynamodb", region_name=region, endpoint_url=endpoint_url)
        self.table: Any = resource.Table(table_name)

    @staticmethod
    def _item(registration: RegistryRegistration) -> dict[str, Any]:
        item = registration.model_dump()
        item["PK"] = f"IBU#{registration.ibu_id}"
        item["SK"] = f"DNA#{registration.dna_fingerprint}"
        item["registered_at"] = registration.registered_at.isoformat()
        return {key: value for key, value in item.items() if value is not None}

    @staticmethod
    def _registration(item: dict[str, Any]) -> RegistryRegistration:
        values = {key: value for key, value in item.items() if key not in {"PK", "SK"}}
        return RegistryRegistration.model_validate(values)

    async def register(
        self, signal: RegistrySignal, registered_at: datetime
    ) -> RegistryRegistration:
        registration = registration_from_signal(
            signal, registered_at, int(matching_config()["ttl_days"])
        )
        self.table.put_item(Item=self._item(registration))
        return registration

    async def find_candidates(self, signal: RegistrySignal) -> list[RegistryRegistration]:
        items: dict[str, dict[str, Any]] = {}
        sort_key = f"DNA#{signal.dna_fingerprint}"
        for ibu_id in matching_config()["simulated_ibus"]:
            response = self.table.get_item(Key={"PK": f"IBU#{ibu_id}", "SK": sort_key})
            if response.get("Item"):
                item = response["Item"]
                items[item["registration_id"]] = item
        queries = (
            ("gsi_bl_number", "bl_number_normalized", signal.bl_number_normalized),
            ("gsi_vessel_date", "vessel_normalized", signal.vessel_normalized),
            ("gsi_exporter", "exporter_normalized", signal.exporter_normalized),
        )
        for index_name, field_name, value in queries:
            if not value:
                continue
            response = self.table.query(
                IndexName=index_name,
                KeyConditionExpression=Key(field_name).eq(value),
            )
            for item in response.get("Items", []):
                items[item["registration_id"]] = item
        now_epoch = int(datetime.now(UTC).timestamp())
        return [
            self._registration(item)
            for item in items.values()
            if item["ibu_id"] != signal.ibu_id and int(item["ttl"]) > now_epoch
        ]

    async def list_all(self) -> list[RegistryRegistration]:
        items: list[dict[str, Any]] = []
        for ibu_id in matching_config()["simulated_ibus"]:
            response = self.table.query(KeyConditionExpression=Key("PK").eq(f"IBU#{ibu_id}"))
            items.extend(response.get("Items", []))
        return sorted(
            (self._registration(item) for item in items),
            key=lambda item: item.registration_id,
        )
