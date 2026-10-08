-- ==============================================================================
-- SevaHealth AI: Clinical Domain Model Schema & Longitudinal Event Store
-- Migration: 001_initial_domain_model.sql
-- Standards: HL7 FHIR R4, openEHR Archetypes, ABDM, DISHA Healthcare Privacy
-- ==============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

SET timezone = 'UTC';

-- 1. Organizations (Administrative Health Hierarchy)
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(64) NOT NULL, -- STATE_HEALTH_MISSION | DISTRICT_HEALTH_OFFICE | PHC | CHC
    jurisdiction VARCHAR(255) NOT NULL, -- "Karnataka", "Mysuru District", "Ward 12"
    parent_organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Care Teams
CREATE TABLE IF NOT EXISTS care_teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    jurisdiction VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS care_team_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    care_team_id UUID NOT NULL REFERENCES care_teams(id) ON DELETE CASCADE,
    user_id VARCHAR(128) NOT NULL,
    role VARCHAR(64) NOT NULL,
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(32),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Patients
CREATE TABLE IF NOT EXISTS patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    abha_id VARCHAR(64) UNIQUE,
    user_id VARCHAR(128) UNIQUE,
    primary_care_team_id UUID REFERENCES care_teams(id) ON DELETE SET NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. Profiles (Demographics & Geographic Allocation)
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL UNIQUE REFERENCES patients(id) ON DELETE CASCADE,
    first_name VARCHAR(128) NOT NULL,
    last_name VARCHAR(128) NOT NULL,
    birth_date DATE NOT NULL,
    gender VARCHAR(16) NOT NULL,
    phone VARCHAR(32) NOT NULL,
    email VARCHAR(128),
    address_line TEXT,
    state VARCHAR(64) NOT NULL DEFAULT 'Karnataka',
    district VARCHAR(64) NOT NULL DEFAULT 'Mysuru',
    sub_district VARCHAR(64) NOT NULL DEFAULT 'Nanjangud',
    village_or_ward VARCHAR(128) NOT NULL DEFAULT 'Ward 4',
    primary_language VARCHAR(16) NOT NULL DEFAULT 'en',
    socioeconomic_tier VARCHAR(32) DEFAULT 'BPL',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. Family History
CREATE TABLE IF NOT EXISTS family_histories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    relative_relationship VARCHAR(64) NOT NULL, -- FATHER | MOTHER | SIBLING
    condition_code VARCHAR(64) NOT NULL,        -- DIABETES_MELLITUS_TYPE_2 | HYPERTENSION
    condition_name VARCHAR(255) NOT NULL,
    age_at_onset INT,
    is_deceased BOOLEAN NOT NULL DEFAULT FALSE,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. Lifestyle Profiles
CREATE TABLE IF NOT EXISTS lifestyle_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    tobacco_use VARCHAR(64) NOT NULL,         -- NEVER | FORMER | CURRENT_SMOKER | CHEWING_TOBACCO
    alcohol_use VARCHAR(64) NOT NULL,         -- NONE | OCCASIONAL | REGULAR | HEAVY
    dietary_pattern VARCHAR(64) NOT NULL,     -- BALANCED | HIGH_CARB_HIGH_SALT | HIGH_PROCESSED
    physical_activity_level VARCHAR(64) NOT NULL, -- SEDENTARY | MODERATE_150_MIN_WK | VIGOROUS
    sleep_hours_per_night NUMERIC(4,2) NOT NULL CHECK (sleep_hours_per_night >= 0 AND sleep_hours_per_night <= 24),
    perceived_stress_level VARCHAR(32) NOT NULL DEFAULT 'MODERATE',
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 7. Risk Factors (Active & Historical Domain Markers)
CREATE TABLE IF NOT EXISTS risk_factors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    domain VARCHAR(64) NOT NULL,              -- DIABETES | HYPERTENSION | CARDIOVASCULAR | METABOLIC | CKD | FATTY_LIVER
    name VARCHAR(255) NOT NULL,
    severity VARCHAR(32) NOT NULL DEFAULT 'MODERATE', -- MILD | MODERATE | HIGH | CRITICAL
    identified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- ==============================================================================
-- LONGITUDINAL CLINICAL MEASUREMENT TABLES (IMMUTABLE APPEND-ONLY STORE)
-- Enforces mandatory patient, value, unit, measurement_timestamp, source,
-- provenance, and confidence score. Never overwritten.
-- ==============================================================================

-- 8. Vital Signs
CREATE TABLE IF NOT EXISTS vital_signs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    clinical_type VARCHAR(64) NOT NULL,       -- SYSTOLIC_BP | DIASTOLIC_BP | HEART_RATE | BMI | WAIST_CIRCUMFERENCE
    value NUMERIC(10,3) NOT NULL,
    unit VARCHAR(32) NOT NULL CHECK (length(trim(unit)) > 0),
    measurement_timestamp TIMESTAMPTZ NOT NULL,
    source VARCHAR(64) NOT NULL,              -- CLINIC_VISIT | COMMUNITY_HEALTH_CAMP | ASHA_HOME_SCREENING
    provenance JSONB NOT NULL,                -- {recorder_id, recorder_role, device_model, device_id}
    confidence_score NUMERIC(3,2) NOT NULL DEFAULT 1.00 CHECK (confidence_score >= 0.00 AND confidence_score <= 1.00),
    is_flagged_abnormal BOOLEAN NOT NULL DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 9. Lab Results
CREATE TABLE IF NOT EXISTS lab_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    test_name VARCHAR(128) NOT NULL,          -- FASTING_BLOOD_GLUCOSE | HBA1C | TOTAL_CHOLESTEROL | TRIGLYCERIDES
    loinc_code VARCHAR(32) NOT NULL,
    value NUMERIC(10,3) NOT NULL,
    unit VARCHAR(32) NOT NULL CHECK (length(trim(unit)) > 0),
    reference_range VARCHAR(64) NOT NULL,
    interpretation VARCHAR(32) NOT NULL DEFAULT 'NORMAL', -- NORMAL | BORDERLINE | ELEVATED | CRITICAL
    measurement_timestamp TIMESTAMPTZ NOT NULL,
    source VARCHAR(64) NOT NULL,              -- PHC_DIAGNOSTIC_LAB | COMMUNITY_POCT_DEVICE
    provenance JSONB NOT NULL,
    confidence_score NUMERIC(3,2) NOT NULL DEFAULT 1.00 CHECK (confidence_score >= 0.00 AND confidence_score <= 1.00),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 10. Medications
CREATE TABLE IF NOT EXISTS medications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    drug_name VARCHAR(255) NOT NULL,
    dosage VARCHAR(64) NOT NULL,
    frequency VARCHAR(64) NOT NULL,
    indication VARCHAR(255) NOT NULL,
    prescribed_by VARCHAR(128) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 11. Medication Adherence Logs
CREATE TABLE IF NOT EXISTS medication_adherences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    medication_id UUID NOT NULL REFERENCES medications(id) ON DELETE CASCADE,
    scheduled_date DATE NOT NULL,
    taken BOOLEAN NOT NULL,
    reported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reason_skipped TEXT
);

-- 12. Screenings
CREATE TABLE IF NOT EXISTS screenings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    screening_type VARCHAR(64) NOT NULL,      -- NCD_COMPREHENSIVE_CBAC | IDRS_DIABETES_RISK
    administered_by VARCHAR(128) NOT NULL,
    administrator_role VARCHAR(64) NOT NULL,
    location VARCHAR(255) NOT NULL,
    screened_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 13. Screening Results
CREATE TABLE IF NOT EXISTS screening_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    screening_id UUID NOT NULL UNIQUE REFERENCES screenings(id) ON DELETE CASCADE,
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    cbac_score INT,
    idrs_score INT,
    needs_immediate_referral BOOLEAN NOT NULL DEFAULT FALSE,
    summary_findings TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 14. Risk Assessments
CREATE TABLE IF NOT EXISTS risk_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    screening_id UUID REFERENCES screenings(id) ON DELETE SET NULL,
    overall_score NUMERIC(5,4) NOT NULL CHECK (overall_score >= 0.0000 AND overall_score <= 1.0000),
    overall_tier VARCHAR(32) NOT NULL,        -- LOW | MODERATE | HIGH | CRITICAL
    domain_scores JSONB NOT NULL DEFAULT '{}'::jsonb,
    clinical_safety_disclaimer TEXT NOT NULL,
    assessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 15. Risk Factor Contributions (Explainability Waterfall)
CREATE TABLE IF NOT EXISTS risk_factor_contributions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    risk_assessment_id UUID NOT NULL REFERENCES risk_assessments(id) ON DELETE CASCADE,
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    factor_name VARCHAR(255) NOT NULL,
    factor_category VARCHAR(64) NOT NULL,     -- BIOMETRIC | LIFESTYLE | DEMOGRAPHIC
    observed_value VARCHAR(128) NOT NULL,
    target_value VARCHAR(128) NOT NULL,
    relative_weight NUMERIC(6,4) NOT NULL,
    is_protective BOOLEAN NOT NULL DEFAULT FALSE,
    evidence_guideline TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 16. Risk Trajectories
CREATE TABLE IF NOT EXISTS risk_trajectories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    assessment_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    historical_scores JSONB NOT NULL DEFAULT '[]'::jsonb,
    trend VARCHAR(32) NOT NULL,               -- IMPROVING | STABLE | DETERIORATING
    rate_of_change NUMERIC(6,4) NOT NULL DEFAULT 0.0000,
    projected_tier_6m VARCHAR(32) NOT NULL,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 17. Intervention Plans
CREATE TABLE IF NOT EXISTS intervention_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    risk_assessment_id UUID REFERENCES risk_assessments(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    primary_domain VARCHAR(64) NOT NULL,
    duration_days INT NOT NULL DEFAULT 30,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    adherence_rate NUMERIC(5,2) NOT NULL DEFAULT 0.00 CHECK (adherence_rate >= 0.00 AND adherence_rate <= 100.00),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 18. Interventions (Pillar Prescriptions)
CREATE TABLE IF NOT EXISTS interventions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID NOT NULL REFERENCES intervention_plans(id) ON DELETE CASCADE,
    pillar VARCHAR(64) NOT NULL,              -- NUTRITION | PHYSICAL_ACTIVITY | SLEEP_HYGIENE | STRESS_AND_LIFESTYLE
    title VARCHAR(255) NOT NULL,
    prescription_text TEXT NOT NULL,
    frequency VARCHAR(64) NOT NULL,
    target_metric VARCHAR(128) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 19. Goals
CREATE TABLE IF NOT EXISTS goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    plan_id UUID REFERENCES intervention_plans(id) ON DELETE SET NULL,
    metric_name VARCHAR(64) NOT NULL,
    baseline_value NUMERIC(10,3) NOT NULL,
    target_value NUMERIC(10,3) NOT NULL,
    target_date DATE NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'IN_PROGRESS', -- IN_PROGRESS | ACHIEVED | MISSED
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 20. Check-Ins
CREATE TABLE IF NOT EXISTS check_ins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    plan_id UUID NOT NULL REFERENCES intervention_plans(id) ON DELETE CASCADE,
    check_in_date DATE NOT NULL,
    tasks_completed_count INT NOT NULL DEFAULT 0,
    tasks_total_count INT NOT NULL DEFAULT 0,
    subjective_wellbeing VARCHAR(32) NOT NULL DEFAULT 'GOOD', -- GOOD | NEUTRAL | STRUGGLING
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 21. Wearable Connections
CREATE TABLE IF NOT EXISTS wearable_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    device_brand VARCHAR(64) NOT NULL,        -- Noise | Fire-Boltt | Apple | Fitbit | Garmin
    device_model VARCHAR(128) NOT NULL,
    connection_status VARCHAR(32) NOT NULL DEFAULT 'CONNECTED',
    last_synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 22. Wearable Observations (Clinical Measurement Time-Series)
CREATE TABLE IF NOT EXISTS wearable_observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    device_connection_id UUID NOT NULL REFERENCES wearable_connections(id) ON DELETE CASCADE,
    metric_type VARCHAR(64) NOT NULL,         -- RESTING_HEART_RATE | HRV_RMSSD | DAILY_STEPS | SLEEP_DURATION_MINUTES
    value NUMERIC(10,3) NOT NULL,
    unit VARCHAR(32) NOT NULL CHECK (length(trim(unit)) > 0),
    measurement_timestamp TIMESTAMPTZ NOT NULL,
    source VARCHAR(64) NOT NULL DEFAULT 'SMARTWATCH_WEARABLE_SDK',
    provenance JSONB NOT NULL,
    confidence_score NUMERIC(3,2) NOT NULL DEFAULT 1.00 CHECK (confidence_score >= 0.00 AND confidence_score <= 1.00),
    rolling_7d_baseline NUMERIC(10,3),
    baseline_deviation_sigma NUMERIC(6,3),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 23. Clinical Encounters
CREATE TABLE IF NOT EXISTS clinical_encounters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    clinician_id VARCHAR(128) NOT NULL,
    encounter_type VARCHAR(64) NOT NULL,      -- PREVENTIVE_HEALTH_CAMP | PHC_OPD_CONSULTATION | TELEMEDICINE_TRIAGE
    reason_for_visit TEXT NOT NULL,
    soap_subjective TEXT NOT NULL,
    soap_objective TEXT NOT NULL,
    soap_assessment TEXT NOT NULL,
    soap_plan TEXT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'COMPLETED',
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ
);

-- 24. Care Plans (Multi-disciplinary Coordination)
CREATE TABLE IF NOT EXISTS care_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    care_team_id UUID REFERENCES care_teams(id) ON DELETE SET NULL,
    lead_clinician_id VARCHAR(128),
    title VARCHAR(255) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 25. Referrals
CREATE TABLE IF NOT EXISTS referrals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    referring_worker_id VARCHAR(128) NOT NULL,
    referred_to_facility VARCHAR(255) NOT NULL,
    urgency VARCHAR(32) NOT NULL DEFAULT 'ROUTINE', -- ROUTINE | PRIORITY | URGENT | EMERGENT
    clinical_reason TEXT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',  -- PENDING | ACCEPTED | COMPLETED | DECLINED
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- 26. Alerts
CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    urgency VARCHAR(32) NOT NULL DEFAULT 'PRIORITY',
    alert_type VARCHAR(64) NOT NULL,          -- CRITICAL_HYPERTENSIVE_SPIKE | GLYCEMIC_DETERIORATION
    message TEXT NOT NULL,
    clinical_rule_triggered VARCHAR(255) NOT NULL,
    is_acknowledged BOOLEAN NOT NULL DEFAULT FALSE,
    acknowledged_by VARCHAR(128),
    acknowledged_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 27. Notifications
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipient_user_id VARCHAR(128) NOT NULL,
    patient_id UUID REFERENCES patients(id) ON DELETE SET NULL,
    channel VARCHAR(32) NOT NULL DEFAULT 'IN_APP', -- PUSH | SMS | WHATSAPP | IN_APP
    title VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 28. Consents (ABDM / DISHA Directive)
CREATE TABLE IF NOT EXISTS consents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    grantee_id VARCHAR(128) NOT NULL,
    grantee_role VARCHAR(64) NOT NULL,
    purpose VARCHAR(64) NOT NULL DEFAULT 'CARE_DELIVERY',
    scope_data_types JSONB NOT NULL DEFAULT '["VITALS","LABS","WEARABLES","RISK_ASSESSMENTS"]'::jsonb,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE', -- ACTIVE | REVOKED | EXPIRED
    valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_until TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 29. Documents
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    file_type VARCHAR(64) NOT NULL,
    storage_path TEXT NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    sha256_hash VARCHAR(64) NOT NULL,
    uploaded_by VARCHAR(128) NOT NULL,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 30. Document References
CREATE TABLE IF NOT EXISTS document_references (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    doc_type VARCHAR(64) NOT NULL,            -- DIAGNOSTIC_LAB_REPORT | PRESCRIPTION_SLIP
    clinical_summary TEXT,
    parsed_entities_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 31. Audit Events (Forensic Immutable Trail)
CREATE TABLE IF NOT EXISTS audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    actor_id VARCHAR(128) NOT NULL,
    actor_role VARCHAR(64) NOT NULL,
    action VARCHAR(64) NOT NULL,              -- USER_REGISTERED | LOGIN_SUCCESS | CONSENT_GRANTED
    resource_type VARCHAR(64) NOT NULL,
    resource_id VARCHAR(128) NOT NULL,
    patient_id UUID REFERENCES patients(id) ON DELETE SET NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ==============================================================================
-- REQUIRED INDEXES FOR PRODUCTION QUERY PERFORMANCE
-- 1. Patient Index (Longitudinal History by Citizen)
-- 2. Timestamp Index (Chronological Sorting & Temporal Windows)
-- 3. Clinical Type Index (Biomarker Specific Retrieval)
-- 4. Risk Domain Index (Epidemiological Stratification)
-- 5. Organization Index (Multi-Tenant Scoping)
-- 6. Geography/Program Index (District, Sub-district, Ward Allocations)
-- ==============================================================================

-- 1. Patient Indexes
CREATE INDEX IF NOT EXISTS idx_vital_signs_patient_time ON vital_signs(patient_id, measurement_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_lab_results_patient_time ON lab_results(patient_id, measurement_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_wearable_obs_patient_time ON wearable_observations(patient_id, measurement_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_screenings_patient ON screenings(patient_id, screened_at DESC);
CREATE INDEX IF NOT EXISTS idx_risk_assessments_patient ON risk_assessments(patient_id, assessed_at DESC);
CREATE INDEX IF NOT EXISTS idx_intervention_plans_patient ON intervention_plans(patient_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_clinical_encounters_patient ON clinical_encounters(patient_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_patient ON alerts(patient_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_consents_patient ON consents(patient_id, status);

-- 2. Timestamp Indexes
CREATE INDEX IF NOT EXISTS idx_vital_signs_timestamp ON vital_signs(measurement_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_lab_results_timestamp ON lab_results(measurement_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_wearable_obs_timestamp ON wearable_observations(measurement_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_events_timestamp ON audit_events(created_at DESC);

-- 3. Clinical Type Indexes
CREATE INDEX IF NOT EXISTS idx_vital_signs_clinical_type ON vital_signs(clinical_type, measurement_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_lab_results_test_name ON lab_results(test_name, measurement_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_lab_results_loinc ON lab_results(loinc_code);
CREATE INDEX IF NOT EXISTS idx_wearable_obs_metric_type ON wearable_observations(metric_type, measurement_timestamp DESC);

-- 4. Risk Domain Indexes
CREATE INDEX IF NOT EXISTS idx_risk_factors_domain_severity ON risk_factors(domain, severity);
CREATE INDEX IF NOT EXISTS idx_risk_assessments_overall_tier ON risk_assessments(overall_tier, assessed_at DESC);
CREATE INDEX IF NOT EXISTS idx_intervention_plans_domain ON intervention_plans(primary_domain);

-- 5. Organization Indexes
CREATE INDEX IF NOT EXISTS idx_patients_organization ON patients(organization_id);
CREATE INDEX IF NOT EXISTS idx_care_teams_organization ON care_teams(organization_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_organization ON audit_events(organization_id, created_at DESC);

-- 6. Geography & Program Indexes
CREATE INDEX IF NOT EXISTS idx_profiles_geography ON profiles(state, district, sub_district, village_or_ward);
CREATE INDEX IF NOT EXISTS idx_organizations_jurisdiction ON organizations(jurisdiction);
CREATE INDEX IF NOT EXISTS idx_care_teams_jurisdiction ON care_teams(jurisdiction);
