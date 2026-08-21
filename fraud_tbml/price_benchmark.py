from __future__ import annotations

from abc import ABC, abstractmethod

from models.fraud_tbml import PriceBenchmarkResult, PriceSignal

from .common import DataUnavailableError, load_json, retrieved_now

PRICE_CAVEATS = [
    "Price differences may reflect quality grade",
    "Incoterms differences (CIF vs FOB) affect unit value",
    "Contract terms or forward pricing may explain deviation",
    "Market timing and seasonal factors affect prices",
    "This is a review signal — not proof of fraud",
]
METHODOLOGY = (
    "Invoice unit value is compared with corridor percentiles using prototype demo values — "
    "not regulatory standards. Values at or below P90 are NORMAL; values up to 1.5× P90 are "
    "REVIEW; higher values are SIGNIFICANT_ANOMALY. Human review is required."
)


class PriceBenchmarkProvider(ABC):
    @abstractmethod
    async def benchmark(
        self,
        hs_code: str,
        origin_country: str,
        destination_country: str,
        period: str,
        invoice_unit_value: float,
        currency: str,
    ) -> PriceBenchmarkResult: ...


class MockPriceBenchmarkProvider(PriceBenchmarkProvider):
    def __init__(self) -> None:
        self.fixture = load_json("fixtures/price_benchmark/un_comtrade_synthetic.json")

    async def benchmark(
        self,
        hs_code: str,
        origin_country: str,
        destination_country: str,
        period: str,
        invoice_unit_value: float,
        currency: str,
    ) -> PriceBenchmarkResult:
        corridor = f"{origin_country} → {destination_country}"
        key = f"{hs_code}|{origin_country}|{destination_country}|{period}"
        reference = self.fixture["records"].get(key)
        if reference is None or currency.upper() != "USD":
            return unavailable_price_result(
                hs_code, corridor, period, invoice_unit_value, currency, "No matching fixture record"
            )
        p50 = float(reference["reference_p50"])
        p90 = float(reference["reference_p90"])
        if invoice_unit_value <= p90:
            signal = PriceSignal.NORMAL
        elif invoice_unit_value <= p90 * 1.5:
            signal = PriceSignal.REVIEW
        else:
            signal = PriceSignal.SIGNIFICANT_ANOMALY
        return PriceBenchmarkResult(
            hs_code=hs_code,
            trade_corridor=corridor,
            period=period,
            reference_min=float(reference["reference_min"]),
            reference_p25=float(reference["reference_p25"]),
            reference_p50=p50,
            reference_p75=float(reference["reference_p75"]),
            reference_p90=p90,
            invoice_unit_value=invoice_unit_value,
            currency=currency,
            deviation_from_p50_pct=round((invoice_unit_value - p50) / p50 * 100, 1),
            signal=signal,
            data_source=str(self.fixture["data_source"]),
            source_version=str(self.fixture["version"]),
            methodology_note=METHODOLOGY,
            caveats=PRICE_CAVEATS.copy(),
            confidence=float(reference["confidence"]),
            retrieved_at=retrieved_now(),
        )


class ProductionPriceBenchmarkProvider(PriceBenchmarkProvider):
    async def benchmark(
        self,
        hs_code: str,
        origin_country: str,
        destination_country: str,
        period: str,
        invoice_unit_value: float,
        currency: str,
    ) -> PriceBenchmarkResult:
        raise DataUnavailableError("Production trade-data provider is not configured")


def unavailable_price_result(
    hs_code: str,
    trade_corridor: str,
    period: str,
    invoice_unit_value: float,
    currency: str,
    reason: str,
) -> PriceBenchmarkResult:
    return PriceBenchmarkResult(
        hs_code=hs_code,
        trade_corridor=trade_corridor,
        period=period,
        invoice_unit_value=invoice_unit_value,
        currency=currency,
        signal=PriceSignal.DATA_UNAVAILABLE,
        data_source="Provider unavailable",
        source_version="unavailable",
        methodology_note=METHODOLOGY,
        caveats=[*PRICE_CAVEATS, reason],
        confidence=0.0,
        retrieved_at=retrieved_now(),
    )

