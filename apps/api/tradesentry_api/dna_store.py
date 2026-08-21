from __future__ import annotations

from typing import Protocol

from sqlalchemy import text

from models.dna import TransactionDNA

from .db import Database


class TransactionDNAStore(Protocol):
    async def save(self, dna: TransactionDNA) -> None: ...
    async def get(self, case_id: str) -> TransactionDNA | None: ...


class InMemoryTransactionDNAStore:
    def __init__(self) -> None:
        self.results: dict[str, TransactionDNA] = {}

    async def save(self, dna: TransactionDNA) -> None:
        self.results[dna.case_id] = dna

    async def get(self, case_id: str) -> TransactionDNA | None:
        return self.results.get(case_id)


class PostgresTransactionDNAStore:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def save(self, dna: TransactionDNA) -> None:
        async with self.database.engine.begin() as connection:
            await connection.execute(
                text(
                    """INSERT INTO transaction_dna
                    (case_id, transaction_id, dna_fingerprint, dna_json, created_at)
                    VALUES (:case_id, :transaction_id, :fingerprint,
                            CAST(:dna AS JSONB), :created_at)
                    ON CONFLICT (case_id) DO UPDATE SET
                      transaction_id=EXCLUDED.transaction_id,
                      dna_fingerprint=EXCLUDED.dna_fingerprint,
                      dna_json=EXCLUDED.dna_json,
                      created_at=EXCLUDED.created_at"""
                ),
                {
                    "case_id": dna.case_id,
                    "transaction_id": dna.transaction_id,
                    "fingerprint": dna.dna_fingerprint,
                    "dna": dna.model_dump_json(),
                    "created_at": dna.created_at,
                },
            )

    async def get(self, case_id: str) -> TransactionDNA | None:
        async with self.database.engine.connect() as connection:
            value = await connection.scalar(
                text("SELECT dna_json FROM transaction_dna WHERE case_id=:case_id"),
                {"case_id": case_id},
            )
        return TransactionDNA.model_validate(value) if value else None
