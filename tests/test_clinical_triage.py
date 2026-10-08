import pytest
from packages.clinical_models.triage import ClinicalTriageCase, SOAPReport
from packages.types.enums import TriageUrgency, ClinicianReviewStatus
from services.store import store


def test_triage_case_lifecycle():
    case = ClinicalTriageCase(
        tenant_id="t1",
        citizen_id="c-lakshmi",
        citizen_name="Lakshmi Devi",
        risk_assessment_id="risk-02",
        urgency=TriageUrgency.EMERGENT,
        escalation_reason="Severe Stage 2 Hypertension (164/98 mmHg)",
        soap_note=SOAPReport(
            subjective="Elderly patient with headache.",
            objective="BP 164/98 mmHg.",
            assessment="Stage 2 HTN.",
            plan="Medical Officer review.",
        ),
    )
    store.add_triage_case(case)

    # Verify retrieval
    pending = store.list_triage_cases(status=ClinicianReviewStatus.PENDING)
    assert any(c.id == case.id for c in pending)

    # Perform clinician review
    case.status = ClinicianReviewStatus.APPROVED
    case.review_notes = "Verified in PHC clinic; lifestyle salt reduction confirmed."
    store.add_triage_case(case)

    approved = store.list_triage_cases(status=ClinicianReviewStatus.APPROVED)
    assert any(c.id == case.id for c in approved)
