from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import datetime
from decimal import Decimal
from difflib import SequenceMatcher

from models.contracts import (
    BillOfLadingFields,
    CommercialInvoiceFields,
    DocumentType,
    ExtractionResult,
    LetterOfCreditFields,
    PackingListFields,
)
from models.dna import ConflictRecord, ConflictSeverity, TransactionDNA

from .normalization import (
    NormalizationError,
    convert_currency_to_usd,
    normalization_config,
    normalize_date,
    normalize_entity_name,
    normalize_free_text,
    normalize_hs_code,
    normalize_identifier,
    normalize_port,
    normalize_quantity,
)


def _extraction(
    extractions: list[ExtractionResult], document_type: DocumentType
) -> ExtractionResult | None:
    return next((item for item in extractions if item.document_type is document_type), None)


def _typed_fields(extraction: ExtractionResult | None, expected: type[object]) -> object | None:
    if extraction is None:
        return None
    return extraction.fields if isinstance(extraction.fields, expected) else None


def _source(
    sources: dict[str, str], fields: tuple[str, ...], extraction: ExtractionResult | None
) -> None:
    if extraction:
        for field in fields:
            sources[field] = extraction.document_id


def _string_conflict(
    field_name: str,
    document_a_id: str,
    value_a: str | None,
    document_b_id: str,
    value_b: str | None,
    normalizer: Callable[[str], str | None],
) -> ConflictRecord | None:
    if value_a is None or value_b is None:
        return None
    normalized_a = normalizer(value_a)
    normalized_b = normalizer(value_b)
    if normalized_a == normalized_b:
        return None
    ratio = Decimal(str(SequenceMatcher(None, str(normalized_a), str(normalized_b)).ratio()))
    threshold = Decimal(normalization_config()["advisory_similarity_threshold"])
    return ConflictRecord(
        field_name=field_name,
        document_a_id=document_a_id,
        document_a_value=value_a,
        document_b_id=document_b_id,
        document_b_value=value_b,
        severity=(ConflictSeverity.ADVISORY if ratio >= threshold else ConflictSeverity.MATERIAL),
    )


def _quantity_conflicts(
    entries: list[tuple[str, Decimal | None, str | None]],
) -> list[ConflictRecord]:
    normalized: list[tuple[str, Decimal, str, Decimal, str]] = []
    for document_id, value, unit in entries:
        if value is None or unit is None:
            continue
        try:
            canonical, canonical_unit = normalize_quantity(value, unit)
        except NormalizationError:
            continue
        normalized.append((document_id, canonical, canonical_unit, value, unit))
    if len(normalized) < 2:
        return []
    first = normalized[0]
    conflicts: list[ConflictRecord] = []
    for current in normalized[1:]:
        if (first[1], first[2]) != (current[1], current[2]):
            conflicts.append(
                ConflictRecord(
                    field_name="quantity",
                    document_a_id=first[0],
                    document_a_value=f"{first[3]} {first[4]}",
                    document_b_id=current[0],
                    document_b_value=f"{current[3]} {current[4]}",
                    severity=ConflictSeverity.MATERIAL,
                )
            )
    return conflicts


def _confidence_flags(extractions: list[ExtractionResult]) -> list[str]:
    field_map = {
        "seller": "exporter_normalized",
        "shipper": "exporter_normalized",
        "buyer": "importer_normalized",
        "consignee": "importer_normalized",
        "bl_number": "bl_number_normalized",
        "vessel_name": "vessel_normalized",
        "voyage_number": "voyage_normalized",
        "loading_port": "loading_port_unlocode",
        "discharge_port": "discharge_port_unlocode",
        "on_board_date": "shipment_date_iso",
        "goods_description": "commodity_normalized",
        "hs_code": "hs_code_canonical",
        "quantity": "quantity_canonical",
        "invoice_amount": "invoice_value_usd",
        "currency": "invoice_value_usd",
    }
    flags = {
        field_map.get(field, field)
        for extraction in extractions
        for field in extraction.extraction_flags
    }
    return sorted(flags)


def build_transaction_dna(
    case_id: str,
    presenting_ibu: str,
    extractions: list[ExtractionResult],
    created_at: datetime,
) -> TransactionDNA:
    lc_extraction = _extraction(extractions, DocumentType.LETTER_OF_CREDIT)
    invoice_extraction = _extraction(extractions, DocumentType.COMMERCIAL_INVOICE)
    bl_extraction = _extraction(extractions, DocumentType.BILL_OF_LADING)
    packing_extraction = _extraction(extractions, DocumentType.PACKING_LIST)
    lc = _typed_fields(lc_extraction, LetterOfCreditFields)
    invoice = _typed_fields(invoice_extraction, CommercialInvoiceFields)
    bl = _typed_fields(bl_extraction, BillOfLadingFields)
    packing = _typed_fields(packing_extraction, PackingListFields)
    lc = lc if isinstance(lc, LetterOfCreditFields) else None
    invoice = invoice if isinstance(invoice, CommercialInvoiceFields) else None
    bl = bl if isinstance(bl, BillOfLadingFields) else None
    packing = packing if isinstance(packing, PackingListFields) else None

    exporter_source = invoice_extraction if invoice and invoice.seller else bl_extraction
    importer_source = invoice_extraction if invoice and invoice.buyer else bl_extraction
    loading_port_source = lc_extraction if lc and lc.loading_port else bl_extraction
    discharge_port_source = lc_extraction if lc and lc.discharge_port else bl_extraction
    commodity_source = (
        invoice_extraction if invoice and invoice.goods_description else bl_extraction
    )
    hs_code_source = invoice_extraction if invoice and invoice.hs_code else bl_extraction
    quantity_source = (
        invoice_extraction if invoice and invoice.quantity is not None else bl_extraction
    )
    unit_source = invoice_extraction if invoice and invoice.unit else bl_extraction

    raw_exporter = invoice.seller if invoice and invoice.seller else bl.shipper if bl else None
    raw_importer = invoice.buyer if invoice and invoice.buyer else bl.consignee if bl else None
    raw_loading_port = (
        lc.loading_port if lc and lc.loading_port else bl.loading_port if bl else None
    )
    raw_discharge_port = (
        lc.discharge_port if lc and lc.discharge_port else bl.discharge_port if bl else None
    )
    raw_commodity = (
        invoice.goods_description
        if invoice and invoice.goods_description
        else bl.goods_description
        if bl
        else None
    )
    raw_hs_code = invoice.hs_code if invoice and invoice.hs_code else bl.hs_code if bl else None
    raw_quantity = (
        invoice.quantity
        if invoice and invoice.quantity is not None
        else bl.quantity
        if bl
        else None
    )
    raw_unit = invoice.unit if invoice and invoice.unit else bl.unit if bl else None
    shipment_date = (bl.on_board_date or bl.bl_date) if bl else None

    sources: dict[str, str] = {}
    _source(sources, ("raw_exporter", "exporter_normalized"), exporter_source)
    _source(sources, ("raw_importer", "importer_normalized"), importer_source)
    _source(
        sources,
        (
            "raw_bl_number",
            "bl_number_normalized",
            "raw_vessel_name",
            "vessel_normalized",
            "imo_number",
            "raw_voyage_number",
            "voyage_normalized",
            "raw_shipment_date",
            "shipment_date_iso",
        ),
        bl_extraction,
    )
    _source(sources, ("raw_loading_port", "loading_port_unlocode"), loading_port_source)
    _source(sources, ("raw_discharge_port", "discharge_port_unlocode"), discharge_port_source)
    _source(sources, ("raw_commodity", "commodity_normalized"), commodity_source)
    _source(sources, ("raw_hs_code", "hs_code_canonical"), hs_code_source)
    _source(sources, ("raw_quantity", "quantity_canonical"), quantity_source)
    _source(sources, ("raw_quantity_unit", "unit_canonical"), unit_source)
    _source(
        sources,
        (
            "raw_invoice_value",
            "raw_currency",
            "invoice_value_usd",
            "unit_value_usd_per_unit",
            "raw_invoice_number",
        ),
        invoice_extraction,
    )
    _source(sources, ("raw_lc_number",), lc_extraction)

    quantity_canonical: Decimal | None = None
    unit_canonical: str | None = None
    if raw_quantity is not None and raw_unit:
        try:
            quantity_canonical, unit_canonical = normalize_quantity(raw_quantity, raw_unit)
        except NormalizationError:
            pass
    invoice_value = invoice.invoice_amount if invoice else None
    raw_currency = invoice.currency if invoice else None
    invoice_value_usd = (
        convert_currency_to_usd(invoice_value, raw_currency)
        if invoice_value is not None and raw_currency
        else None
    )
    unit_value = (
        invoice_value_usd / quantity_canonical
        if invoice_value_usd is not None
        and quantity_canonical is not None
        and quantity_canonical != 0
        else None
    )

    conflicts: list[ConflictRecord] = []
    if invoice and bl and invoice_extraction and bl_extraction:
        for conflict in (
            _string_conflict(
                "exporter",
                invoice_extraction.document_id,
                invoice.seller,
                bl_extraction.document_id,
                bl.shipper,
                normalize_entity_name,
            ),
            _string_conflict(
                "vessel_name",
                invoice_extraction.document_id,
                invoice.vessel_name,
                bl_extraction.document_id,
                bl.vessel_name,
                normalize_free_text,
            ),
        ):
            if conflict:
                conflicts.append(conflict)
    if lc and bl and lc_extraction and bl_extraction:
        for field_name in ("loading_port", "discharge_port"):
            conflict = _string_conflict(
                field_name,
                lc_extraction.document_id,
                getattr(lc, field_name),
                bl_extraction.document_id,
                getattr(bl, field_name),
                normalize_port,
            )
            if conflict:
                conflicts.append(conflict)
    conflicts.extend(
        _quantity_conflicts(
            [
                (
                    invoice_extraction.document_id if invoice_extraction else "invoice",
                    invoice.quantity if invoice else None,
                    invoice.unit if invoice else None,
                ),
                (
                    bl_extraction.document_id if bl_extraction else "bill_of_lading",
                    bl.quantity if bl else None,
                    bl.unit if bl else None,
                ),
                (
                    packing_extraction.document_id if packing_extraction else "packing_list",
                    packing.total_quantity if packing else None,
                    next(
                        (item.unit for item in packing.line_items if item.unit),
                        None,
                    )
                    if packing
                    else None,
                ),
            ]
        )
    )
    conflicts = sorted(
        conflicts, key=lambda item: (item.field_name, item.document_a_id, item.document_b_id)
    )

    normalized = {
        "exporter_normalized": normalize_entity_name(raw_exporter) if raw_exporter else None,
        "importer_normalized": normalize_entity_name(raw_importer) if raw_importer else None,
        "bl_number_normalized": normalize_identifier(bl.bl_number) if bl and bl.bl_number else None,
        "vessel_normalized": normalize_free_text(bl.vessel_name) if bl and bl.vessel_name else None,
        "voyage_normalized": normalize_identifier(bl.voyage_number)
        if bl and bl.voyage_number
        else None,
        "loading_port_unlocode": normalize_port(raw_loading_port) if raw_loading_port else None,
        "discharge_port_unlocode": normalize_port(raw_discharge_port)
        if raw_discharge_port
        else None,
        "shipment_date_iso": normalize_date(shipment_date.isoformat()).isoformat()
        if shipment_date
        else None,
    }
    fingerprint_fields = [
        normalized["bl_number_normalized"],
        normalized["vessel_normalized"],
        normalized["voyage_normalized"],
        normalized["loading_port_unlocode"],
        normalized["discharge_port_unlocode"],
        normalized["shipment_date_iso"],
        normalized["exporter_normalized"],
    ]
    fingerprint = hashlib.sha256(
        "".join(value or "" for value in fingerprint_fields).encode()
    ).hexdigest()
    transaction_id = f"txn-{hashlib.sha256(f'{case_id}:{fingerprint}'.encode()).hexdigest()[:24]}"

    source_values: dict[str, object | None] = {
        "raw_exporter": raw_exporter,
        "exporter_normalized": normalized["exporter_normalized"],
        "raw_importer": raw_importer,
        "importer_normalized": normalized["importer_normalized"],
        "raw_bl_number": bl.bl_number if bl else None,
        "bl_number_normalized": normalized["bl_number_normalized"],
        "raw_vessel_name": bl.vessel_name if bl else None,
        "vessel_normalized": normalized["vessel_normalized"],
        "imo_number": bl.imo_number if bl else None,
        "raw_voyage_number": bl.voyage_number if bl else None,
        "voyage_normalized": normalized["voyage_normalized"],
        "raw_loading_port": raw_loading_port,
        "loading_port_unlocode": normalized["loading_port_unlocode"],
        "raw_discharge_port": raw_discharge_port,
        "discharge_port_unlocode": normalized["discharge_port_unlocode"],
        "raw_shipment_date": shipment_date,
        "shipment_date_iso": normalized["shipment_date_iso"],
        "raw_commodity": raw_commodity,
        "commodity_normalized": raw_commodity,
        "raw_hs_code": raw_hs_code,
        "hs_code_canonical": raw_hs_code,
        "raw_quantity": raw_quantity,
        "raw_quantity_unit": raw_unit,
        "quantity_canonical": quantity_canonical,
        "unit_canonical": unit_canonical,
        "raw_invoice_value": invoice_value,
        "raw_currency": raw_currency,
        "invoice_value_usd": invoice_value_usd,
        "unit_value_usd_per_unit": unit_value,
        "raw_lc_number": lc.lc_number if lc else None,
        "raw_invoice_number": invoice.invoice_number if invoice else None,
    }
    sources = {
        field: document_id
        for field, document_id in sources.items()
        if source_values.get(field) is not None
    }

    return TransactionDNA(
        transaction_id=transaction_id,
        case_id=case_id,
        presenting_ibu=presenting_ibu,
        raw_exporter=raw_exporter,
        raw_importer=raw_importer,
        raw_bl_number=bl.bl_number if bl else None,
        raw_vessel_name=bl.vessel_name if bl else None,
        raw_voyage_number=bl.voyage_number if bl else None,
        raw_loading_port=raw_loading_port,
        raw_discharge_port=raw_discharge_port,
        raw_shipment_date=shipment_date.isoformat() if shipment_date else None,
        raw_commodity=raw_commodity,
        raw_hs_code=raw_hs_code,
        raw_quantity=raw_quantity,
        raw_quantity_unit=raw_unit,
        raw_invoice_value=invoice_value,
        raw_currency=raw_currency,
        raw_lc_number=lc.lc_number if lc else None,
        raw_invoice_number=invoice.invoice_number if invoice else None,
        exporter_normalized=normalized["exporter_normalized"],
        importer_normalized=normalized["importer_normalized"],
        bl_number_normalized=normalized["bl_number_normalized"],
        vessel_normalized=normalized["vessel_normalized"],
        imo_number=normalize_identifier(bl.imo_number) if bl and bl.imo_number else None,
        voyage_normalized=normalized["voyage_normalized"],
        loading_port_unlocode=normalized["loading_port_unlocode"],
        discharge_port_unlocode=normalized["discharge_port_unlocode"],
        shipment_date_iso=normalized["shipment_date_iso"],
        commodity_normalized=normalize_free_text(raw_commodity) if raw_commodity else None,
        hs_code_canonical=normalize_hs_code(raw_hs_code) if raw_hs_code else None,
        quantity_canonical=quantity_canonical,
        unit_canonical=unit_canonical,
        invoice_value_usd=invoice_value_usd,
        unit_value_usd_per_unit=unit_value,
        dna_fingerprint=fingerprint,
        source_documents=sources,
        normalization_methods={
            "exporter_normalized": "normalize_entity_name:v1",
            "importer_normalized": "normalize_entity_name:v1",
            "bl_number_normalized": "normalize_identifier:v1",
            "vessel_normalized": "normalize_free_text:v1",
            "voyage_normalized": "normalize_identifier:v1",
            "loading_port_unlocode": "bundled_unlocode_aliases:v1",
            "discharge_port_unlocode": "bundled_unlocode_aliases:v1",
            "shipment_date_iso": "normalize_date:v1",
            "commodity_normalized": "normalize_free_text:v1",
            "hs_code_canonical": "normalize_hs_code:v1",
            "quantity_canonical": "normalize_quantity:v1",
            "invoice_value_usd": "bundled_currency_rate:USD-only:v1",
        },
        confidence_flags=_confidence_flags(extractions),
        conflicts=conflicts,
        created_at=created_at,
    )
