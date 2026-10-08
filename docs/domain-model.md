# SevaHealth AI: Clinical Domain Model & Longitudinal Data Architecture

**Document Version:** 1.1.0  
**Target:** SevaHealth AI Platform  
**Standard Alignments:** HL7 FHIR R4, openEHR Archetypes, Ayushman Bharat Digital Mission (ABDM), ICMR-INDIAB Guidelines, WHO Package of Essential NCD Interventions (WHO PEN)  
**Verification:** Formally verified via Pydantic schemas, PostgreSQL migrations, synthetic seed fixtures, and automated test suites (`tests/test_domain_models.py`).

---

## 1. Domain Architecture Overview

SevaHealth AI is designed as a **preventive-health and early-warning decision-intelligence platform**. Clinical data is modeled with strict healthcare safety principles:
1. **Never store measurements without units and timestamps.**
2. **Support immutable longitudinal history** (measurements form an append-only event series; previous observations are never overwritten).
3. **Capture comprehensive provenance and quality/confidence** for every observation.
4. **Partition by organization, jurisdiction, and risk domain** for rapid population queries.

```
                              +-------------------------+
                              |      Organization       |
                              +------------+------------+
                                           | 1
                                           | *
                              +------------v------------+
                              |        CareTeam         |
                              +------------+------------+
                                           | 1
                                           | *
                              +------------v------------+
                              |         Patient         |
                              +------------+------------+
                                           | 1
       +-------------------+---------------+-------------------+-------------------+
       | 1                 | 1                                 | 1                 | 1
+------v------+     +------v------+                     +------v------+     +------v------+
|   Profile   |     |LifestyleProf|                     |FamilyHistory|     |   Consent   |
+-------------+     +-------------+                     +-------------+     +-------------+
       |
       | 1
       | *
+------v----------------------------------------------------------------------------------+
|                           LONGITUDINAL CLINICAL EVENT STREAM                             |
|  - VitalSign             (SYSTOLIC_BP, DIASTOLIC_BP, WAIST, BMI, HR)                    |
|  - LabResult             (FASTING_GLUCOSE, HBA1C, LIPIDS, CREATININE, eGFR)             |
|  - WearableObservation   (RESTING_HR, HRV_RMSSD, DAILY_STEPS, SLEEP_MINUTES)            |
|  - Screening             (Administered CBAC, IDRS, Community Camp Sessions)             |
|  - ScreeningResult       (Scored CBAC >= 4, IDRS >= 60, Immediate Referral Needed)      |
|  - RiskAssessment        (Composite Score, Domain Tiers: DM, HTN, CVD, MASLD, CKD)      |
|  - RiskFactorContribution(Attribution Waterfall: Observed vs Target, + / - Weights)    |
|  - RiskTrajectory        (DETERIORATING, STABLE, IMPROVING, Rate of Change)             |
|  - InterventionPlan      (30-Day Preventive Journey, Pillar Prescriptions)              |
|  - Intervention          (Nutrition, Physical Activity, Sleep, Stress Guidance)         |
|  - Goal                  (Biomarker & Activity Milestones with Target Dates)            |
|  - CheckIn               (Daily Habit Completions, Subjective Wellbeing)                |
|  - Medication            (Active Prescriptions, Indication, Dosage, Prescriber)         |
|  - MedicationAdherence   (Daily Scheduled vs Taken Logs, Omission Reasons)              |
|  - ClinicalEncounter     (SOAP Notes, Diagnosis, Physical Consults, Tele-triage)        |
|  - CarePlan              (Multi-disciplinary Longitudinal Team Plan)                    |
|  - Referral              (Urgent / Emergent Escalations to PHC / CHC / District Hosp)   |
|  - Alert                 (Clinical Rule Violations, Hypertensive Spikes)                |
|  - Notification          (Citizen Reminders, SMS, WhatsApp, In-App Alerts)              |
|  - DocumentReference     (Diagnostic Lab Reports, Discharge Summaries, PDFs)            |
|  - AuditEvent            (Forensic Immutable Ledger: Actor, Tenant, Action, Resource)   |
+-----------------------------------------------------------------------------------------+
```

---

## 2. Complete 31 Domain Entity Catalog

### 2.1. Structural & Administrative Entities
1. **`Organization`**: Hierarchy of healthcare entities (`STATE_HEALTH_MISSION`, `DISTRICT_HEALTH_OFFICE`, `PHC`, `CHC`). Includes `jurisdiction` string and self-referencing `parent_organization_id`.
2. **`CareTeam`**: Community or clinical multidisciplinary team linked to an organization, assigned to specific jurisdictions (e.g., "Ward 12 NCD Prevention Cell").
3. **`Patient`**: Core platform subject linked to `organization_id`, `user_id`, optional `primary_care_team_id`, and national `abha_id`.
4. **`Profile`**: Demographics, address, and geographic binning (`state`, `district`, `sub_district`, `village_or_ward`, `socioeconomic_tier`).

### 2.2. Clinical History & Baseline Entities
5. **`FamilyHistory`**: Hereditary predisposition tracking relationship (`FATHER`, `MOTHER`, `SIBLING`), condition codes (`DIABETES_MELLITUS_TYPE_2`, `HYPERTENSION`), and age of onset.
6. **`LifestyleProfile`**: Tobacco use, alcohol consumption, dietary patterns (`HIGH_CARB_HIGH_SALT`), weekly physical activity levels, nightly sleep duration, and perceived stress.
7. **`RiskFactor`**: Identified active and historical clinical risk conditions (`IMPAIRED_FASTING_GLYCEMIA`, `CENTRAL_VISCERAL_ADIPOSITY`) with severity levels (`MILD`, `MODERATE`, `HIGH`, `CRITICAL`).

### 2.3. Longitudinal Clinical Measurement Entities
Enforces: **Never store clinical measurements without units and timestamps.**
8. **`VitalSign`**:
   - `clinical_type`: `SYSTOLIC_BP`, `DIASTOLIC_BP`, `HEART_RATE`, `BMI`, `WAIST_CIRCUMFERENCE`, `SPO2`, etc.
   - `value`: Numeric biomarker reading.
   - `unit`: Mandatory clinical unit (e.g. `mmHg`, `bpm`, `kg/m2`, `cm`).
   - `measurement_timestamp`: Mandatory exact UTC timestamp.
   - `source`: Clinical origin (`CLINIC_VISIT`, `COMMUNITY_HEALTH_CAMP`, `ASHA_HOME_SCREENING`).
   - `provenance`: `ProvenanceRecord` containing `recorder_id`, `recorder_role`, `device_model`, `device_id`, `capture_method`.
   - `confidence_score`: Sensor or capture quality score ($0.00 \le c \le 1.00$).
9. **`LabResult`**:
   - Diagnostic chemistry and hematology tests (`FASTING_BLOOD_GLUCOSE`, `HBA1C`, `TRIGLYCERIDES`, `HDL`, `LDL`, `CREATININE`).
   - Includes standard `loinc_code`, reference range, and interpretation tag (`NORMAL`, `BORDERLINE`, `ELEVATED`, `CRITICAL`).
10. **`WearableObservation`**:
    - High-frequency smartwatch biometric time series (`RESTING_HEART_RATE`, `HRV_RMSSD`, `DAILY_STEPS`, `SLEEP_DURATION_MINUTES`).
    - Stamped with mandatory unit, measurement timestamp, device provenance, confidence score, and rolling 7-day baselines.

### 2.4. Medication & Adherence Entities
11. **`Medication`**: Active and historical pharmacological interventions (`drug_name`, `dosage`, `frequency`, `indication`, `prescribed_by`, `start_date`, `end_date`).
12. **`MedicationAdherence`**: Longitudinal scheduled-vs-taken logs for calculating proportion of days covered (PDC) and identifying early non-compliance.

### 2.5. Screening & Risk Stratification Entities
13. **`Screening`**: Field or clinic screening encounters administered by ASHA workers or ANMs (`screening_type`, `location`, `screened_at`).
14. **`ScreeningResult`**: Standardized scoring calculators output (CBAC score $\ge 4$, IDRS score $\ge 60$) with referral triggers.
15. **`RiskAssessment`**: Comprehensive multi-factor NCD stratification ($0.0 \dots 1.0$ composite score, tier, and domain scores across Diabetes, Hypertension, CVD, Metabolic, CKD, MASLD). Stamped with mandatory non-diagnostic disclaimer.
16. **`RiskFactorContribution`**: Explainable waterfall attributions (SHAP-style drivers and protective factors with observed vs. target metrics and evidence guideline citations).
17. **`RiskTrajectory`**: Longitudinal risk velocity tracking progression trend (`IMPROVING`, `STABLE`, `DETERIORATING`), rate of change, and 6-month projected tier.

### 2.6. Preventive Interventions & Daily Tracking
18. **`InterventionPlan`**: 30-day preventive health journey targeting specific risk domains with calculated adherence percentage.
19. **`Intervention`**: Pillar-specific lifestyle prescriptions (`NUTRITION`, `PHYSICAL_ACTIVITY`, `SLEEP_HYGIENE`, `STRESS_AND_LIFESTYLE`).
20. **`Goal`**: Measurable clinical and behavioral milestone targets with baseline, target, and target date.
21. **`CheckIn`**: Citizen daily habit check-off logs tracking task completion count and subjective wellbeing.

### 2.7. Device Connectivity & Wearables
22. **`WearableConnection`**: Smartwatch integration record (Noise, Fire-Boltt, Apple, Fitbit, Garmin) with sync status and battery/connection health.

### 2.8. Clinical Governance & Care Coordination
23. **`ClinicalEncounter`**: Formal physical or tele-consultation encounters containing structured SOAP notes (`subjective`, `objective`, `assessment`, `plan`).
24. **`CarePlan`**: Comprehensive multi-disciplinary care coordination plan linking lead clinicians and care teams.
25. **`Referral`**: Clinical escalation routing from community screening camps to PHC medical officers or district hospitals (`urgency`, `reason`, `status`).
26. **`Alert`**: Automated decision-support trigger detecting clinical threshold violations (e.g., BP $\ge 160/100$ mmHg, rapid glycemic deterioration).
27. **`Notification`**: Outbound citizen nudges and clinical alerts across push, SMS, WhatsApp, and in-app channels.

### 2.9. Consent, Documents & Forensic Audits
28. **`Consent`**: ABDM-aligned granular consent directives granting time-bound provider access with revocation rights.
29. **`Document`**: Secure binary storage metadata (PDF lab reports, ECG recordings) with SHA-256 hash and size.
30. **`DocumentReference`**: Clinical metadata and parsed JSON entities extracted from uploaded clinical documents.
31. **`AuditEvent`**: Immutable forensic audit log tracking every data access, modification, export, or AI generation event.

---

## 3. Longitudinal History & Non-Overwrite Guarantees

In healthcare, overwriting past observations is a critical data-integrity violation. SevaHealth AI enforces:
* **Append-Only Time Series:** Every vital sign, lab result, and wearable reading receives a unique UUID (`id`) and immutable UTC timestamp (`measurement_timestamp`).
* **Chronological Trend Queries:** Temporal queries sort by `measurement_timestamp DESC`, allowing algorithms and clinicians to visualize improvement or deterioration trajectories over time.
* **Preservation of Baselines:** Initial high-risk readings are preserved as historical context, enabling calculation of true Intervention Outcome Deltas (e.g., systolic BP reductions over 30 days).

---

## 4. Production Indexing Strategy

The PostgreSQL migration establishes dedicated B-tree and composite indexes across six mission-critical query access patterns:

| Index Category | SQL Index Definition | Primary Query Use Case |
|---|---|---|
| **1. Patient Index** | `vital_signs(patient_id, measurement_timestamp DESC)`<br>`lab_results(patient_id, measurement_timestamp DESC)`<br>`wearable_observations(patient_id, measurement_timestamp DESC)`<br>`risk_assessments(patient_id, assessed_at DESC)` | Instant retrieval of a citizen's longitudinal health record and chart history. |
| **2. Timestamp Index** | `vital_signs(measurement_timestamp DESC)`<br>`lab_results(measurement_timestamp DESC)`<br>`wearable_observations(measurement_timestamp DESC)`<br>`audit_events(created_at DESC)` | High-throughput time-window analytics, batch aggregations, and forensic audits. |
| **3. Clinical Type Index**| `vital_signs(clinical_type, measurement_timestamp DESC)`<br>`lab_results(test_name, measurement_timestamp DESC)`<br>`lab_results(loinc_code)`<br>`wearable_observations(metric_type, measurement_timestamp DESC)` | Domain-specific trend extraction (e.g., retrieving all systolic BP readings for a cohort). |
| **4. Risk Domain Index** | `risk_factors(domain, severity)`<br>`risk_assessments(overall_tier, assessed_at DESC)`<br>`intervention_plans(primary_domain)` | Rapid population risk stratification and high-risk triage filtering. |
| **5. Organization Index** | `patients(organization_id)`<br>`care_teams(organization_id)`<br>`audit_events(organization_id, created_at DESC)` | Multi-tenant scoping and cross-tenant boundary isolation. |
| **6. Geography Index** | `profiles(state, district, sub_district, village_or_ward)`<br>`organizations(jurisdiction)`<br>`care_teams(jurisdiction)` | District, taluk, and ward-level epidemiological heatmaps and ASHA worker routing. |

---

## 5. Artifacts & Code References

1. **Pydantic Domain Schemas:** [`packages/clinical_models/domain_models.py`](file:///d:/Kalyan/SevaFirst%20AI/sevahealth-ai/packages/clinical_models/domain_models.py)
2. **Re-export Module:** [`packages/clinical_models/__init__.py`](file:///d:/Kalyan/SevaFirst%20AI/sevahealth-ai/packages/clinical_models/__init__.py)
3. **PostgreSQL Migration DDL:** [`infrastructure/postgres/migrations/001_initial_domain_model.sql`](file:///d:/Kalyan/SevaFirst%20AI/sevahealth-ai/infrastructure/postgres/migrations/001_initial_domain_model.sql)
4. **PostgreSQL Entrypoint:** [`infrastructure/postgres/init.sql`](file:///d:/Kalyan/SevaFirst%20AI/sevahealth-ai/infrastructure/postgres/init.sql)
5. **Synthetic Demo Fixtures SQL:** [`infrastructure/postgres/seeds/001_synthetic_fixtures.sql`](file:///d:/Kalyan/SevaFirst%20AI/sevahealth-ai/infrastructure/postgres/seeds/001_synthetic_fixtures.sql)
6. **Synthetic Dataset Generator:** [`scripts/seed_domain_fixtures.py`](file:///d:/Kalyan/SevaFirst%20AI/sevahealth-ai/scripts/seed_domain_fixtures.py)
7. **Domain Model Test Suite:** [`tests/test_domain_models.py`](file:///d:/Kalyan/SevaFirst%20AI/sevahealth-ai/tests/test_domain_models.py) (9 dedicated tests passing, 47 platform tests total).
