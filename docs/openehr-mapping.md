# SevaHealth AI: openEHR & EHRbase Mapping Specification

**Document Version:** 1.0.0  
**Target:** SevaHealth AI Platform  
**Standard Alignments:** openEHR Release 1.0.4, HL7 FHIR R4, ABDM (Ayushman Bharat Digital Mission)  
**Implementation Adapter:** `ClinicalRepository` (`PostgreSQLRepository`, `OpenEHRRepository`, `HybridClinicalRepository`)

---

## 1. Multi-Tier Healthcare Data Architecture

A common architectural antipattern in digital health is forcing every operational and binary asset into openEHR. SevaHealth AI enforces a **purpose-fit, multi-tier data architecture**:

```
+----------------------------------------------------------------------------------------------------+
|                                    SEVAHEALTH AI API GATEWAY                                       |
+----------------------------------------------------------------------------------------------------+
       |                     |                        |                     |                  |
       v                     v                        v                     v                  v
+--------------+     +---------------+        +---------------+     +---------------+   +--------------+
| OPERATIONAL  |     | LONGITUDINAL  |        | BINARY / DOCS |     | WEARABLE DATA |   |  ANALYTICS   |
|     DATA     |     | CLINICAL DATA |        |     VAULT     |     |     LAYER     |   | PROJECTIONS  |
| (PostgreSQL) |     |   (openEHR)   |        |  (FileNest /  |     |   (Timescale/ |   |  (Regional   |
|              |     |   (EHRbase)   |        |    MinIO)     |     |     Redis)    |   |     DB)      |
+--------------+     +---------------+        +---------------+     +---------------+   +--------------+
| - IAM Users  |     | - Vital Signs |        | - PDF Reports |     | - 1Hz-100Hz   |   | - District   |
| - Sessions   |     | - Lab Results |        | - Scans/DICOM |     |   Raw PPG     |   |   Prevalence |
| - Passwords  |     | - Clinical    |        | - Discharge   |     | - Step Counts |   | - Risk Tier  |
| - Consents   |     |   Encounters  |        |   Summaries   |     | - Sleep Stage |   |   Breakdowns |
| - Audit logs |     |   (SOAP)      |        | - Raw Sensor  |     |   Timeseries  |   | - Outcome    |
| - App State  |     | - Care Plans  |        |   Dumps       |     | - R-R Intervals|   |   Deltas     |
+--------------+     +---------------+        +---------------+     +---------------+   +--------------+
```

### Storage Responsibilities:
1. **Operational Data → PostgreSQL**:
   - High-throughput identity transactions, session tokens, password hashes, consent directives, audit entries, UI configuration, and background task states.
2. **Longitudinal Clinical Data → openEHR / EHRbase**:
   - Vendor-neutral, computable longitudinal electronic health records structured into semantic clinical archetypes and compositions.
3. **Documents → Object Storage (FileNest / MinIO)**:
   - High-volume binary files (diagnostic PDF reports, radiological scans, prescriptions) referenced by `Document` and `DocumentReference` metadata.
4. **Wearable Time Series → Wearable Data Layer**:
   - Minute-by-minute streaming telemetry (continuous heart rate, HRV rMSSD, step counters, sleep epoch minutes) suited for time-series optimization.
5. **Analytics Projections → Analytics Store**:
   - De-identified epidemiological metrics, district risk breakdowns, and intervention outcome deltas generated from pre-aggregated analytical pipelines.

---

## 2. Patient / EHR Identifier Mapping

openEHR decouples demographic identity from clinical records through the `EHR_STATUS` subject reference.

```
Citizen Record (SevaHealth)
  ├── ID: "citizen-ramesh-patel-01"
  └── ABHA ID: "91-4829-1029-4820"
            │
            ▼
openEHR EHR_STATUS (EHRbase)
  ├── namespace: "in.gov.abdm" (or "in.sevahealth.ai")
  ├── scheme: "in.gov.abdm"
  ├── value: "91-4829-1029-4820"
  └── type: "PERSON"
            │
            ▼
openEHR EHR Identifier (EHRbase)
  └── ehr_id: "e43b1842-8821-4f10-9102-482019284012"
```

* **ABDM Alignment:** When an ABHA ID is present, the namespace is set to `in.gov.abdm`.
* **State / Local Fallback:** For unregistered citizens, the namespace defaults to `in.sevahealth.ai` with the internal UUID.

---

## 3. openEHR Archetype & Composition Mapping Catalog

### 3.1. Physical Vital Signs (`openEHR-EHR-COMPOSITION.encounter.v1`)

| Domain Model Property | openEHR Archetype ID | Archetype Node | Data Type | Units / Encoding |
|---|---|---|---|---|
| `SYSTOLIC_BP` | `openEHR-EHR-OBSERVATION.blood_pressure.v2` | `at0004` (Systolic) | `DV_QUANTITY` | `mmHg` |
| `DIASTOLIC_BP` | `openEHR-EHR-OBSERVATION.blood_pressure.v2` | `at0005` (Diastolic)| `DV_QUANTITY` | `mmHg` |
| `HEART_RATE` | `openEHR-EHR-OBSERVATION.pulse.v1` | `at0004` (Rate) | `DV_QUANTITY` | `/min` or `bpm` |
| `BMI` | `openEHR-EHR-OBSERVATION.body_mass_index.v2` | `at0004` (BMI) | `DV_QUANTITY` | `kg/m2` |
| `WAIST_CIRCUMFERENCE` | `openEHR-EHR-OBSERVATION.waist_circumference.v1` | `at0004` (Waist) | `DV_QUANTITY` | `cm` |

### 3.2. Diagnostic Laboratory Results (`openEHR-EHR-COMPOSITION.report-result.v1`)

| Test Name | LOINC Code | openEHR Archetype | Element | Target Units |
|---|---|---|---|---|
| `FASTING_BLOOD_GLUCOSE` | `1558-6` | `openEHR-EHR-OBSERVATION.laboratory_test_result.v1` | `at0001` (Result value) | `mg/dL` |
| `HBA1C` | `4548-4` | `openEHR-EHR-OBSERVATION.laboratory_test_result.v1` | `at0001` (Result value) | `%` |
| `TOTAL_CHOLESTEROL` | `2093-3` | `openEHR-EHR-OBSERVATION.laboratory_test_result.v1` | `at0001` (Result value) | `mg/dL` |
| `TRIGLYCERIDES` | `2571-8` | `openEHR-EHR-OBSERVATION.laboratory_test_result.v1` | `at0001` (Result value) | `mg/dL` |
| `HDL_CHOLESTEROL` | `2085-9` | `openEHR-EHR-OBSERVATION.laboratory_test_result.v1` | `at0001` (Result value) | `mg/dL` |
| `SERUM_CREATININE` | `2160-0` | `openEHR-EHR-OBSERVATION.laboratory_test_result.v1` | `at0001` (Result value) | `mg/dL` |

### 3.3. Clinical Consultation Encounters (`openEHR-EHR-COMPOSITION.encounter.v1`)

Structured SOAP clinical notes map to `openEHR-EHR-SECTION.soap.v1`:
* **`Subjective`**: Patient reported symptoms, lifestyle adherence, dietary barriers.
* **`Objective`**: Physical measurements and validated POCT laboratory results.
* **`Assessment`**: Clinical diagnosis and multi-factor NCD progression staging.
* **`Plan`**: Preventive medicine prescriptions, dietary modifications, follow-up schedule.

### 3.4. Longitudinal Preventive Care Plans (`openEHR-EHR-COMPOSITION.care_plan.v1`)

Persistent openEHR composition capturing:
* Lead clinician identifier (`composer.name`).
* Care plan title and protocol narrative (`openEHR-EHR-INSTRUCTION.care_plan.v1`).
* Longitudinal lifecycle status (`ACTIVE`, `COMPLETED`, `SUSPENDED`).

---

## 4. Provenance & Audit Alignment

Every composition includes openEHR `audit_details`:
* **`system_id`**: `sevahealth.karnataka.in`
* **`committer`**: Identified healthcare worker or physician (`PARTY_IDENTIFIED`)
* **`time_committed`**: ISO-8601 UTC timestamp
* **`change_type`**: `creation` (initial observation) or `amendment`

---

## 5. AQL Query Catalog

### 5.1. Retrieve Longitudinal Blood Pressure History for Patient
```sql
SELECT
    c/context/start_time/value as encounter_time,
    obs/data[at0001]/events[at0002]/data[at0003]/items[at0004]/value/magnitude as systolic,
    obs/data[at0001]/events[at0002]/data[at0003]/items[at0005]/value/magnitude as diastolic
FROM EHR e
CONTAINS COMPOSITION c[openEHR-EHR-COMPOSITION.encounter.v1]
CONTAINS OBSERVATION obs[openEHR-EHR-OBSERVATION.blood_pressure.v2]
WHERE e/ehr_id/value = 'e43b1842-8821-4f10-9102-482019284012'
ORDER BY c/context/start_time/value DESC
```

### 5.2. Retrieve Fasting Glucose & HbA1c Lab Trends
```sql
SELECT
    c/context/start_time/value as test_time,
    obs/data[at0001]/events[at0002]/data[at0003]/items[at0005]/value/defining_code/code_string as loinc_code,
    obs/data[at0001]/events[at0002]/data[at0003]/items[at0001]/value/magnitude as test_value,
    obs/data[at0001]/events[at0002]/data[at0003]/items[at0001]/value/units as test_unit
FROM EHR e
CONTAINS COMPOSITION c
CONTAINS OBSERVATION obs[openEHR-EHR-OBSERVATION.laboratory_test_result.v1]
WHERE e/ehr_id/value = 'e43b1842-8821-4f10-9102-482019284012'
ORDER BY c/context/start_time/value DESC
```
