import pytest
from packages.clinical_models.observations import Observation
from packages.clinical_models.fhir import (
    export_patient_fhir_r4,
    export_observation_fhir_r4,
)


def test_fhir_patient_export():
    fhir_p = export_patient_fhir_r4(
        citizen_id="c-001",
        first_name="Ramesh",
        last_name="Patel",
        gender="MALE",
        birth_date="1978-04-12",
        phone="+919845012345",
        abha_id="91-4829-1029-4820",
    )

    assert fhir_p["resourceType"] == "Patient"
    assert fhir_p["id"] == "c-001"
    assert fhir_p["name"][0]["family"] == "Patel"
    assert fhir_p["gender"] == "male"
    assert any(i["value"] == "91-4829-1029-4820" for i in fhir_p["identifier"])


def test_fhir_observation_export():
    obs = Observation(
        citizen_id="c-001",
        tenant_id="t-001",
        code="HBA1C",
        value=6.2,
        unit="%",
        loinc_code="4548-4",
        display_name="Hemoglobin A1c",
    )
    fhir_obs = export_observation_fhir_r4(obs)

    assert fhir_obs["resourceType"] == "Observation"
    assert fhir_obs["status"] == "final"
    assert fhir_obs["code"]["coding"][0]["code"] == "4548-4"
    assert fhir_obs["valueQuantity"]["value"] == 6.2
    assert fhir_obs["valueQuantity"]["unit"] == "%"
