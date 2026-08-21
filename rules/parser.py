from __future__ import annotations

from models.compliance import LCRequirements
from models.contracts import LetterOfCreditFields


def parse_lc_requirements(fields: LetterOfCreditFields) -> LCRequirements:
    """Map extracted LC facts only; this function does not infer rule content."""
    return LCRequirements(
        lc_number=fields.lc_number,
        issuing_bank=fields.issuing_bank,
        applicant=fields.applicant,
        beneficiary=fields.beneficiary,
        credit_amount=fields.credit_amount,
        currency=fields.currency,
        about_flag=bool(fields.about_flag),
        expiry_date=fields.expiry_date,
        latest_shipment_date=fields.latest_shipment_date,
        credit_specific_presentation_days=fields.credit_specific_presentation_days,
        partial_shipments_allowed=(
            True if fields.partial_shipments_allowed is None else fields.partial_shipments_allowed
        ),
        required_documents=fields.required_documents,
        special_conditions=fields.special_conditions,
        goods_description=fields.goods_description,
        quantity=fields.quantity,
        unit=fields.unit,
        loading_port=fields.loading_port,
        discharge_port=fields.discharge_port,
    )
