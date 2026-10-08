"""Comprehensive Test Suite for SevaHealth Clinical Interoperability and Multi-EMR Adapters.

Tests:
1. Data normalization across all 4 adapters (Local, openEHR, bezs-emr-gql, bezs-hms)
2. Zero provider data model leakage
3. Anti-arbitrary query guard (blocks SQL / GraphQL query strings)
4. RBAC authorization (citizens can only access own data; clinicians can access; public health admins restricted)
5. Immutable clinical access audit logging
6. Federated deduplication and chart aggregation
7. AI agent controlled tools
8. REST API endpoints
"""

import pytest
import uuid
from datetime import datetime, timezone
from starlette.testclient import TestClient

from packages.types.enums import UserRole, Gender
from packages.auth.jwt import create_access_token, TokenPayload
from packages.interop.models import (
    ClinicalSourceSystem,
    ObservationCategory,
    ConditionClinicalStatus,
    ConditionVerificationStatus,
    MedicationStatus,
    EncounterClass,
    ClinicalDocumentType,
    NormalizedPatient,
    NormalizedObservation,
    NormalizedCondition,
    NormalizedMedication,
    NormalizedEncounter,
    NormalizedCarePlan,
    NormalizedClinicalDocument,
    FederatedClinicalChart,
)
from packages.interop.base import AccessContext
from packages.interop.security import (
    ClinicalRBACGuard,
    AntiArbitraryQueryGuard,
    AccessDeniedError,
    ArbitraryQueryViolationError,
)
from packages.interop.audit import ClinicalAccessAuditLogger
from packages.interop.adapters.local_adapter import SevaHealthLocalAdapter
from packages.interop.adapters.openehr_adapter import OpenEhrEhrBaseAdapter
from packages.interop.adapters.emr_gql_adapter import EmrGqlAdapter
from packages.interop.adapters.hms_adapter import HmsAdapter
from packages.interop.service import FederatedClinicalDataProvider, federated_clinical_data_provider
from packages.interop.service import federated_clinical_data_provider
from services.ai_agent.interop_tools import (
    tool_get_federated_patient,
    tool_get_federated_vitals_and_labs,
    tool_get_federated_conditions,
    tool_get_federated_medications,
    tool_get_federated_encounters,
    tool_get_federated_clinical_chart,
)
from services.ai_agent.prevention_agent import prevention_agent
from services.store import store, CitizenRecord
from packages.clinical_models.observations import Observation
from services.api.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup clean test state in store."""
    # Seed a test citizen
    citizen = CitizenRecord(
        id="cit_interop_001",
        tenant_id="karnataka_state_health",
        user_id="usr_citizen_001",
        abha_id="91-1234-5678-9012",
        first_name="Ramesh",
        last_name="Gowda",
        birth_date="1978-05-12",
        gender=Gender.MALE,
        phone="+919876543210",
        state="Karnataka",
        district="Mysuru",
        sub_district="Nanjangud",
        village_or_ward="Ward 4",
    )
    store.add_citizen(citizen)

    # Seed observations in local store
    obs = Observation(
        citizen_id="cit_interop_001",
        tenant_id="karnataka_state_health",
        code="SYSTOLIC_BP",
        loinc_code="8480-6",
        display_name="Systolic Blood Pressure",
        value=142.0,
        unit="mmHg",
    )
    store.add_observation(obs)

    # Seed local medication
    store.medications["cit_interop_001"] = [
        {
            "id": "med_001",
            "medication_name": "Metformin 500mg",
            "dosage_instruction": "500 mg orally twice daily with meals",
            "status": "ACTIVE",
            "route": "ORAL",
        }
    ]

    # Seed local encounter
    store.encounters["cit_interop_001"] = [
        {
            "id": "enc_001",
            "class": "FIELD",
            "status": "COMPLETED",
            "reason": "Annual NCD Screening",
            "provider_name": "Dr. Ananya Rao",
            "facility_name": "Nanjangud PHC",
        }
    ]


@pytest.fixture
def clinician_context():
    return AccessContext(
        actor_id="clinician_001",
        actor_role=UserRole.CLINICIAN,
        tenant_id="karnataka_state_health",
        purpose_of_use="CARE_DELIVERY",
    )


@pytest.fixture
def citizen_context():
    return AccessContext(
        actor_id="cit_interop_001",
        actor_role=UserRole.CITIZEN,
        tenant_id="karnataka_state_health",
        purpose_of_use="PATIENT_PORTAL",
    )


@pytest.fixture
def other_citizen_context():
    return AccessContext(
        actor_id="other_cit_999",
        actor_role=UserRole.CITIZEN,
        tenant_id="karnataka_state_health",
        purpose_of_use="PATIENT_PORTAL",
    )


@pytest.fixture
def public_health_admin_context():
    return AccessContext(
        actor_id="pha_001",
        actor_role=UserRole.PUBLIC_HEALTH_ADMIN,
        tenant_id="karnataka_state_health",
        purpose_of_use="PUBLIC_HEALTH_ANALYSIS",
    )


# ==============================================================================
# 1. LOCAL ADAPTER TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_local_adapter_normalizes_records(clinician_context):
    adapter = SevaHealthLocalAdapter()
    assert adapter.source_system == ClinicalSourceSystem.SEVAHEALTH_LOCAL

    patient = await adapter.get_patient("cit_interop_001", clinician_context)
    assert patient is not None
    assert isinstance(patient, NormalizedPatient)
    assert patient.name == "Ramesh Gowda"
    assert patient.source_system == ClinicalSourceSystem.SEVAHEALTH_LOCAL
    assert patient.national_id == "91-1234-5678-9012"

    observations = await adapter.get_observations("cit_interop_001", clinician_context)
    assert len(observations) >= 1
    assert isinstance(observations[0], NormalizedObservation)
    assert observations[0].value == 142.0
    assert observations[0].unit == "mmHg"
    assert observations[0].category == ObservationCategory.VITAL_SIGN

    medications = await adapter.get_medications("cit_interop_001", clinician_context)
    assert len(medications) == 1
    assert isinstance(medications[0], NormalizedMedication)
    assert medications[0].medication_name == "Metformin 500mg"
    assert medications[0].status == MedicationStatus.ACTIVE

    encounters = await adapter.get_encounters("cit_interop_001", clinician_context)
    assert len(encounters) == 1
    assert isinstance(encounters[0], NormalizedEncounter)
    assert encounters[0].provider_name == "Dr. Ananya Rao"


# ==============================================================================
# 2. OPENEHR ADAPTER TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_openehr_adapter_normalizes_compositions(clinician_context):
    adapter = OpenEhrEhrBaseAdapter()
    assert adapter.source_system == ClinicalSourceSystem.OPENEHR_EHRBASE

    # Seed an openEHR vital sign composition
    comp = {
        "name": {"value": "Vital signs encounter"},
        "archetype_details": {"archetype_id": {"value": "openEHR-EHR-COMPOSITION.encounter.v1"}},
        "uid": {"value": "openehr_comp_123"},
        "content": [
            {
                "name": {"value": "Systolic Blood Pressure"},
                "archetype_node_id": "at0004",
                "data": {"magnitude": 138.0, "units": "mmHg"},
            },
            {
                "name": {"value": "Pulse Rate"},
                "archetype_node_id": "at0005",
                "data": {"magnitude": 76.0, "units": "/min"},
            }
        ]
    }
    adapter.store_local_composition("cit_interop_001", comp)

    observations = await adapter.get_observations("cit_interop_001", clinician_context)
    assert len(observations) == 2
    assert all(isinstance(o, NormalizedObservation) for o in observations)
    assert all(o.source_system == ClinicalSourceSystem.OPENEHR_EHRBASE for o in observations)
    assert observations[0].value == 138.0
    assert observations[1].value == 76.0


# ==============================================================================
# 3. BEZS-EMR-GQL ADAPTER TESTS (FHIR R4)
# ==============================================================================

@pytest.mark.asyncio
async def test_emr_gql_adapter_normalizes_fhir(clinician_context):
    adapter = EmrGqlAdapter()
    assert adapter.source_system == ClinicalSourceSystem.BEZS_EMR_GQL

    # Seed FHIR Patient
    adapter.seed_fhir_resource(
        "cit_interop_001",
        "Patient",
        {
            "id": "fhir_pat_001",
            "name": [{"family": "Gowda", "given": ["Ramesh"]}],
            "gender": "male",
            "birthDate": "1978-05-12",
            "identifier": [{"system": "abha", "value": "91-1234-5678-9012"}],
        }
    )

    # Seed FHIR Observation (HbA1c)
    adapter.seed_fhir_resource(
        "cit_interop_001",
        "Observation",
        {
            "id": "fhir_obs_001",
            "category": [{"coding": [{"code": "laboratory"}]}],
            "code": {"coding": [{"code": "4548-4", "display": "HbA1c"}]},
            "valueQuantity": {"value": 7.4, "unit": "%"},
            "status": "final",
        }
    )

    # Seed FHIR Condition (Type 2 Diabetes)
    adapter.seed_fhir_resource(
        "cit_interop_001",
        "Condition",
        {
            "id": "fhir_cond_001",
            "code": {"coding": [{"code": "E11.9", "display": "Type 2 Diabetes Mellitus"}]},
            "clinicalStatus": {"coding": [{"code": "active"}]},
            "verificationStatus": {"coding": [{"code": "confirmed"}]},
        }
    )

    # Seed FHIR MedicationRequest
    adapter.seed_fhir_resource(
        "cit_interop_001",
        "MedicationRequest",
        {
            "id": "fhir_med_001",
            "medicationCodeableConcept": {"coding": [{"code": "860975", "display": "Metformin 500mg"}]},
            "dosageInstruction": [{"text": "500 mg orally twice daily"}],
            "status": "active",
        }
    )

    pat = await adapter.get_patient("cit_interop_001", clinician_context)
    assert pat is not None
    assert pat.name == "Ramesh Gowda"
    assert pat.source_system == ClinicalSourceSystem.BEZS_EMR_GQL

    obs = await adapter.get_observations("cit_interop_001", clinician_context)
    assert len(obs) == 1
    assert obs[0].code == "LOINC::4548-4"
    assert obs[0].value == 7.4
    assert obs[0].unit == "%"
    assert obs[0].category == ObservationCategory.LABORATORY

    conds = await adapter.get_conditions("cit_interop_001", clinician_context)
    assert len(conds) == 1
    assert conds[0].code == "ICD-10::E11.9"
    assert conds[0].clinical_status == ConditionClinicalStatus.ACTIVE

    meds = await adapter.get_medications("cit_interop_001", clinician_context)
    assert len(meds) == 1
    assert meds[0].medication_name == "Metformin 500mg"


# ==============================================================================
# 4. BEZS-HMS ADAPTER TESTS (INTAKES & CONSULTATIONS)
# ==============================================================================

@pytest.mark.asyncio
async def test_hms_adapter_normalizes_intake_and_consultations(clinician_context):
    adapter = HmsAdapter()
    assert adapter.source_system == ClinicalSourceSystem.BEZS_HMS

    # Seed an HMS Intake
    adapter.seed_intake(
        "cit_interop_001",
        {
            "id": 101,
            "mode": "TEXT",
            "status": "COMPLETED",
            "conversation": [{"role": "user", "content": "I feel thirsty and tired recently."}],
            "report": {
                "risk_level": "HIGH",
                "differential_diagnosis": [
                    {"code": "PRE_DIABETES", "condition": "Prediabetes / Impaired Fasting Glucose"}
                ]
            }
        }
    )

    # Seed an HMS Consultation with SOAP note
    adapter.seed_consultation(
        "cit_interop_001",
        {
            "id": 202,
            "room_id": "room_HMS99X",
            "status": "COMPLETED",
            "published_at": "2026-10-08T10:00:00Z",
            "published_by": "Dr. Vivek Sharma",
            "soap_note": {
                "subjective": "Patient reports persistent polydipsia and fatigue.",
                "objective": "BP 142/88 mmHg, random glucose 165 mg/dL.",
                "assessment": "Suspected early type 2 diabetes with stage 1 hypertension.",
                "plan": "Order HbA1c test and initiate lifestyle diet modifications.",
            },
            "observations": [
                {"code": "RANDOM_GLUCOSE", "display": "Random Blood Glucose", "value": 165.0, "unit": "mg/dL"}
            ],
            "medication_requests": [
                {"medication_name": "Amlodipine 5mg", "dosage_instruction": "5 mg once daily in morning"}
            ],
        }
    )

    # Test Documents: Intake assessment and SOAP reports
    docs = await adapter.get_clinical_documents("cit_interop_001", clinician_context)
    assert len(docs) == 2
    doc_types = [d.document_type for d in docs]
    assert ClinicalDocumentType.INTAKE_ASSESSMENT in doc_types
    assert ClinicalDocumentType.SOAP_REPORT in doc_types

    # Test Encounters: SOAP note parsed into normalized encounter
    encounters = await adapter.get_encounters("cit_interop_001", clinician_context)
    assert len(encounters) == 1
    assert encounters[0].encounter_class == EncounterClass.VIRTUAL
    assert encounters[0].soap_note is not None
    assert "polydipsia" in encounters[0].soap_note["subjective"]
    assert encounters[0].provider_name == "Dr. Vivek Sharma"

    # Test Observations from HMS consultation
    obs = await adapter.get_observations("cit_interop_001", clinician_context)
    assert len(obs) == 1
    assert obs[0].value == 165.0

    # Test Medications from HMS consultation
    meds = await adapter.get_medications("cit_interop_001", clinician_context)
    assert len(meds) == 1
    assert meds[0].medication_name == "Amlodipine 5mg"


# ==============================================================================
# 5. SECURITY GUARD TESTS: ANTI-ARBITRARY QUERY INJECTION
# ==============================================================================

def test_anti_arbitrary_query_blocks_sql():
    # Detects SELECT ... FROM
    with pytest.raises(ArbitraryQueryViolationError) as exc_info:
        AntiArbitraryQueryGuard.inspect_query_parameter("query", "SELECT * FROM citizens WHERE id = '1'")
    assert "Arbitrary SQL/database queries are strictly forbidden" in str(exc_info.value)

    # Detects DROP TABLE
    with pytest.raises(ArbitraryQueryViolationError):
        AntiArbitraryQueryGuard.inspect_query_parameter("table", "DROP TABLE patients;")

    # Detects SQL injection UNION
    with pytest.raises(ArbitraryQueryViolationError):
        AntiArbitraryQueryGuard.inspect_query_parameter("id", "' UNION SELECT password FROM users --")


def test_anti_arbitrary_query_blocks_graphql():
    # Detects raw GraphQL query
    with pytest.raises(ArbitraryQueryViolationError) as exc_info:
        AntiArbitraryQueryGuard.inspect_query_parameter("gql", "query { patient(id: 1) { name } }")
    assert "Arbitrary GraphQL queries are strictly forbidden" in str(exc_info.value)

    # Detects GraphQL schema introspection
    with pytest.raises(ArbitraryQueryViolationError):
        AntiArbitraryQueryGuard.inspect_query_parameter("query", "{ __schema { types { name } } }")


@pytest.mark.asyncio
async def test_adapter_rejects_query_injection_attempt(clinician_context):
    adapter = EmrGqlAdapter()
    malicious_id = "cit_001' UNION SELECT * FROM users --"

    with pytest.raises(ArbitraryQueryViolationError):
        await adapter.get_observations(malicious_id, clinician_context)


# ==============================================================================
# 6. RBAC PERMISSION ENFORCEMENT TESTS
# ==============================================================================

def test_rbac_citizen_access_control(citizen_context, other_citizen_context):
    # Citizen can access their own chart
    ClinicalRBACGuard.check_read_permission("cit_interop_001", citizen_context)

    # Citizen accessing another patient's chart is blocked
    with pytest.raises(AccessDeniedError) as exc_info:
        ClinicalRBACGuard.check_read_permission("cit_interop_001", other_citizen_context)
    assert "Citizens are only authorized to access their own clinical records" in str(exc_info.value)


def test_rbac_public_health_admin_restricted(public_health_admin_context):
    # Public health admin is restricted from reading identifiable patient chart
    with pytest.raises(AccessDeniedError) as exc_info:
        ClinicalRBACGuard.check_read_permission("cit_interop_001", public_health_admin_context)
    assert "Public health administrators are restricted" in str(exc_info.value)


def test_rbac_clinician_permitted(clinician_context):
    # Clinician is authorized for clinical care delivery
    ClinicalRBACGuard.check_read_permission("cit_interop_001", clinician_context)


# ==============================================================================
# 7. AUDIT LOGGING TESTS
# ==============================================================================

def test_clinical_access_audit_logger(clinician_context):
    entry = ClinicalAccessAuditLogger.log_access(
        context=clinician_context,
        patient_id="cit_interop_001",
        source_system="SEVAHEALTH_LOCAL",
        resource_type="Observation",
        items_count=3,
        status="GRANTED",
    )

    assert entry["actor_id"] == "clinician_001"
    assert entry["patient_id"] == "cit_interop_001"
    assert entry["status"] == "GRANTED"
    assert entry["items_count"] == 3

    logs = ClinicalAccessAuditLogger.get_audit_trail(patient_id="cit_interop_001")
    assert len(logs) >= 1
    assert any(l["event_id"] == entry["event_id"] for l in logs)


# ==============================================================================
# 8. FEDERATED CLINICAL DATA PROVIDER INTEGRATION TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_federated_chart_aggregates_and_deduplicates(clinician_context):
    # Setup federated provider with configured test adapters
    local_ad = SevaHealthLocalAdapter()
    emr_ad = EmrGqlAdapter()
    hms_ad = HmsAdapter()
    openehr_ad = OpenEhrEhrBaseAdapter()

    # Seed same medication Metformin 500mg in both local and emr_gql
    emr_ad.seed_fhir_resource(
        "cit_interop_001",
        "MedicationRequest",
        {
            "id": "fhir_med_dup",
            "medicationCodeableConcept": {"coding": [{"display": "Metformin 500mg"}]},
            "status": "active",
        }
    )

    # Seed unique medication in HMS
    hms_ad.seed_consultation(
        "cit_interop_001",
        {
            "id": 999,
            "status": "COMPLETED",
            "medication_requests": [{"medication_name": "Atorvastatin 10mg"}],
        }
    )

    service = FederatedClinicalDataProvider(
        local_adapter=local_ad,
        openehr_adapter=openehr_ad,
        emr_gql_adapter=emr_ad,
        hms_adapter=hms_ad,
    )

    # Retrieve federated medications
    meds = await service.get_medications("cit_interop_001", clinician_context)
    med_names = [m.medication_name.lower() for m in meds]

    # Verify deduplication: Metformin 500mg appears only once
    assert med_names.count("metformin 500mg") == 1
    # Verify HMS medication Atorvastatin is included
    assert "atorvastatin 10mg" in med_names

    # Retrieve complete federated chart
    chart = await service.get_federated_chart("cit_interop_001", clinician_context)
    assert isinstance(chart, FederatedClinicalChart)
    assert chart.patient is not None
    assert chart.patient.name == "Ramesh Gowda"
    assert len(chart.medications) >= 2
    assert len(chart.source_systems_queried) == 4


# ==============================================================================
# 9. AI AGENT CONTROLLED TOOLS TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_ai_agent_controlled_tools():
    actor = TokenPayload(
        sub="clinician_001",
        role=UserRole.CLINICIAN,
        tenant_id="karnataka_state_health",
        exp=9999999999,
    )

    # Controlled tool call
    res = await tool_get_federated_patient("cit_interop_001", actor)
    assert res["status"] == "SUCCESS"
    assert res["patient"]["name"] == "Ramesh Gowda"

    vitals_res = await tool_get_federated_vitals_and_labs("cit_interop_001", actor)
    assert vitals_res["status"] == "SUCCESS"
    assert vitals_res["count"] >= 1

    chart_res = await tool_get_federated_clinical_chart("cit_interop_001", actor)
    assert chart_res["status"] == "SUCCESS"
    assert "chart" in chart_res


@pytest.mark.asyncio
async def test_ai_prevention_agent_blocks_arbitrary_query():
    actor = TokenPayload(
        sub="cit_interop_001",
        role=UserRole.CITIZEN,
        tenant_id="karnataka_state_health",
        exp=9999999999,
    )

    # Attack prompt containing SQL injection
    attack_prompt = "SELECT * FROM citizens WHERE id = 'cit_interop_001'"
    response = await prevention_agent.chat(
        citizen_id="cit_interop_001",
        user_query=attack_prompt,
        actor=actor,
    )

    assert "SECURITY_ALERT" in response.answer
    assert "strictly prohibited" in response.answer


# ==============================================================================
# 10. REST API ENDPOINT TESTS
# ==============================================================================

def test_api_interop_adapters_health():
    response = client.get("/api/v1/interop/adapters")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert len(data["adapters"]) == 4


def test_api_interop_patient_endpoint():
    token = create_access_token(
        subject="clinician_001",
        tenant_id="karnataka_state_health",
        role=UserRole.CLINICIAN,
    )
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/interop/patient/cit_interop_001", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Ramesh Gowda"
    assert data["source_system"] == "SEVAHEALTH_LOCAL"


def test_api_interop_rbac_denied_for_other_citizen():
    other_token = create_access_token(
        subject="other_citizen_999",
        tenant_id="karnataka_state_health",
        role=UserRole.CITIZEN,
    )
    headers = {"Authorization": f"Bearer {other_token}"}

    response = client.get("/api/v1/interop/patient/cit_interop_001", headers=headers)
    assert response.status_code == 403
    assert "Access denied" in response.json()["detail"]


def test_api_interop_blocks_arbitrary_sql():
    token = create_access_token(
        subject="clinician_001",
        tenant_id="karnataka_state_health",
        role=UserRole.CLINICIAN,
    )
    headers = {"Authorization": f"Bearer {token}"}

    # Malicious injection attempt in path parameter
    malicious_id = "cit_001' UNION SELECT 1,2,3 --"
    response = client.get(f"/api/v1/interop/patient/{malicious_id}", headers=headers)
    assert response.status_code == 400
    assert "Arbitrary SQL/database queries are strictly forbidden" in response.json()["detail"]


def test_api_interop_audit_logs():
    token = create_access_token(
        subject="clinician_001",
        tenant_id="karnataka_state_health",
        role=UserRole.CLINICIAN,
    )
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/interop/audit-logs?patient_id=cit_interop_001", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
