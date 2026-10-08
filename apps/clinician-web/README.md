# SevaHealth AI: Clinician Decision-Support & Triage Portal

**Platform:** Web Portal (Next.js / Tailwind CSS / shadcn/ui)  
**Primary Users:** Primary Care Physicians, Medical Officers, Specialists  
**Architectural Reference:** `bezs-hms` (DrGodly HMS) clinical review patterns  

---

## Clinical Triage & Decision-Support Workflow

1. **High-Risk Triage Queue:**
   - Automatically surfaces citizens whose multivariable risk score enters `HIGH` or `CRITICAL` tiers.
   - Categorizes urgency: `ROUTINE`, `PRIORITY` (within 14 days), `URGENT` (within 48 hours), or `EMERGENT` (immediate evaluation).
2. **Pre-Consultation SOAP Synthesis:**
   - Synthesizes Subjective, Objective, Assessment, and Plan notes from field screening surveys and wearable baselines.
   - Highlights key clinical drivers (e.g., *Impaired Glycemia HbA1c 6.2%*, *Stage 2 HTN 164/98 mmHg*).
3. **Doctor Review & Care Plan Sign-off:**
   - Provides explicit human-in-the-loop review actions: `APPROVED`, `MODIFIED`, or `REFERRED`.
   - Modifies 30-day preventive targets (e.g., sodium restriction < 2g/day).
   - Stamped with clinician ID and server-side timestamp for forensic auditability.
