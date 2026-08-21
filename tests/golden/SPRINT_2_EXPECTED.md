# Sprint 2 golden expectations

These outputs were documented before implementing the Sprint 2 golden tests. They reproduce the supplied sprint acceptance cases without adding or interpreting UCP rules.

| Case | Expected deterministic output |
|---|---|
| TC-01 | `COMPLIANT`, complete, zero findings. |
| TC-02 | `COMPLIANT`, zero findings; the configured Art. 30(a) about range permits 265,000 against 250,000. |
| TC-03 | `DISCREPANCY`, at least one `MATERIAL` Art. 30 amount/drawing finding. |
| TC-04 | `COMPLIANT`; 520 is within the configured 5% bulk tolerance around 500. |
| TC-05 | `DISCREPANCY`, `MATERIAL`, rule `UCP600-ART30B-QUANTITY-TOLERANCE`. |
| TC-06 | `DISCREPANCY`, `MATERIAL`, rule `UCP600-ART14C-PRESENTATION-PERIOD`; 25 days exceeds 21. |
| TC-07 | `COMPLIANT`; 25 days is within the credit-specific 30 days. |
| TC-08 | `INCOMPLETE`, insurance listed as missing, zero field-level findings. |
| TC-09 | `DISCREPANCY`, one `ADVISORY` Art. 14(d) vessel-name variation. |
| TC-10 | `DISCREPANCY`, one `MATERIAL` Art. 14(d) goods-description conflict. |

Every finding must contain a stable finding ID, rule ID, article, expected value, actual value, document/field/page provenance, evidence, severity, and rule version. No prohibited severity label is permitted.
