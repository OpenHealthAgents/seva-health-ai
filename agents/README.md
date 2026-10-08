# SevaHealth AI Agents Architecture

This directory houses the specialized preventive health AI agents configured with strict clinical safety boundaries:

```
agents/
├── prevention/    # Lifestyle medicine 30-day intervention planner (Nutrition, Activity, Sleep, Stress)
├── clinical/      # Clinician pre-consult triage summary & SOAP synthesis agent
├── screening/     # Conversational screening agent for symptom and lifestyle assessment
├── followup/      # Daily habit adherence reminder and behavioral nudging agent
└── population/    # Regional epidemiological anomaly detection agent
```

## Clinical Safety Protocol
All agents inherit the non-diagnostic safety boundary enforced by `services/ai_agent/safety.py`:
- Never diagnose disease independently.
- Never prescribe pharmaceutical medications.
- Always include the mandatory clinical safety disclaimer: *"Clinical review recommended. Not a medical diagnosis."*
- Structured Pydantic outputs only.
