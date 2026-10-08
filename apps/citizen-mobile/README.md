# SevaHealth AI: Citizen Mobile Application

**Platform:** Flutter (Dart >= 3.5.0)  
**Target:** Android & iOS (adapted from `DrGodly-Mobile-Aplication` architecture)  
**Primary Users:** Citizens & At-Risk Individuals  

---

## Architecture Overview

The Citizen Mobile application provides a clean, responsive, offline-first mobile client for citizens to conduct preventive health screening, monitor biometric vitals, track daily 30-day lifestyle medicine habits, and connect consumer smartwatches.

```
lib/
├── core/
│   ├── config/ (API base URLs, environment settings)
│   ├── theme/ (Clean medical blue/teal aesthetic)
│   └── network/ (Dio HTTP client with JWT interceptors)
├── data/
│   ├── service/ (fhir_api_client.dart, auth_service.dart)
│   ├── repository/ (Local SQLite cache via sqflite)
│   └── models/ (VitalsPayload, CarePlanModel, RiskAssessmentModel)
├── domain/
│   ├── usecases/ (SubmitScreening, SyncWearables, ToggleDailyTask)
│   └── entities/
├── view/
│   ├── auth/ (Login, ABHA ID linking)
│   ├── intake/ (Interactive CBAC/IDRS Screening Chat)
│   ├── dashboard/ (Vitals cards, Risk radar, Trajectory graph)
│   ├── care_plan/ (30-Day Daily Habit Checklist)
│   └── devices/ (Health Connect & Bluetooth LE 0x180D HRM Bridge)
└── viewmodel/ (Provider-based ViewModels for state management)
```

---

## Wearable & Hardware Sensor Bridge

Following the specification in `docs/open_wearables_device_compatibility.md`:
1. **Android Health Connect:** Directly bridges boAt, Noise, Fire-Boltt, Amazfit, and Samsung Galaxy Watch companion apps into normalized biometrics (Resting HR, HRV, Steps, Sleep).
2. **Standard Bluetooth LE (0x180D):** Directly connects standard BLE heart rate monitors (Polar, Scosche) without requiring external cloud accounts.
3. **FHIR Vitals Sync:** Pushes discrete vitals as HL7 FHIR R4 Observations to `/api/v1/wearables/sync/{citizen_id}`.
