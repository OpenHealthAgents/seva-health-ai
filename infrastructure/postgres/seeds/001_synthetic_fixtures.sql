-- ==============================================================================
-- SevaHealth AI: Synthetic Demo Fixtures Seed Script
-- WARNING: All persona records, biometrics, and clinical parameters are strictly
-- synthetic and generated for demonstration, testing, and evaluation purposes.
-- ==============================================================================

-- 1. Organizations
INSERT INTO organizations (id, name, type, jurisdiction) VALUES
('11111111-1111-1111-1111-111111111111', 'Karnataka State Health Mission', 'STATE_HEALTH_MISSION', 'Karnataka'),
('22222222-2222-2222-2222-222222222222', 'Mysuru District Health Office', 'DISTRICT_HEALTH_OFFICE', 'Mysuru District'),
('33333333-3333-3333-3333-333333333333', 'Nanjangud Primary Health Centre', 'PHC', 'Nanjangud Taluk')
ON CONFLICT (id) DO NOTHING;

-- 2. Care Teams
INSERT INTO care_teams (id, organization_id, name, jurisdiction) VALUES
('44444444-4444-4444-4444-444444444444', '33333333-3333-3333-3333-333333333333', 'Ward 12 Community NCD Care Team', 'Ward 12')
ON CONFLICT (id) DO NOTHING;

INSERT INTO care_team_members (id, care_team_id, user_id, role, name, phone) VALUES
('55555555-5555-5555-5555-555555555551', '44444444-4444-4444-4444-444444444444', 'worker-user-01', 'HEALTH_WORKER', 'Sunita Devi (ASHA Worker)', '+91 98450 11111'),
('55555555-5555-5555-5555-555555555552', '44444444-4444-4444-4444-444444444444', 'doctor-user-01', 'CLINICIAN', 'Dr. Anand Kulkarni, MD', '+91 98450 22222')
ON CONFLICT (id) DO NOTHING;

-- 3. Patient: Ramesh Patel
INSERT INTO patients (id, organization_id, abha_id, user_id, primary_care_team_id) VALUES
('a1111111-1111-1111-1111-111111111111', '33333333-3333-3333-3333-333333333333', '91-4829-1029-4820', 'citizen-user-01', '44444444-4444-4444-4444-444444444444')
ON CONFLICT (id) DO NOTHING;

-- 4. Profile: Ramesh Patel
INSERT INTO profiles (id, patient_id, first_name, last_name, birth_date, gender, phone, email, state, district, sub_district, village_or_ward, primary_language, socioeconomic_tier) VALUES
('b1111111-1111-1111-1111-111111111111', 'a1111111-1111-1111-1111-111111111111', 'Ramesh', 'Patel', '1978-04-12', 'MALE', '+91 98450 12345', 'ramesh@sevahealth.ai', 'Karnataka', 'Bengaluru Rural', 'Devanahalli', 'Ward 12', 'kn', 'BPL')
ON CONFLICT (id) DO NOTHING;

-- 5. Family History
INSERT INTO family_histories (id, patient_id, relative_relationship, condition_code, condition_name, age_at_onset, is_deceased) VALUES
('c1111111-1111-1111-1111-111111111111', 'a1111111-1111-1111-1111-111111111111', 'FATHER', 'DIABETES_MELLITUS_TYPE_2', 'Type 2 Diabetes Mellitus', 52, TRUE),
('c1111111-1111-1111-1111-111111111112', 'a1111111-1111-1111-1111-111111111111', 'MOTHER', 'HYPERTENSION', 'Essential Hypertension', 58, FALSE)
ON CONFLICT (id) DO NOTHING;

-- 6. Lifestyle Profile
INSERT INTO lifestyle_profiles (id, patient_id, tobacco_use, alcohol_use, dietary_pattern, physical_activity_level, sleep_hours_per_night, perceived_stress_level) VALUES
('d1111111-1111-1111-1111-111111111111', 'a1111111-1111-1111-1111-111111111111', 'NEVER', 'NONE', 'HIGH_CARB_HIGH_SALT', 'SEDENTARY', 6.00, 'MODERATE')
ON CONFLICT (id) DO NOTHING;

-- 7. Risk Factors
INSERT INTO risk_factors (id, patient_id, domain, name, severity) VALUES
('e1111111-1111-1111-1111-111111111111', 'a1111111-1111-1111-1111-111111111111', 'DIABETES', 'IMPAIRED_FASTING_GLYCEMIA', 'HIGH'),
('e1111111-1111-1111-1111-111111111112', 'a1111111-1111-1111-1111-111111111111', 'HYPERTENSION', 'PREHYPERTENSION_VASCULAR_STRAIN', 'MODERATE'),
('e1111111-1111-1111-1111-111111111113', 'a1111111-1111-1111-1111-111111111111', 'METABOLIC', 'CENTRAL_VISCERAL_ADIPOSITY', 'HIGH')
ON CONFLICT (id) DO NOTHING;

-- 8. Longitudinal Vital Signs (Chronological history: screening visit 1 vs follow-up visit 2)
INSERT INTO vital_signs (id, patient_id, clinical_type, value, unit, measurement_timestamp, source, provenance, confidence_score) VALUES
('f1111111-1111-1111-1111-111111111101', 'a1111111-1111-1111-1111-111111111111', 'SYSTOLIC_BP', 142.000, 'mmHg', '2026-09-01 09:30:00Z', 'COMMUNITY_HEALTH_CAMP', '{"recorder_id": "worker-user-01", "recorder_role": "HEALTH_WORKER", "device_model": "Omron HEM-7120"}'::jsonb, 0.95),
('f1111111-1111-1111-1111-111111111102', 'a1111111-1111-1111-1111-111111111111', 'DIASTOLIC_BP', 90.000, 'mmHg', '2026-09-01 09:30:00Z', 'COMMUNITY_HEALTH_CAMP', '{"recorder_id": "worker-user-01", "recorder_role": "HEALTH_WORKER", "device_model": "Omron HEM-7120"}'::jsonb, 0.95),
('f1111111-1111-1111-1111-111111111103', 'a1111111-1111-1111-1111-111111111111', 'BMI', 27.400, 'kg/m2', '2026-09-01 09:30:00Z', 'COMMUNITY_HEALTH_CAMP', '{"recorder_id": "worker-user-01", "recorder_role": "HEALTH_WORKER"}'::jsonb, 1.00),
('f1111111-1111-1111-1111-111111111104', 'a1111111-1111-1111-1111-111111111111', 'WAIST_CIRCUMFERENCE', 97.000, 'cm', '2026-09-01 09:30:00Z', 'COMMUNITY_HEALTH_CAMP', '{"recorder_id": "worker-user-01", "recorder_role": "HEALTH_WORKER"}'::jsonb, 1.00),
-- Follow-up after 3 weeks of intervention
('f1111111-1111-1111-1111-111111111105', 'a1111111-1111-1111-1111-111111111111', 'SYSTOLIC_BP', 138.000, 'mmHg', '2026-09-22 10:15:00Z', 'PHC_OPD_CONSULTATION', '{"recorder_id": "doctor-user-01", "recorder_role": "CLINICIAN", "device_model": "Welch Allyn 767"}'::jsonb, 0.98),
('f1111111-1111-1111-1111-111111111106', 'a1111111-1111-1111-1111-111111111111', 'DIASTOLIC_BP', 88.000, 'mmHg', '2026-09-22 10:15:00Z', 'PHC_OPD_CONSULTATION', '{"recorder_id": "doctor-user-01", "recorder_role": "CLINICIAN", "device_model": "Welch Allyn 767"}'::jsonb, 0.98)
ON CONFLICT (id) DO NOTHING;

-- 9. Lab Results
INSERT INTO lab_results (id, patient_id, test_name, loinc_code, value, unit, reference_range, interpretation, measurement_timestamp, source, provenance, confidence_score) VALUES
('01111111-1111-1111-1111-111111111101', 'a1111111-1111-1111-1111-111111111111', 'FASTING_BLOOD_GLUCOSE', '1558-6', 118.000, 'mg/dL', '70 - 99 mg/dL', 'ELEVATED', '2026-09-22 08:00:00Z', 'PHC_DIAGNOSTIC_LAB', '{"recorder_id": "phc-lab-tech", "recorder_role": "HEALTH_WORKER"}'::jsonb, 0.99),
('01111111-1111-1111-1111-111111111102', 'a1111111-1111-1111-1111-111111111111', 'HBA1C', '4548-4', 6.200, '%', '< 5.7 %', 'ELEVATED', '2026-09-22 08:00:00Z', 'PHC_DIAGNOSTIC_LAB', '{"recorder_id": "phc-lab-tech", "recorder_role": "HEALTH_WORKER"}'::jsonb, 0.99),
('01111111-1111-1111-1111-111111111103', 'a1111111-1111-1111-1111-111111111111', 'TRIGLYCERIDES', '2571-8', 185.000, 'mg/dL', '< 150 mg/dL', 'ELEVATED', '2026-09-22 08:00:00Z', 'PHC_DIAGNOSTIC_LAB', '{"recorder_id": "phc-lab-tech", "recorder_role": "HEALTH_WORKER"}'::jsonb, 0.99)
ON CONFLICT (id) DO NOTHING;

-- 10. Medications
INSERT INTO medications (id, patient_id, drug_name, dosage, frequency, indication, prescribed_by, start_date) VALUES
('02111111-1111-1111-1111-111111111101', 'a1111111-1111-1111-1111-111111111111', 'Metformin Hydrochloride', '500 mg', 'Once Daily with Dinner', 'Impaired Glycemia / Prediabetes Reversal', 'Dr. Anand Kulkarni', '2026-09-23')
ON CONFLICT (id) DO NOTHING;

-- 11. Medication Adherence
INSERT INTO medication_adherences (id, patient_id, medication_id, scheduled_date, taken, reported_at) VALUES
('03111111-1111-1111-1111-111111111101', 'a1111111-1111-1111-1111-111111111111', '02111111-1111-1111-1111-111111111101', '2026-09-23', TRUE, '2026-09-23 21:00:00Z'),
('03111111-1111-1111-1111-111111111102', 'a1111111-1111-1111-1111-111111111111', '02111111-1111-1111-1111-111111111101', '2026-09-24', TRUE, '2026-09-24 21:10:00Z')
ON CONFLICT (id) DO NOTHING;

-- 12. Screenings
INSERT INTO screenings (id, patient_id, screening_type, administered_by, administrator_role, location, screened_at) VALUES
('04111111-1111-1111-1111-111111111101', 'a1111111-1111-1111-1111-111111111111', 'NCD_COMPREHENSIVE_CBAC', 'Sunita Devi', 'HEALTH_WORKER', 'Ward 12 Community Health Hall', '2026-09-01 09:30:00Z')
ON CONFLICT (id) DO NOTHING;

-- 13. Screening Results
INSERT INTO screening_results (id, screening_id, patient_id, cbac_score, idrs_score, needs_immediate_referral, summary_findings) VALUES
('05111111-1111-1111-1111-111111111101', '04111111-1111-1111-1111-111111111101', 'a1111111-1111-1111-1111-111111111111', 7, 60, TRUE, 'High IDRS (60/100) and CBAC score (7) indicate substantial risk of progression to Type 2 Diabetes and Hypertension.')
ON CONFLICT (id) DO NOTHING;

-- 14. Risk Assessments
INSERT INTO risk_assessments (id, patient_id, screening_id, overall_score, overall_tier, domain_scores, clinical_safety_disclaimer, assessed_at) VALUES
('06111111-1111-1111-1111-111111111101', 'a1111111-1111-1111-1111-111111111111', '04111111-1111-1111-1111-111111111101', 0.6800, 'HIGH', '{"diabetes": 0.74, "hypertension": 0.62, "cardiovascular": 0.45, "metabolic": 0.70}'::jsonb, 'CLINICAL REVIEW RECOMMENDED: AI-assisted preventive risk stratification. Does not constitute a clinical diagnosis.', '2026-09-01 10:00:00Z')
ON CONFLICT (id) DO NOTHING;

-- 15. Risk Factor Contributions
INSERT INTO risk_factor_contributions (id, risk_assessment_id, patient_id, factor_name, factor_category, observed_value, target_value, relative_weight, is_protective, evidence_guideline) VALUES
('07111111-1111-1111-1111-111111111101', '06111111-1111-1111-1111-111111111101', 'a1111111-1111-1111-1111-111111111111', 'Prediabetic Impaired Glycemia', 'BIOMETRIC', 'HbA1c 6.2%, FBG 118 mg/dL', 'HbA1c < 5.7%', 0.2600, FALSE, 'ICMR-INDIAB Guidelines 2023'),
('07111111-1111-1111-1111-111111111102', '06111111-1111-1111-1111-111111111101', 'a1111111-1111-1111-1111-111111111111', 'Prehypertension Vascular Strain', 'BIOMETRIC', '138/88 mmHg', '< 120/80 mmHg', 0.1900, FALSE, 'ACC/AHA 2017 Guidelines'),
('07111111-1111-1111-1111-111111111103', '06111111-1111-1111-1111-111111111101', 'a1111111-1111-1111-1111-111111111111', 'Tobacco Abstinence', 'LIFESTYLE', 'Non-smoker', 'Non-smoker', -0.1200, TRUE, 'WHO Preventive Guidelines')
ON CONFLICT (id) DO NOTHING;

-- 16. Risk Trajectories
INSERT INTO risk_trajectories (id, patient_id, assessment_ids, historical_scores, trend, rate_of_change, projected_tier_6m) VALUES
('08111111-1111-1111-1111-111111111101', 'a1111111-1111-1111-1111-111111111111', '["06111111-1111-1111-1111-111111111101"]'::jsonb, '[{"date": "2026-09-01", "score": 0.68}]'::jsonb, 'DETERIORATING', 0.0450, 'CRITICAL')
ON CONFLICT (id) DO NOTHING;

-- 17. Intervention Plans
INSERT INTO intervention_plans (id, patient_id, risk_assessment_id, title, primary_domain, duration_days, start_date, end_date, adherence_rate) VALUES
('09111111-1111-1111-1111-111111111101', 'a1111111-1111-1111-1111-111111111111', '06111111-1111-1111-1111-111111111101', 'SevaHealth 30-Day Glycemic Stabilization Journey', 'Prediabetes & Vascular Protection', 30, '2026-09-01', '2026-10-01', 23.30)
ON CONFLICT (id) DO NOTHING;

-- 18. Interventions
INSERT INTO interventions (id, plan_id, pillar, title, prescription_text, frequency, target_metric) VALUES
('0a111111-1111-1111-1111-111111111101', '09111111-1111-1111-1111-111111111101', 'NUTRITION', 'Swap White Rice with Foxtail Millet', 'Replace refined carbohydrates with low-glycemic whole millets.', 'Daily with lunch', '1 serving'),
('0a111111-1111-1111-1111-111111111102', '09111111-1111-1111-1111-111111111101', 'PHYSICAL_ACTIVITY', 'Post-Dinner 20-Min Brisk Walk', 'Blunts evening postprandial glucose spike by up to 28%.', 'Daily after dinner', '2,500 steps')
ON CONFLICT (id) DO NOTHING;

-- 19. Goals
INSERT INTO goals (id, patient_id, plan_id, metric_name, baseline_value, target_value, target_date, status) VALUES
('0b111111-1111-1111-1111-111111111101', 'a1111111-1111-1111-1111-111111111111', '09111111-1111-1111-1111-111111111101', 'FASTING_GLUCOSE', 118.000, 99.000, '2026-10-01', 'IN_PROGRESS'),
('0b111111-1111-1111-1111-111111111102', 'a1111111-1111-1111-1111-111111111111', '09111111-1111-1111-1111-111111111101', 'SYSTOLIC_BP', 138.000, 120.000, '2026-10-01', 'IN_PROGRESS')
ON CONFLICT (id) DO NOTHING;

-- 20. Check-Ins
INSERT INTO check_ins (id, patient_id, plan_id, check_in_date, tasks_completed_count, tasks_total_count, subjective_wellbeing) VALUES
('0c111111-1111-1111-1111-111111111101', 'a1111111-1111-1111-1111-111111111111', '09111111-1111-1111-1111-111111111101', '2026-09-07', 7, 7, 'GOOD')
ON CONFLICT (id) DO NOTHING;

-- 21. Wearable Connections
INSERT INTO wearable_connections (id, patient_id, device_brand, device_model, connection_status, last_synced_at) VALUES
('0d111111-1111-1111-1111-111111111101', 'a1111111-1111-1111-1111-111111111111', 'Noise', 'ColorFit Pro 4', 'CONNECTED', '2026-10-07 18:00:00Z')
ON CONFLICT (id) DO NOTHING;

-- 22. Longitudinal Wearable Observations
INSERT INTO wearable_observations (id, patient_id, device_connection_id, metric_type, value, unit, measurement_timestamp, source, provenance, confidence_score, rolling_7d_baseline) VALUES
('0e111111-1111-1111-1111-111111111101', 'a1111111-1111-1111-1111-111111111111', '0d111111-1111-1111-1111-111111111101', 'RESTING_HEART_RATE', 72.000, 'bpm', '2026-10-07 06:00:00Z', 'SMARTWATCH_WEARABLE_SDK', '{"device_brand": "Noise", "sensor": "PPG"}'::jsonb, 0.94, 73.500),
('0e111111-1111-1111-1111-111111111102', 'a1111111-1111-1111-1111-111111111111', '0d111111-1111-1111-1111-111111111101', 'HRV_RMSSD', 48.200, 'ms', '2026-10-07 06:00:00Z', 'SMARTWATCH_WEARABLE_SDK', '{"device_brand": "Noise", "sensor": "PPG"}'::jsonb, 0.92, 45.000),
('0e111111-1111-1111-1111-111111111103', 'a1111111-1111-1111-1111-111111111111', '0d111111-1111-1111-1111-111111111101', 'DAILY_STEPS', 7450.000, 'steps', '2026-10-07 23:59:59Z', 'SMARTWATCH_WEARABLE_SDK', '{"device_brand": "Noise", "sensor": "3-Axis Accelerometer"}'::jsonb, 0.99, 6800.000)
ON CONFLICT (id) DO NOTHING;

-- 23. Clinical Encounters
INSERT INTO clinical_encounters (id, patient_id, clinician_id, encounter_type, reason_for_visit, soap_subjective, soap_objective, soap_assessment, soap_plan, status) VALUES
('0f111111-1111-1111-1111-111111111101', 'a1111111-1111-1111-1111-111111111111', 'doctor-user-01', 'PHC_OPD_CONSULTATION', 'Evaluation of prediabetes and borderline vascular strain', 'Reports lethargy after meals. Denies chest pain or shortness of breath.', 'BP 138/88 mmHg, FBG 118 mg/dL, HbA1c 6.2%, Waist 96 cm.', 'Impaired Fasting Glycemia (Prediabetes) and Prehypertension.', 'Prescribed Metformin 500mg daily, low-glycemic dietary modification, and 30-day care plan adherence tracking.', 'COMPLETED')
ON CONFLICT (id) DO NOTHING;

-- 24. Care Plans
INSERT INTO care_plans (id, patient_id, care_team_id, lead_clinician_id, title, status) VALUES
('a2111111-1111-1111-1111-111111111101', 'a1111111-1111-1111-1111-111111111111', '44444444-4444-4444-4444-444444444444', 'doctor-user-01', 'Integrated Primary Prevention & Glycemic Care Plan', 'ACTIVE')
ON CONFLICT (id) DO NOTHING;

-- 25. Referrals
INSERT INTO referrals (id, patient_id, referring_worker_id, referred_to_facility, urgency, clinical_reason, status) VALUES
('a3111111-1111-1111-1111-111111111101', 'a1111111-1111-1111-1111-111111111111', 'worker-user-01', 'Nanjangud PHC Medical Officer', 'PRIORITY', 'High CBAC score (7) and elevated blood pressure at field camp.', 'COMPLETED')
ON CONFLICT (id) DO NOTHING;

-- 26. Alerts
INSERT INTO alerts (id, patient_id, urgency, alert_type, message, clinical_rule_triggered, is_acknowledged) VALUES
('a4111111-1111-1111-1111-111111111101', 'a1111111-1111-1111-1111-111111111111', 'PRIORITY', 'GLYCEMIC_DETERIORATION', 'Elevated HbA1c (6.2%) and FBG (118 mg/dL) require physician follow-up.', 'Rule-NCD-GLY-02: FBG > 110 mg/dL with family history', TRUE)
ON CONFLICT (id) DO NOTHING;

-- 27. Notifications
INSERT INTO notifications (id, recipient_user_id, patient_id, channel, title, body) VALUES
('a5111111-1111-1111-1111-111111111101', 'citizen-user-01', 'a1111111-1111-1111-1111-111111111111', 'IN_APP', 'Day 8 Care Plan Reminder', 'Time for your 20-minute post-dinner brisk walk! Keep up the great streak.')
ON CONFLICT (id) DO NOTHING;

-- 28. Consents
INSERT INTO consents (id, patient_id, grantee_id, grantee_role, purpose, valid_from, valid_until) VALUES
('a6111111-1111-1111-1111-111111111101', 'a1111111-1111-1111-1111-111111111111', 'doctor-user-01', 'CLINICIAN', 'CARE_DELIVERY', NOW(), NOW() + INTERVAL '90 days')
ON CONFLICT (id) DO NOTHING;

-- 29. Documents
INSERT INTO documents (id, patient_id, file_name, file_type, storage_path, file_size_bytes, sha256_hash, uploaded_by) VALUES
('a7111111-1111-1111-1111-111111111101', 'a1111111-1111-1111-1111-111111111111', 'nanjangud_phc_lab_report_sep2026.pdf', 'application/pdf', 'documents/a1111111/nanjangud_phc_lab_report_sep2026.pdf', 245100, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'doctor-user-01')
ON CONFLICT (id) DO NOTHING;

-- 30. Document References
INSERT INTO document_references (id, document_id, patient_id, doc_type, clinical_summary, parsed_entities_json) VALUES
('a8111111-1111-1111-1111-111111111101', 'a7111111-1111-1111-1111-111111111101', 'a1111111-1111-1111-1111-111111111111', 'DIAGNOSTIC_LAB_REPORT', 'Nanjangud PHC Diagnostic Report showing FBG 118 mg/dL and HbA1c 6.2%', '{"hba1c": 6.2, "fasting_glucose": 118, "triglycerides": 185}'::jsonb)
ON CONFLICT (id) DO NOTHING;

-- 31. Audit Events
INSERT INTO audit_events (id, organization_id, actor_id, actor_role, action, resource_type, resource_id, patient_id, details) VALUES
('a9111111-1111-1111-1111-111111111101', '33333333-3333-3333-3333-333333333333', 'worker-user-01', 'HEALTH_WORKER', 'SCREENING_SUBMITTED', 'Screening', '04111111-1111-1111-1111-111111111101', 'a1111111-1111-1111-1111-111111111111', '{"screening_type": "NCD_COMPREHENSIVE_CBAC"}'::jsonb),
('a9111111-1111-1111-1111-111111111102', '33333333-3333-3333-3333-333333333333', 'doctor-user-01', 'CLINICIAN', 'CLINICIAN_REVIEWED', 'ClinicalEncounter', '0f111111-1111-1111-1111-111111111101', 'a1111111-1111-1111-1111-111111111111', '{"status": "COMPLETED"}'::jsonb)
ON CONFLICT (id) DO NOTHING;
