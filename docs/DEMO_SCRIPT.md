# TradeSentry — Live Demo Presentation Script
**Platform**: AI-Assisted Pre-Settlement Trade Finance Intelligence Layer  
**Target Environment**: GIFT City International Banking Units (IBUs)  
**Estimated Demo Duration**: 5–7 Minutes  

---

## 🎯 Executive Summary (Elevator Pitch — 30 Seconds)
> *"Trade finance powers global commerce, but banks face two massive challenges: slow manual documentary compliance under UCP 600 rules, and catastrophic fraud risks like duplicate invoice financing and Trade-Based Money Laundering (TBML).  
> **TradeSentry** is an AWS-native, human-authorized intelligence layer designed specifically for GIFT City IBUs. It automates multi-document OCR and UCP 600 compliance, generates Transaction DNA to cross-verify cargo details, checks privacy-preserving Cross-IBU registries to stop duplicate financing before settlement, and gives trade officers an explainable, auditable investigation console."*

---

## ⏱️ Step-by-Step Demo Flow

### Act 1: The Overview & Mission (0:00 – 1:00)
* **View**: `Dashboard` (`/`)
* **What to Show**:
  - Live KPI metrics (Active Cases, Awaiting Review, Risk Distribution).
  - Case Pipeline lifecycle: `Submitted` ➔ `Processing` ➔ `Compliance` ➔ `Investigation` ➔ `Review` ➔ `Ready`.
* **Talking Points**:
  - *"Welcome to TradeSentry. This platform serves as a pre-settlement co-pilot for Trade Finance Officers."*
  - *"Notice the core design principle: **Human-in-the-loop**. Risk scores are investigation signals, not automated settlement decisions. Every high-risk finding requires officer sign-off before downstream systems proceed."*

---

### Act 2: Document Ingestion & AWS Bedrock OCR (1:00 – 2:15)
* **View**: `Documents` (`/documents`) ➔ `Document Ingestion & Live Extraction`
* **Action**:
  - Upload or select a set of trade finance documents (Letter of Credit, Commercial Invoice, Bill of Lading, Certificate of Origin).
  - Click **Extract with AWS Bedrock**.
* **Talking Points**:
  - *"In traditional banking, an officer reviews 5 to 10 dense physical or PDF documents per LC presentation."*
  - *"TradeSentry uses **AWS Bedrock Claude 3.5 Sonnet** to extract critical fields with high confidence: LC reference, exporter/importer entities, HS codes, commodity pricing, ports of loading/discharge, and shipment deadlines."*
  - *"Notice that extracted values are typed, verified, and mapped directly to compliance fields."*

---

### Act 3: Deterministic UCP 600 Compliance Engine (2:15 – 3:30)
* **View**: `Trade Cases` (`/cases`) ➔ Select a Case ➔ Step 1–2 of Investigation
* **Talking Points**:
  - *"Large Language Models must NEVER invent or hallucinate banking rules. That is why TradeSentry uses a **deterministic, rule-based UCP 600 compliance engine**."*
  - *"Every compliance finding references the exact ICC UCP 600 article:"*
    - **Art. 18**: Commercial invoice description and currency matching.
    - **Art. 20**: Bill of Lading port of loading and discharge consistency.
    - **Art. 14 / 28**: Insurance coverage percentages and expiry validity.
  - *"The officer immediately sees: Expected Value vs Actual Document Value with exact evidence references."*

---

### Act 4: Transaction DNA & Cross-IBU Duplicate Detection (3:30 – 4:45)
* **View**: `Transaction DNA` (`/transaction-dna`) & `Cross-IBU Intelligence` (`/cross-ibu`)
* **Talking Points**:
  - *"One of the biggest systemic risks in trade finance is **duplicate financing** — where a rogue trader pledges the exact same cargo/Bill of Lading across three different banks in GIFT City."*
  - *"TradeSentry creates a **Transaction DNA Profile** — normalized cryptographic fingerprints of the B/L number, vessel, shipment date, and exporter."*
  - *"Through our **Cross-IBU Intelligence Registry** (backed by Amazon DynamoDB GSIs), banks can query shared trade fingerprints without exposing confidential customer PII."*
  - *"If another IBU in GIFT City has already registered this Bill of Lading, TradeSentry raises an instant high-priority duplicate flag."*

---

### Act 5: TBML Investigation & Officer Authorization (4:45 – 6:00)
* **View**: `Investigations` (`/investigations` or Case detail triage console)
* **Talking Points**:
  - *"For complex cases, our constrained investigation engine executes 4 specialized fraud tools:"*
    1. **Price Benchmarking**: Compares unit pricing against corridor P90 historical benchmarks to detect over/under-invoicing.
    2. **Vessel Verification**: Cross-references AIS vessel routes and carrier schedules.
    3. **Sanctions & Entity Screening**: Screen counterparties against global watchlists.
    4. **Duplicate Financing Check**: Confirms registry status across IBUs.
  - *"Every step generates an immutable audit log entry in the audit trail (`/audit`)."*
  - *"Finally, the Trade Officer reviews the findings and issues a formal decision: **Approve Presentation**, **Request Discrepancy Notice**, or **Escalate for Secondary Review**."*

---

## 🛡️ Key Architectural & Regulatory Guardrails (Q&A Highlights)

1. **Why is settlement not executed automatically?**
   - *Rule 2 & 8: TradeSentry is pre-settlement intelligence. FCSS is downstream settlement infrastructure. Human approval is mandatory for every consequential decision.*
2. **How is privacy protected across banks?**
   - *Cross-IBU queries use normalized cryptographic hashes and indexed attributes; raw document contents, secrets, and customer PII are never broadcast across units.*
3. **What is the AWS infrastructure footprint?**
   - *Containerized Next.js frontend deployed via **AWS App Runner**, backend on **ECS Fargate / FastAPI**, **Amazon DynamoDB** for registry lookups, **Amazon S3 with KMS envelope encryption** for documents, and **AWS Bedrock (Claude 3.5 Sonnet)** for document intelligence.*

---

## 🎤 Closing Statement (15 Seconds)
> *"TradeSentry transforms hours of high-risk documentary checking into minutes of verifiable, auditable intelligence — protecting GIFT City banking units against multi-million dollar trade fraud while preserving strict UCP 600 compliance."*
