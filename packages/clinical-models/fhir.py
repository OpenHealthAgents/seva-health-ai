from typing import Dict, Any, List
from packages.clinical_models.observations import Observation
from packages.clinical_models.risk import RiskAssessment


def export_patient_fhir_r4(
    citizen_id: str,
    first_name: str,
    last_name: str,
    gender: str,
    birth_date: str,
    phone: str,
    abha_id: str = None
) -> Dict[str, Any]:
    """Serializes a Citizen into an HL7 FHIR R4 Patient Resource."""
    identifiers = [
        {"system": "https://sevahealth.ai/citizen-id", "value": citizen_id}
    ]
    if abha_id:
        identifiers.append({"system": "https://abdm.gov.in/abha", "value": abha_id})

    return {
        "resourceType": "Patient",
        "id": citizen_id,
        "identifier": identifiers,
        "active": True,
        "name": [{
            "use": "official",
            "family": last_name,
            "given": [first_name]
        }],
        "telecom": [{
            "system": "phone",
            "value": phone,
            "use": "mobile"
        }],
        "gender": gender.lower() if gender in ["MALE", "FEMALE"] else "other",
        "birthDate": birth_date
    }


def export_observation_fhir_r4(obs: Observation) -> Dict[str, Any]:
    """Serializes an Observation into an HL7 FHIR R4 Observation Resource."""
    return {
        "resourceType": "Observation",
        "id": obs.id,
        "status": "final",
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": obs.loinc_code,
                "display": obs.display_name
            }]
        },
        "subject": {
            "reference": f"Patient/{obs.citizen_id}"
        },
        "effectiveDateTime": obs.recorded_at.isoformat(),
        "valueQuantity": {
            "value": obs.value,
            "unit": obs.unit,
            "system": "http://unitsofmeasure.org"
        },
        "interpretation": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                "code": "A" if obs.is_abnormal else "N",
                "display": "Abnormal" if obs.is_abnormal else "Normal"
            }]
        }]
    }


def export_risk_assessment_fhir_r4(risk: RiskAssessment) -> Dict[str, Any]:
    """Serializes a RiskAssessment into an HL7 FHIR R4 RiskAssessment Resource."""
    return {
        "resourceType": "RiskAssessment",
        "id": risk.id,
        "status": "final",
        "subject": {
            "reference": f"Patient/{risk.citizen_id}"
        },
        "occurrenceDateTime": risk.evaluated_at.isoformat(),
        "prediction": [{
            "probabilityDecimal": round(risk.overall_score, 4),
            "qualitativeRisk": {
                "coding": [{
                    "system": "https://sevahealth.ai/risk-tier",
                    "code": risk.overall_tier.value,
                    "display": f"{risk.overall_tier.value} Risk"
                }]
            },
            "rationale": risk.clinical_summary
        }],
        "note": [{
            "text": risk.safety_disclaimer
        }]
    }
