# SevaHealth AI — Challenge Demonstration Script

> **Intended Audience**: Seva First Innovation Challenge Judges, Technical Evaluators & Clinicians  
> **Estimated Execution Time**: < 5 Minutes (Automated Workflow completes in ~2 seconds)  
> **Primary Command**: `make demo` (or `./scripts/demo.sh` / `python scripts/demo.py`)

---

## Demonstration Narrative: The Story of a Citizen

Our demonstration tells the story of a citizen (**Devendra Sharma / Ramesh Patel**, 52-year-old schoolteacher).
- He feels completely healthy.
- Subclinically, he is experiencing silent metabolic and cardiovascular drift.
- SevaHealth AI detects the worsening trajectory, explains the drivers, engages the citizen, connects wearable tracking, detects rapid deterioration, alerts a clinician, structures an intervention, and reverses the trajectory—demonstrating measurable public health value.

---

## Step-by-Step 16-Stage Demonstration Script

### STEP 1: Frontline Citizen Registration
- **Actor**: Frontline Health Worker (ASHA / ANM)
- **Interface**: [http://localhost:8000/health-worker-app](http://localhost:8000/health-worker-app)
- **Action**: Health worker enters citizen basic demographic details (ABHA ID, age 52, gender M, phone, Mysuru district).
- **Key Talking Point**: *"Notice the large 48px touch targets and offline-tolerant caching. An intake takes under 45 seconds."*

### STEP 2: NCD Screening Intake
- **Actor**: Citizen with Health Worker assistance
- **Action**: Completes digital CBAC (Community-Based Assessment Checklist) and IDRS (Indian Diabetes Risk Score) survey. Enters Omron BP (134/86 mmHg), fasting capillary blood glucose (114 mg/dL), waist circumference (94 cm).
- **Key Talking Point**: *"Zero manual scoring. The platform automatically maps LOINC codes and validates range boundaries."*

### STEP 3: Multi-Dimensional Risk Calculation
- **Actor**: Deterministic Clinical Engine
- **Result**: Baseline Metabolic Risk = **52.0% (MODERATE)**. Cardiovascular Risk = **38% (MILD)**.
- **Key Talking Point**: *"Crucially, this is NOT computed by an unconstrained LLM. It is calculated using validated ICMR-INDIAB and WHO Asian Indian scoring charts."*

### STEP 4: Explainable AI Trajectory Attribution
- **Actor**: AI Decision Intelligence Engine
- **Interface**: [http://localhost:8000/citizen-app](http://localhost:8000/citizen-app)
- **Result**: Generates plain-language waterfall:
  - Waist circumference and weight drift: +14% risk contribution
  - Fasting glycemic drift: +9% risk contribution
  - Non-smoker protective factor: -7%
- **Key Talking Point**: *"No black box. The citizen sees WHY their risk is elevated in simple Kannada, Hindi, or English."*

### STEP 5: Personalized Prevention Plan Generation
- **Actor**: Prevention Planning Agent
- **Result**: Creates a 30-Day Multi-Pillar Lifestyle Care Plan:
  - Nutrition: Replace polished white rice with foxtail millet at dinner; drink 2.5L water daily.
  - Physical Activity: 30-minute brisk morning walk (target: 7,500 daily steps).
  - Sleep & Stress: 10-minute bedtime breathwork; sleep before 10:30 PM.

### STEP 6: Wearable Device Connection
- **Actor**: Citizen
- **Action**: Connects consumer smart band via self-hosted Open Wearables integration.
- **Key Talking Point**: *"We don't demand expensive proprietary hardware. We ingest Apple Health, Garmin, Fitbit, or sub-$20 Noise/Boat trackers."*

### STEP 7: Continuous Passive Telemetry Ingestion
- **Actor**: Open Wearables Pipeline
- **Result**: System ingests 14 days of continuous step count, resting heart rate, and sleep metrics. Establishes a rolling 7-day physiological baseline.

### STEP 8: Trajectory Velocity Shift (Silent Drift)
- **Actor**: Trajectory Engine
- **Result**: Over the next 6 months, citizen undergoes subclinical lifestyle deterioration:
  - Daily steps drop from 7,200 to 3,100 steps/day.
  - Mean blood pressure drifts upward to 158/96 mmHg.
  - HbA1c rises from 6.1% to 6.9%.
  - Metabolic Risk accelerates to **81.0% (HIGH)**.

### STEP 9: AI Detects Trajectory Deterioration
- **Actor**: AI Surveillance Agent
- **Result**: Calculates positive risk velocity (+35% increase per quarter). Triggers automated trajectory shift from `STABLE` to `DETERIORATING`.

### STEP 10: High-Priority Clinical Alert Dispatch
- **Actor**: System Safety Dispatcher
- **Result**: Because SBP > 150 mmHg and HbA1c > 6.5%, the system immediately generates an emergent notification and routes the case to the **Clinician Triage Queue**.

### STEP 11: Clinician Review & Copilot Triage
- **Actor**: Primary Care Physician (PHC Medical Officer)
- **Interface**: [http://localhost:8000/clinician-app](http://localhost:8000/clinician-app)
- **Action**: Doctor opens the automated pre-compiled **SOAP Clinical Summary**:
  - *Subjective*: Citizen reports fatigue, sedentary work hours.
  - *Objective*: SBP 158/96, HbA1c 6.9%, RHR 82 bpm, average steps 3,100.
  - *Assessment*: Worsening Metabolic Syndrome drifting into Stage 1 Hypertension & Type 2 Diabetes.
  - *Plan*: Diet modification, daily exercise reinforcement, low-dose Metformin proposal.

### STEP 12: Clinician Modifies & Digitally Signs Care Plan
- **Actor**: Clinician
- **Action**: Physician reviews AI-proposed care plan, approves lifestyle pillars, attaches medical digital stamp, and orders a 30-day follow-up.
- **Key Talking Point**: *"Human in the loop. The AI proposes, but the licensed physician disposes."*

### STEP 13: Citizen Receives Tailored Intervention
- **Actor**: Citizen Mobile App
- **Result**: Citizen receives updated vernacular audio notification and daily micro-habit schedule on their smartphone.

### STEP 14: Follow-up Measurement Recorded
- **Actor**: Health Worker at follow-up visit
- **Action**: ASHA records 30-day follow-up vitals: SBP reduced to 124/80 mmHg, daily steps increased to 8,400, weight reduced by 2.2 kg.

### STEP 15: Risk Trajectory Reversal Verified
- **Actor**: Trajectory Engine
- **Result**: Metabolic Risk score falls to **22.5% (LOW / IMPROVED)**. Net trajectory improvement = **72.2% Risk Reduction**.

### STEP 16: Population Dashboard Reflects Cohort Impact
- **Actor**: Public Health Officer
- **Interface**: [http://localhost:8000/public-health-app](http://localhost:8000/public-health-app)
- **Result**: Aggregate district dashboard updates in real-time:
  - Ward 12 risk concentration drops.
  - Program ROI indicates ₹37,800,000 projected healthcare savings per 10k cohort.
  - Defaulter roster automatically clears Devendra Sharma as "Follow-up Completed".

---

## How to Run the Demonstration Live

### Option A: Complete Single-Command Execution
```bash
python scripts/demo.py
# Or: make demo
# Or: ./scripts/demo.sh (Linux/macOS)
# Or: .\scripts\demo.bat (Windows)
```

### Option B: Interactive 16-Step Step-by-Step Mode
```bash
python scripts/run_challenge_demo.py --interactive
```

### Option C: Instant Reset Button
To wipe all challenge modifications and restore the clean seed state:
```bash
python scripts/run_challenge_demo.py --reset
```
