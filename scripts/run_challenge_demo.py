#!/usr/bin/env python3
"""Seva Innovation Challenge Demo Workflow CLI Runner (PROMPT 25).

Executes the official 16-step SevaHealth AI demonstration workflow:
  STEP 1:  Health worker registers citizen.
  STEP 2:  Citizen completes NCD screening.
  STEP 3:  System calculates risk.
  STEP 4:  AI explains risk.
  STEP 5:  System generates personalized prevention plan.
  STEP 6:  Citizen connects wearable.
  STEP 7:  System receives activity/sleep/heart-rate data.
  STEP 8:  Risk trajectory changes.
  STEP 9:  AI detects deterioration.
  STEP 10: High-risk alert is generated.
  STEP 11: Clinician reviews the patient.
  STEP 12: Clinician creates/approves care plan.
  STEP 13: Citizen receives intervention.
  STEP 14: Follow-up measurement is recorded.
  STEP 15: Risk trajectory improves.
  STEP 16: Population dashboard shows aggregate impact.

Usage:
  python scripts/run_challenge_demo.py              # Full automated execution (< 10s)
  python scripts/run_challenge_demo.py --reset      # Trigger Demo Reset Button
  python scripts/run_challenge_demo.py --step 5     # Run up to Step 5
  python scripts/run_challenge_demo.py --interactive# Interactive pause between steps
"""

import sys
import os
import io
import time
import argparse
from pathlib import Path

# Safe Windows stdout encoding configuration
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.demo.challenge_workflow import (
    execute_challenge_step,
    execute_all_challenge_steps,
    reset_challenge_demo,
    get_challenge_demo_state,
    CHALLENGE_CITIZEN_ID,
    ChallengeStepRecord,
    ChallengeWorkflowSummary,
)


def print_banner(text: str, ch: str = "="):
    line = ch * 84
    print(f"\n{line}\n   {text}\n{line}")


def print_step_header(step: ChallengeStepRecord):
    actor_badges = {
        "HEALTH_WORKER": "[HEALTH WORKER]",
        "CITIZEN": "[CITIZEN]",
        "SYSTEM": "[SYSTEM ENGINE]",
        "AI_ENGINE": "[EXPLAINABLE AI]",
        "CLINICIAN": "[PHYSICIAN / COPILOT]",
        "PUBLIC_HEALTH_ADMIN": "[POPULATION ADMIN]",
    }
    badge = actor_badges.get(step.actor_role, f"[{step.actor_role}]")
    print(f"\n{'='*84}")
    print(f"  STEP {step.step_number}/16 : {step.title.upper()}")
    print(f"  Actor: {badge} {step.actor_name} | Elapsed: {step.execution_time_ms:.1f}ms")
    print(f"{'-'*84}")
    print(f"  Action: {step.description}\n")


def print_telemetry_box(telemetry: dict):
    print("  Key Telemetry Snapshot:")
    for k, v in telemetry.items():
        if isinstance(v, dict):
            print(f"    * {k}:")
            for sub_k, sub_v in v.items():
                print(f"        - {sub_k}: {sub_v}")
        elif isinstance(v, list) and v and isinstance(v[0], dict):
            print(f"    * {k} ({len(v)} items):")
            for item in v[:4]:
                summary_str = " | ".join(f"{ik}: {iv}" for ik, iv in item.items() if ik != "guideline")
                print(f"        - {summary_str}")
        else:
            print(f"    * {k}: {v}")


def print_ascii_trajectory_curve():
    print("""
   --- NCD RISK TRAJECTORY EVOLUTION CURVE ---
   Risk %
    90 |
    80 |                 [*] Step 9 (79% HIGH - DETERIORATION DETECTED)
    70 |                / \\
    60 |               /   \\
    50 |   [*] Step 3 /     \\
    40 |   (52% MOD) /       \\
    30 |                      \\
    20 |                       [*] Step 15 (22% LOW - REVERSED)
    10 |
     0 +------------------------------------------------------------> Time
          Month 0 (Baseline)   Month 2 (Silent Drift)   Month 3 (Reversal)
          Devendra Sharma      Overtime & Lapse         30-Day Millet & Walk Rx
    ----------------------------------------------------------------------------
""")


def print_ascii_waterfall():
    print("""
   --- EXPLAINABLE AI RISK ATTRIBUTION WATERFALL (STEP 4) ---
     [==================] +22% : Impaired Fasting Glycemia (FBG 112 mg/dL, HbA1c 5.9%)
     [==============    ] +18% : Prehypertension Vascular Strain (134/86 mmHg)
     [==========        ] +14% : Central Visceral Adiposity (Waist 92 cm, BMI 26.4)
     [======            ] +10% : Physical Inactivity (Sedentary lifestyle pattern)
     [<<<<<             ] -12% : Mitigating Factor: Tobacco & Alcohol Abstinence
     -------------------------------------------------------------------------
     No Black Box: Transparent attribution mapped directly to ICMR Guidelines.
""")


def print_population_impact_box():
    print("""
   =============================================================================
      POPULATION HEALTH COMMAND CENTER: DISTRICT IMPACT METRICS (STEP 16)
   =============================================================================
     District Jurisdiction:         Bengaluru Rural, Karnataka
     Screened Population:           5,420 citizens
     Enrolled High-Risk Cohort:     840 citizens
     Cohort Lifestyle Adherence:    88.4%
     Average HbA1c Reduction:       -0.65% across prediabetic cohort
     Average Systolic BP Drop:      -14.8 mmHg across hypertensive cohort
     High-to-Low Risk Migration:    64.2% transitioned to Low/Moderate within 90 days
     Annual Cost Avoidance / Citizen: INR 45,000
     Total Annualized District ROI:   INR 3.78 Crores (INR 37,800,000)
   =============================================================================
""")


def run_full_challenge_demo(interactive: bool = False, max_step: int = 16):
    print_banner("SEVAHEALTH AI - SEVA INNOVATION CHALLENGE DEMONSTRATION WORKFLOW")
    print("  Tagline: Detect risk early. Prevent disease. Bring personalized healthcare to every community.")
    print("  Insight: Don't wait for people to become patients. Identify people silently moving toward")
    print("           disease and intervene before they need expensive hospitalization.\n")
    print("  Workflow: Executing all 16 official challenge demonstration steps.")

    t_start = time.time()

    for s in range(1, max_step + 1):
        step_rec = execute_challenge_step(s)
        print_step_header(step_rec)
        print_telemetry_box(step_rec.telemetry)

        if s == 4:
            print_ascii_waterfall()
        elif s == 9:
            print_ascii_trajectory_curve()
        elif s == 16:
            print_population_impact_box()

        if interactive and s < max_step:
            input(f"\n  [Press Enter to continue to Step {s + 1} / 16] > ")

    elapsed = time.time() - t_start

    print_banner(f"CHALLENGE DEMO SUCCESSFULLY CONCLUDED IN {elapsed:.2f}s (TARGET: < 300s)")
    print(f"  - Citizen Subject:               Devendra Sharma ({CHALLENGE_CITIZEN_ID})")
    print(f"  - Baseline Risk (Step 3):        52.0% (MODERATE)")
    print(f"  - Peak Deterioration (Step 9):   79.0% (HIGH)")
    print(f"  - Normalized Outcome (Step 15):  22.0% (LOW)")
    print(f"  - Net Relative Risk Reduction:   72.2%")
    print(f"  - Clinician Review & Sign-Off:   APPROVED by Dr. Anand Kulkarni, MD")
    print(f"  - District Annual Cost Savings:  INR 3.78 Crores")
    print(f"  - Demo Reset Button Available:   Run 'python scripts/run_challenge_demo.py --reset'")
    print(f"{'='*84}\n")


def main():
    parser = argparse.ArgumentParser(description="Seva Innovation Challenge Demo Workflow Runner")
    parser.add_argument("--reset", action="store_true", help="Trigger the Demo Reset Button and exit")
    parser.add_argument("--step", type=int, default=16, help="Execute up to a specific step (1-16)")
    parser.add_argument("--interactive", action="store_true", help="Pause interactively between steps")
    args = parser.parse_args()

    if args.reset:
        print_banner("SEVAHEALTH DEMO RESET BUTTON TRIGGERED")
        res = reset_challenge_demo()
        print(f"  Status:  {res['status']}")
        print(f"  Message: {res['message']}")
        print(f"  Subject: {res['citizen_id']}")
        print(f"  Reset Timestamp: {res['reset_at']}")
        print("  [OK] Environment is now clean and ready for a fresh demonstration run.\n")
        return

    run_full_challenge_demo(interactive=args.interactive, max_step=args.step)


if __name__ == "__main__":
    main()
