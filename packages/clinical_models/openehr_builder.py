from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import uuid

from packages.clinical_models.domain_models import (
    VitalSign,
    LabResult,
    ClinicalEncounter,
    CarePlan,
    ProvenanceRecord,
)


def _iso_now(dt: Optional[datetime] = None) -> str:
    if dt:
        return dt.isoformat()
    return datetime.now(timezone.utc).isoformat()


def build_ehr_status(subject_id: str, namespace: str = "in.gov.abdm") -> Dict[str, Any]:
    """Generates canonical openEHR EHR_STATUS payload."""
    return {
        "_type": "EHR_STATUS",
        "archetype_node_id": "openEHR-EHR-EHR_STATUS.generic.v1",
        "name": {
            "_type": "DV_TEXT",
            "value": "SevaHealth Patient EHR Status"
        },
        "subject": {
            "_type": "PARTY_SELF",
            "external_ref": {
                "_type": "PARTY_REF",
                "id": {
                    "_type": "GENERIC_ID",
                    "value": subject_id,
                    "scheme": namespace,
                },
                "namespace": namespace,
                "type": "PERSON",
            }
        },
        "is_queryable": True,
        "is_modifiable": True,
    }


def build_vital_signs_composition(
    vitals: List[VitalSign],
    composer_name: str = "SevaHealth Clinical Worker",
    facility_name: str = "Nanjangud Community Health Centre",
) -> Dict[str, Any]:
    """Builds canonical openEHR COMPOSITION.encounter.v1 containing vital signs observations."""
    composition_time = vitals[0].measurement_timestamp if vitals else datetime.now(timezone.utc)
    content: List[Dict[str, Any]] = []

    # Blood Pressure grouping (if systolic or diastolic exist)
    systolic = next((v for v in vitals if v.clinical_type == "SYSTOLIC_BP"), None)
    diastolic = next((v for v in vitals if v.clinical_type == "DIASTOLIC_BP"), None)

    if systolic or diastolic:
        bp_items = []
        if systolic:
            bp_items.append({
                "_type": "ELEMENT",
                "archetype_node_id": "at0004",
                "name": {"_type": "DV_TEXT", "value": "Systolic"},
                "value": {
                    "_type": "DV_QUANTITY",
                    "magnitude": float(systolic.value),
                    "units": systolic.unit,
                }
            })
        if diastolic:
            bp_items.append({
                "_type": "ELEMENT",
                "archetype_node_id": "at0005",
                "name": {"_type": "DV_TEXT", "value": "Diastolic"},
                "value": {
                    "_type": "DV_QUANTITY",
                    "magnitude": float(diastolic.value),
                    "units": diastolic.unit,
                }
            })

        content.append({
            "_type": "OBSERVATION",
            "archetype_node_id": "openEHR-EHR-OBSERVATION.blood_pressure.v2",
            "name": {"_type": "DV_TEXT", "value": "Blood Pressure"},
            "language": {"_type": "CODE_PHRASE", "terminology_id": {"value": "ISO_639-1"}, "code_string": "en"},
            "encoding": {"_type": "CODE_PHRASE", "terminology_id": {"value": "IANA_character-sets"}, "code_string": "UTF-8"},
            "subject": {"_type": "PARTY_SELF"},
            "data": {
                "_type": "HISTORY",
                "archetype_node_id": "at0001",
                "name": {"_type": "DV_TEXT", "value": "history"},
                "origin": {"_type": "DV_DATE_TIME", "value": _iso_now(composition_time)},
                "events": [{
                    "_type": "POINT_EVENT",
                    "archetype_node_id": "at0002",
                    "name": {"_type": "DV_TEXT", "value": "Any event"},
                    "time": {"_type": "DV_DATE_TIME", "value": _iso_now(composition_time)},
                    "data": {
                        "_type": "ITEM_TREE",
                        "archetype_node_id": "at0003",
                        "name": {"_type": "DV_TEXT", "value": "blood pressure"},
                        "items": bp_items,
                    }
                }]
            }
        })

    # Pulse / Heart rate
    hr = next((v for v in vitals if v.clinical_type == "HEART_RATE"), None)
    if hr:
        content.append({
            "_type": "OBSERVATION",
            "archetype_node_id": "openEHR-EHR-OBSERVATION.pulse.v1",
            "name": {"_type": "DV_TEXT", "value": "Pulse/Heart beat"},
            "language": {"_type": "CODE_PHRASE", "terminology_id": {"value": "ISO_639-1"}, "code_string": "en"},
            "encoding": {"_type": "CODE_PHRASE", "terminology_id": {"value": "IANA_character-sets"}, "code_string": "UTF-8"},
            "subject": {"_type": "PARTY_SELF"},
            "data": {
                "_type": "HISTORY",
                "archetype_node_id": "at0002",
                "name": {"_type": "DV_TEXT", "value": "history"},
                "origin": {"_type": "DV_DATE_TIME", "value": _iso_now(hr.measurement_timestamp)},
                "events": [{
                    "_type": "POINT_EVENT",
                    "archetype_node_id": "at0003",
                    "name": {"_type": "DV_TEXT", "value": "Any event"},
                    "time": {"_type": "DV_DATE_TIME", "value": _iso_now(hr.measurement_timestamp)},
                    "data": {
                        "_type": "ITEM_TREE",
                        "archetype_node_id": "at0001",
                        "name": {"_type": "DV_TEXT", "value": "Structure"},
                        "items": [{
                            "_type": "ELEMENT",
                            "archetype_node_id": "at0004",
                            "name": {"_type": "DV_TEXT", "value": "Rate"},
                            "value": {
                                "_type": "DV_QUANTITY",
                                "magnitude": float(hr.value),
                                "units": hr.unit,
                            }
                        }]
                    }
                }]
            }
        })

    # Body Mass Index (BMI)
    bmi = next((v for v in vitals if v.clinical_type == "BMI"), None)
    if bmi:
        content.append({
            "_type": "OBSERVATION",
            "archetype_node_id": "openEHR-EHR-OBSERVATION.body_mass_index.v2",
            "name": {"_type": "DV_TEXT", "value": "Body mass index"},
            "language": {"_type": "CODE_PHRASE", "terminology_id": {"value": "ISO_639-1"}, "code_string": "en"},
            "encoding": {"_type": "CODE_PHRASE", "terminology_id": {"value": "IANA_character-sets"}, "code_string": "UTF-8"},
            "subject": {"_type": "PARTY_SELF"},
            "data": {
                "_type": "HISTORY",
                "archetype_node_id": "at0001",
                "name": {"_type": "DV_TEXT", "value": "history"},
                "origin": {"_type": "DV_DATE_TIME", "value": _iso_now(bmi.measurement_timestamp)},
                "events": [{
                    "_type": "POINT_EVENT",
                    "archetype_node_id": "at0002",
                    "name": {"_type": "DV_TEXT", "value": "Any event"},
                    "time": {"_type": "DV_DATE_TIME", "value": _iso_now(bmi.measurement_timestamp)},
                    "data": {
                        "_type": "ITEM_TREE",
                        "archetype_node_id": "at0003",
                        "name": {"_type": "DV_TEXT", "value": "Single"},
                        "items": [{
                            "_type": "ELEMENT",
                            "archetype_node_id": "at0004",
                            "name": {"_type": "DV_TEXT", "value": "Body mass index"},
                            "value": {
                                "_type": "DV_QUANTITY",
                                "magnitude": float(bmi.value),
                                "units": bmi.unit,
                            }
                        }]
                    }
                }]
            }
        })

    # Waist Circumference
    waist = next((v for v in vitals if v.clinical_type == "WAIST_CIRCUMFERENCE"), None)
    if waist:
        content.append({
            "_type": "OBSERVATION",
            "archetype_node_id": "openEHR-EHR-OBSERVATION.waist_circumference.v1",
            "name": {"_type": "DV_TEXT", "value": "Waist circumference"},
            "language": {"_type": "CODE_PHRASE", "terminology_id": {"value": "ISO_639-1"}, "code_string": "en"},
            "encoding": {"_type": "CODE_PHRASE", "terminology_id": {"value": "IANA_character-sets"}, "code_string": "UTF-8"},
            "subject": {"_type": "PARTY_SELF"},
            "data": {
                "_type": "HISTORY",
                "archetype_node_id": "at0001",
                "name": {"_type": "DV_TEXT", "value": "history"},
                "origin": {"_type": "DV_DATE_TIME", "value": _iso_now(waist.measurement_timestamp)},
                "events": [{
                    "_type": "POINT_EVENT",
                    "archetype_node_id": "at0002",
                    "name": {"_type": "DV_TEXT", "value": "Any event"},
                    "time": {"_type": "DV_DATE_TIME", "value": _iso_now(waist.measurement_timestamp)},
                    "data": {
                        "_type": "ITEM_TREE",
                        "archetype_node_id": "at0003",
                        "name": {"_type": "DV_TEXT", "value": "Tree"},
                        "items": [{
                            "_type": "ELEMENT",
                            "archetype_node_id": "at0004",
                            "name": {"_type": "DV_TEXT", "value": "Waist circumference"},
                            "value": {
                                "_type": "DV_QUANTITY",
                                "magnitude": float(waist.value),
                                "units": waist.unit,
                            }
                        }]
                    }
                }]
            }
        })

    return {
        "_type": "COMPOSITION",
        "name": {"_type": "DV_TEXT", "value": "Physical Vitals Screening Encounter"},
        "archetype_node_id": "openEHR-EHR-COMPOSITION.encounter.v1",
        "archetype_details": {
            "archetype_id": {"value": "openEHR-EHR-COMPOSITION.encounter.v1"},
            "template_id": {"value": "SevaHealth_Vitals_Screening_v1"},
            "rm_version": "1.0.4",
        },
        "language": {"_type": "CODE_PHRASE", "terminology_id": {"value": "ISO_639-1"}, "code_string": "en"},
        "territory": {"_type": "CODE_PHRASE", "terminology_id": {"value": "ISO_3166-1"}, "code_string": "IN"},
        "category": {
            "_type": "DV_CODED_TEXT",
            "value": "event",
            "defining_code": {"_type": "CODE_PHRASE", "terminology_id": {"value": "openehr"}, "code_string": "433"}
        },
        "composer": {"_type": "PARTY_IDENTIFIED", "name": composer_name},
        "context": {
            "_type": "EVENT_CONTEXT",
            "start_time": {"_type": "DV_DATE_TIME", "value": _iso_now(composition_time)},
            "setting": {
                "_type": "DV_CODED_TEXT",
                "value": "primary medical care",
                "defining_code": {"_type": "CODE_PHRASE", "terminology_id": {"value": "openehr"}, "code_string": "228"}
            },
            "location": facility_name,
        },
        "content": content,
    }


def build_laboratory_composition(
    labs: List[LabResult],
    composer_name: str = "PHC Diagnostic Laboratory",
    facility_name: str = "Nanjangud Primary Health Centre",
) -> Dict[str, Any]:
    """Builds canonical openEHR COMPOSITION.encounter.v1 containing laboratory test observations."""
    composition_time = labs[0].measurement_timestamp if labs else datetime.now(timezone.utc)
    lab_items = []

    for lab in labs:
        lab_items.append({
            "_type": "OBSERVATION",
            "archetype_node_id": "openEHR-EHR-OBSERVATION.laboratory_test_result.v1",
            "name": {"_type": "DV_TEXT", "value": lab.test_name.replace("_", " ").title()},
            "language": {"_type": "CODE_PHRASE", "terminology_id": {"value": "ISO_639-1"}, "code_string": "en"},
            "encoding": {"_type": "CODE_PHRASE", "terminology_id": {"value": "IANA_character-sets"}, "code_string": "UTF-8"},
            "subject": {"_type": "PARTY_SELF"},
            "data": {
                "_type": "HISTORY",
                "archetype_node_id": "at0001",
                "name": {"_type": "DV_TEXT", "value": "history"},
                "origin": {"_type": "DV_DATE_TIME", "value": _iso_now(lab.measurement_timestamp)},
                "events": [{
                    "_type": "POINT_EVENT",
                    "archetype_node_id": "at0002",
                    "name": {"_type": "DV_TEXT", "value": "Any event"},
                    "time": {"_type": "DV_DATE_TIME", "value": _iso_now(lab.measurement_timestamp)},
                    "data": {
                        "_type": "ITEM_TREE",
                        "archetype_node_id": "at0003",
                        "name": {"_type": "DV_TEXT", "value": "Tree"},
                        "items": [
                            {
                                "_type": "ELEMENT",
                                "archetype_node_id": "at0005",
                                "name": {"_type": "DV_TEXT", "value": "Test name"},
                                "value": {
                                    "_type": "DV_CODED_TEXT",
                                    "value": lab.test_name,
                                    "defining_code": {
                                        "_type": "CODE_PHRASE",
                                        "terminology_id": {"value": "LOINC"},
                                        "code_string": lab.loinc_code,
                                    }
                                }
                            },
                            {
                                "_type": "ELEMENT",
                                "archetype_node_id": "at0001",
                                "name": {"_type": "DV_TEXT", "value": "Result value"},
                                "value": {
                                    "_type": "DV_QUANTITY",
                                    "magnitude": float(lab.value),
                                    "units": lab.unit,
                                }
                            },
                            {
                                "_type": "ELEMENT",
                                "archetype_node_id": "at0004",
                                "name": {"_type": "DV_TEXT", "value": "Reference range"},
                                "value": {"_type": "DV_TEXT", "value": lab.reference_range}
                            },
                            {
                                "_type": "ELEMENT",
                                "archetype_node_id": "at0008",
                                "name": {"_type": "DV_TEXT", "value": "Interpretation"},
                                "value": {"_type": "DV_TEXT", "value": lab.interpretation}
                            }
                        ]
                    }
                }]
            }
        })

    return {
        "_type": "COMPOSITION",
        "name": {"_type": "DV_TEXT", "value": "Diagnostic Laboratory Report"},
        "archetype_node_id": "openEHR-EHR-COMPOSITION.report-result.v1",
        "archetype_details": {
            "archetype_id": {"value": "openEHR-EHR-COMPOSITION.report-result.v1"},
            "template_id": {"value": "SevaHealth_Lab_Report_v1"},
            "rm_version": "1.0.4",
        },
        "language": {"_type": "CODE_PHRASE", "terminology_id": {"value": "ISO_639-1"}, "code_string": "en"},
        "territory": {"_type": "CODE_PHRASE", "terminology_id": {"value": "ISO_3166-1"}, "code_string": "IN"},
        "category": {
            "_type": "DV_CODED_TEXT",
            "value": "event",
            "defining_code": {"_type": "CODE_PHRASE", "terminology_id": {"value": "openehr"}, "code_string": "433"}
        },
        "composer": {"_type": "PARTY_IDENTIFIED", "name": composer_name},
        "context": {
            "_type": "EVENT_CONTEXT",
            "start_time": {"_type": "DV_DATE_TIME", "value": _iso_now(composition_time)},
            "setting": {
                "_type": "DV_CODED_TEXT",
                "value": "laboratory",
                "defining_code": {"_type": "CODE_PHRASE", "terminology_id": {"value": "openehr"}, "code_string": "261"}
            },
            "location": facility_name,
        },
        "content": lab_items,
    }


def build_clinical_encounter_composition(encounter: ClinicalEncounter) -> Dict[str, Any]:
    """Builds canonical openEHR COMPOSITION.encounter.v1 with structured SOAP notes."""
    return {
        "_type": "COMPOSITION",
        "name": {"_type": "DV_TEXT", "value": f"Clinical Consultation: {encounter.reason_for_visit}"},
        "archetype_node_id": "openEHR-EHR-COMPOSITION.encounter.v1",
        "archetype_details": {
            "archetype_id": {"value": "openEHR-EHR-COMPOSITION.encounter.v1"},
            "template_id": {"value": "SevaHealth_Encounter_SOAP_v1"},
            "rm_version": "1.0.4",
        },
        "language": {"_type": "CODE_PHRASE", "terminology_id": {"value": "ISO_639-1"}, "code_string": "en"},
        "territory": {"_type": "CODE_PHRASE", "terminology_id": {"value": "ISO_3166-1"}, "code_string": "IN"},
        "category": {
            "_type": "DV_CODED_TEXT",
            "value": "event",
            "defining_code": {"_type": "CODE_PHRASE", "terminology_id": {"value": "openehr"}, "code_string": "433"}
        },
        "composer": {"_type": "PARTY_IDENTIFIED", "name": encounter.clinician_id},
        "context": {
            "_type": "EVENT_CONTEXT",
            "start_time": {"_type": "DV_DATE_TIME", "value": _iso_now(encounter.started_at)},
            "end_time": {"_type": "DV_DATE_TIME", "value": _iso_now(encounter.ended_at)} if encounter.ended_at else None,
            "setting": {
                "_type": "DV_CODED_TEXT",
                "value": "primary medical care",
                "defining_code": {"_type": "CODE_PHRASE", "terminology_id": {"value": "openehr"}, "code_string": "228"}
            },
        },
        "content": [
            {
                "_type": "SECTION",
                "archetype_node_id": "openEHR-EHR-SECTION.soap.v1",
                "name": {"_type": "DV_TEXT", "value": "SOAP Clinical Notes"},
                "items": [
                    {
                        "_type": "EVALUATION",
                        "archetype_node_id": "openEHR-EHR-EVALUATION.reason_for_encounter.v1",
                        "name": {"_type": "DV_TEXT", "value": "Reason for encounter"},
                        "language": {"_type": "CODE_PHRASE", "terminology_id": {"value": "ISO_639-1"}, "code_string": "en"},
                        "encoding": {"_type": "CODE_PHRASE", "terminology_id": {"value": "IANA_character-sets"}, "code_string": "UTF-8"},
                        "subject": {"_type": "PARTY_SELF"},
                        "data": {
                            "_type": "ITEM_TREE",
                            "archetype_node_id": "at0001",
                            "name": {"_type": "DV_TEXT", "value": "Tree"},
                            "items": [
                                {
                                    "_type": "ELEMENT",
                                    "archetype_node_id": "at0002",
                                    "name": {"_type": "DV_TEXT", "value": "Subjective"},
                                    "value": {"_type": "DV_TEXT", "value": encounter.soap_subjective}
                                },
                                {
                                    "_type": "ELEMENT",
                                    "archetype_node_id": "at0003",
                                    "name": {"_type": "DV_TEXT", "value": "Objective"},
                                    "value": {"_type": "DV_TEXT", "value": encounter.soap_objective}
                                },
                                {
                                    "_type": "ELEMENT",
                                    "archetype_node_id": "at0004",
                                    "name": {"_type": "DV_TEXT", "value": "Assessment"},
                                    "value": {"_type": "DV_TEXT", "value": encounter.soap_assessment}
                                },
                                {
                                    "_type": "ELEMENT",
                                    "archetype_node_id": "at0005",
                                    "name": {"_type": "DV_TEXT", "value": "Plan"},
                                    "value": {"_type": "DV_TEXT", "value": encounter.soap_plan}
                                },
                            ]
                        }
                    }
                ]
            }
        ]
    }


def build_care_plan_composition(care_plan: CarePlan) -> Dict[str, Any]:
    """Builds canonical openEHR COMPOSITION.care_plan.v1."""
    return {
        "_type": "COMPOSITION",
        "name": {"_type": "DV_TEXT", "value": care_plan.title},
        "archetype_node_id": "openEHR-EHR-COMPOSITION.care_plan.v1",
        "archetype_details": {
            "archetype_id": {"value": "openEHR-EHR-COMPOSITION.care_plan.v1"},
            "template_id": {"value": "SevaHealth_Care_Plan_v1"},
            "rm_version": "1.0.4",
        },
        "language": {"_type": "CODE_PHRASE", "terminology_id": {"value": "ISO_639-1"}, "code_string": "en"},
        "territory": {"_type": "CODE_PHRASE", "terminology_id": {"value": "ISO_3166-1"}, "code_string": "IN"},
        "category": {
            "_type": "DV_CODED_TEXT",
            "value": "persistent",
            "defining_code": {"_type": "CODE_PHRASE", "terminology_id": {"value": "openehr"}, "code_string": "431"}
        },
        "composer": {"_type": "PARTY_IDENTIFIED", "name": care_plan.lead_clinician_id or "Care Team"},
        "context": {
            "_type": "EVENT_CONTEXT",
            "start_time": {"_type": "DV_DATE_TIME", "value": _iso_now(care_plan.created_at)},
            "setting": {
                "_type": "DV_CODED_TEXT",
                "value": "other care",
                "defining_code": {"_type": "CODE_PHRASE", "terminology_id": {"value": "openehr"}, "code_string": "238"}
            },
        },
        "content": [
            {
                "_type": "INSTRUCTION",
                "archetype_node_id": "openEHR-EHR-INSTRUCTION.care_plan.v1",
                "name": {"_type": "DV_TEXT", "value": "Care Plan Protocol"},
                "language": {"_type": "CODE_PHRASE", "terminology_id": {"value": "ISO_639-1"}, "code_string": "en"},
                "encoding": {"_type": "CODE_PHRASE", "terminology_id": {"value": "IANA_character-sets"}, "code_string": "UTF-8"},
                "subject": {"_type": "PARTY_SELF"},
                "narrative": {"_type": "DV_TEXT", "value": f"Status: {care_plan.status}"},
            }
        ]
    }
