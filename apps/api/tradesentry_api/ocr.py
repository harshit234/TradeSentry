from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Protocol

import boto3  # type: ignore[import-untyped]

from models.contracts import DocumentType


@dataclass(slots=True)
class PageBlock:
    page_number: int
    text: str
    confidence: float
    bbox: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class QueryAnswer:
    answer: str
    confidence: float
    page: int


@dataclass(slots=True)
class ExtractedTable:
    page: int
    rows: list[list[str]]


@dataclass(slots=True)
class RawOCRResult:
    full_text: str
    page_blocks: list[PageBlock]
    query_results: dict[str, QueryAnswer]
    tables: list[ExtractedTable]
    overall_confidence: float
    low_confidence_pages: list[int]
    job_id: str | None = None


class OCRProvider(Protocol):
    async def analyze_document(
        self, s3_bucket: str, s3_key: str, document_type: DocumentType, page_count: int
    ) -> RawOCRResult: ...


class StubOCRProvider:
    async def analyze_document(
        self, s3_bucket: str, s3_key: str, document_type: DocumentType, page_count: int
    ) -> RawOCRResult:
        del s3_bucket, s3_key, document_type
        pages = [
            PageBlock(page_number=number, text="", confidence=0.98)
            for number in range(1, page_count + 1)
        ]
        return RawOCRResult(
            full_text="",
            page_blocks=pages,
            query_results={},
            tables=[],
            overall_confidence=0.98,
            low_confidence_pages=[],
        )


QUERIES: dict[DocumentType, tuple[str, ...]] = {
    DocumentType.LETTER_OF_CREDIT: (
        "What is the LC number?",
        "What is the credit amount?",
        "What is the expiry date?",
        "Who is the beneficiary?",
        "Who is the applicant?",
        "What is the latest shipment date?",
        "What is the presentation period?",
        "What is the port of loading?",
        "What is the port of discharge?",
    ),
    DocumentType.BILL_OF_LADING: (
        "What is the Bill of Lading number?",
        "What is the vessel name?",
        "What is the IMO number?",
        "What is the voyage number?",
        "What is the port of loading?",
        "What is the port of discharge?",
        "What is the on-board date?",
        "Who is the shipper?",
        "Who is the consignee?",
    ),
    DocumentType.COMMERCIAL_INVOICE: (
        "What is the invoice number?",
        "What is the invoice amount?",
        "What is the currency?",
        "What is the quantity?",
        "What is the unit price?",
        "What is the HS code?",
        "What is the country of origin?",
    ),
    DocumentType.CERTIFICATE_OF_ORIGIN: (
        "What is the certificate number?",
        "What is the country of origin?",
        "Who is the exporter?",
        "Who is the consignee?",
    ),
    DocumentType.INSURANCE_CERTIFICATE: (
        "What is the policy number?",
        "What is the insured amount?",
        "Who is the insured party?",
        "Who is the insurer?",
    ),
}


FEATURES: dict[DocumentType, tuple[str, ...]] = {
    DocumentType.LETTER_OF_CREDIT: ("FORMS", "TABLES", "QUERIES"),
    DocumentType.COMMERCIAL_INVOICE: ("FORMS", "TABLES", "QUERIES"),
    DocumentType.BILL_OF_LADING: ("FORMS", "QUERIES"),
    DocumentType.PACKING_LIST: ("TABLES",),
    DocumentType.CERTIFICATE_OF_ORIGIN: ("FORMS", "QUERIES"),
    DocumentType.INSURANCE_CERTIFICATE: ("FORMS", "QUERIES"),
    DocumentType.INSPECTION_CERTIFICATE: ("FORMS",),
    DocumentType.UNKNOWN: ("FORMS", "TABLES"),
}


class TextractTimeoutError(TimeoutError):
    pass


class TextractOCRProvider:
    def __init__(
        self,
        region: str,
        confidence_threshold: float = 0.70,
        timeout_seconds: int = 120,
        poll_seconds: float = 2,
        endpoint_url: str | None = None,
    ) -> None:
        self.client: Any = boto3.client("textract", region_name=region, endpoint_url=endpoint_url)
        self.confidence_threshold = confidence_threshold
        self.timeout_seconds = timeout_seconds
        self.poll_seconds = poll_seconds

    def _request_options(self, document_type: DocumentType) -> dict[str, Any]:
        options: dict[str, Any] = {"FeatureTypes": list(FEATURES[document_type])}
        queries = QUERIES.get(document_type, ())
        if queries:
            options["QueriesConfig"] = {"Queries": [{"Text": query} for query in queries]}
        return options

    async def analyze_document(
        self, s3_bucket: str, s3_key: str, document_type: DocumentType, page_count: int
    ) -> RawOCRResult:
        document = {"S3Object": {"Bucket": s3_bucket, "Name": s3_key}}
        options = self._request_options(document_type)
        if page_count <= 1:
            response = await asyncio.to_thread(
                self.client.analyze_document, Document=document, **options
            )
            return self._parse_blocks(response.get("Blocks", []), document_type)

        started = await asyncio.to_thread(
            self.client.start_document_analysis, DocumentLocation=document, **options
        )
        job_id = str(started["JobId"])
        blocks = await asyncio.wait_for(self._poll(job_id), timeout=self.timeout_seconds)
        result = self._parse_blocks(blocks, document_type)
        result.job_id = job_id
        return result

    async def _poll(self, job_id: str) -> list[dict[str, Any]]:
        blocks: list[dict[str, Any]] = []
        next_token: str | None = None
        while True:
            arguments = {"JobId": job_id}
            if next_token:
                arguments["NextToken"] = next_token
            response = await asyncio.to_thread(self.client.get_document_analysis, **arguments)
            status = response.get("JobStatus")
            if status == "FAILED":
                raise RuntimeError("Textract document analysis failed")
            if status == "SUCCEEDED":
                blocks.extend(response.get("Blocks", []))
                next_token = response.get("NextToken")
                if not next_token:
                    return blocks
                continue
            await asyncio.sleep(self.poll_seconds)

    def _parse_blocks(
        self, blocks: list[dict[str, Any]], document_type: DocumentType
    ) -> RawOCRResult:
        del document_type
        by_id = {str(block.get("Id")): block for block in blocks if block.get("Id")}
        page_lines: dict[int, list[dict[str, Any]]] = {}
        query_results: dict[str, QueryAnswer] = {}
        for block in blocks:
            page = int(block.get("Page", 1))
            if block.get("BlockType") == "LINE":
                page_lines.setdefault(page, []).append(block)
            if block.get("BlockType") == "QUERY":
                question = str(block.get("Query", {}).get("Text", ""))
                answer_ids = [
                    child
                    for relation in block.get("Relationships", [])
                    if relation.get("Type") == "ANSWER"
                    for child in relation.get("Ids", [])
                ]
                if answer_ids and (answer := by_id.get(str(answer_ids[0]))):
                    query_results[question] = QueryAnswer(
                        answer=str(answer.get("Text", "")),
                        confidence=float(answer.get("Confidence", 0)) / 100,
                        page=int(answer.get("Page", page)),
                    )

        page_blocks: list[PageBlock] = []
        for page, lines in sorted(page_lines.items()):
            confidences = [float(line.get("Confidence", 0)) / 100 for line in lines]
            confidence = sum(confidences) / len(confidences) if confidences else 0.0
            page_blocks.append(
                PageBlock(
                    page_number=page,
                    text="\n".join(str(line.get("Text", "")) for line in lines),
                    confidence=confidence,
                    bbox=self._combined_bbox(lines),
                )
            )
        overall = (
            sum(page.confidence for page in page_blocks) / len(page_blocks) if page_blocks else 0.0
        )
        return RawOCRResult(
            full_text="\n\n".join(page.text for page in page_blocks),
            page_blocks=page_blocks,
            query_results=query_results,
            tables=self._parse_tables(blocks, by_id),
            overall_confidence=overall,
            low_confidence_pages=[
                page.page_number
                for page in page_blocks
                if page.confidence < self.confidence_threshold
            ],
        )

    def _combined_bbox(self, blocks: list[dict[str, Any]]) -> dict[str, float]:
        boxes = [block.get("Geometry", {}).get("BoundingBox", {}) for block in blocks]
        boxes = [box for box in boxes if box]
        if not boxes:
            return {}
        left = min(float(box.get("Left", 0)) for box in boxes)
        top = min(float(box.get("Top", 0)) for box in boxes)
        right = max(float(box.get("Left", 0)) + float(box.get("Width", 0)) for box in boxes)
        bottom = max(float(box.get("Top", 0)) + float(box.get("Height", 0)) for box in boxes)
        return {"left": left, "top": top, "width": right - left, "height": bottom - top}

    def _parse_tables(
        self, blocks: list[dict[str, Any]], by_id: dict[str, dict[str, Any]]
    ) -> list[ExtractedTable]:
        tables: list[ExtractedTable] = []
        for table in (block for block in blocks if block.get("BlockType") == "TABLE"):
            cell_ids = [
                child
                for relation in table.get("Relationships", [])
                if relation.get("Type") == "CHILD"
                for child in relation.get("Ids", [])
            ]
            cells = [by_id[str(cell_id)] for cell_id in cell_ids if str(cell_id) in by_id]
            row_count = max((int(cell.get("RowIndex", 0)) for cell in cells), default=0)
            column_count = max((int(cell.get("ColumnIndex", 0)) for cell in cells), default=0)
            rows = [["" for _ in range(column_count)] for _ in range(row_count)]
            for cell in cells:
                words = [
                    str(by_id[str(child)].get("Text", ""))
                    for relation in cell.get("Relationships", [])
                    if relation.get("Type") == "CHILD"
                    for child in relation.get("Ids", [])
                    if str(child) in by_id
                ]
                row_index = int(cell.get("RowIndex", 1)) - 1
                column_index = int(cell.get("ColumnIndex", 1)) - 1
                if 0 <= row_index < row_count and 0 <= column_index < column_count:
                    rows[row_index][column_index] = " ".join(words)
            tables.append(ExtractedTable(page=int(table.get("Page", 1)), rows=rows))
        return tables


class LLMFallback(Protocol):
    async def reextract(
        self, raw_result: RawOCRResult, document_type: DocumentType
    ) -> dict[str, Any]: ...


class NoOpLLMFallback:
    async def reextract(
        self, raw_result: RawOCRResult, document_type: DocumentType
    ) -> dict[str, Any]:
        del raw_result, document_type
        return {}


class BedrockLLMFallback:
    """Optional low-confidence fallback; AWS credentials come from the task role."""

    def __init__(self, region: str, model_id: str) -> None:
        self.client: Any = boto3.client("bedrock-runtime", region_name=region)
        self.model_id = model_id

    async def reextract(
        self, raw_result: RawOCRResult, document_type: DocumentType
    ) -> dict[str, Any]:
        prompt = (
            f"Extract {document_type.value} fields as a flat JSON object. "
            "Return JSON only. Document text follows:\n" + raw_result.full_text
        )
        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2048,
                "temperature": 0,
                "messages": [{"role": "user", "content": prompt}],
            }
        )
        response = await asyncio.to_thread(
            self.client.invoke_model,
            modelId=self.model_id,
            contentType="application/json",
            accept="application/json",
            body=body,
        )
        payload = json.loads(response["body"].read())
        return dict(json.loads(payload["content"][0]["text"]))
