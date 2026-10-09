#!/usr/bin/env python3
"""SevaHealth AI: Complete Interactive Demo Mode CLI.

Executes the complete 9-stage narrative in under 5 minutes:
1. Citizen starts with Moderate Risk.
2. Silent Progression: Weight ↑, Activity ↓, BP ↑, HbA1c ↑.
3. SevaHealth Trajectory Engine detects worsening trajectory (+35% velocity).
4. AI explains contributors (explainable waterfall, non-causal language).
5. AI creates personalized 30-day multi-pillar lifestyle intervention.
6. Citizen completes intervention (adherence logged, wearable steps up).
7. Risk improves & trajectory reverses to IMPROVING (-47% delta).
8. Clinician reviews triage SOAP note and approves with digital stamp.
9. Population health dashboard reflects verified outcome delta.

Usage:
    python scripts/run_demo.py
    python scripts/run_demo.py --auto
    python scripts/run_demo.py --interactive
"""

import sys
import io
import time
from pathlib import Path

# Windows console encoding safeguard
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Ensure sevahealth-ai root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.seed_data import seed_all_demo_data
from services.demo.personas import get_persona_summary_list
from services.demo.story_runner import execute_demo_story, DemoStoryResult


# Terminal ANSI Colors
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    RESET = "\033[0m"


def print_banner():
    banner = f"""
{Colors.CYAN}{Colors.BOLD}================================================================================
   ____                  _   _            _ _   _         _    ___ 
  / ___|  _____   ____ _| | | | ___  __ _| | |_| |__     / \\  |_ _|
  \\___ \\ / _ \\ \\ / / _` | |_| |/ _ \\/ _` | | __| '_ \\   / _ \\  | | 
   ___) |  __/\\ V / (_| |  _  |  __/ (_| | | |_| | | | / ___ \\ | | 
  |____/ \\___| \\_/ \\__,_|_| |_|\\___|\\__,_|_|\\__|_| |_|/_/   \\_\\___|
{Colors.RESET}
  {Colors.BOLD}AI-Powered Early Detection & Prevention of Non-Communicable Diseases{Colors.RESET}
  {Colors.GREEN}"Detect risk early. Prevent disease. Bring personalized healthcare to every community."{Colors.RESET}
================================================================================
"""
    print(banner)


def print_personas_table(personas):
    print(f"\n{Colors.BOLD}{Colors.YELLOW}[1] SEEDING COMPLETE: 12 SYNTHETIC CLINICAL PERSONAS LOADED{Colors.RESET}")
    print("-" * 88)
    print(f"{'#':<3} {'Name':<18} {'Phenotype / Persona':<32} {'Risk Tier':<10} {'Trajectory':<12}")
    print("-" * 88)
    for idx, p in enumerate(personas, 1):
        color = Colors.GREEN if p["risk_tier"] == "LOW" else (Colors.YELLOW if p["risk_tier"] == "MODERATE" else Colors.RED)
        print(f"{idx:<3} {p['name']:<18} {p['persona_type']:<32} {color}{p['risk_tier']:<10}{Colors.RESET} {p['trajectory_trend']:<12}")
    print("-" * 88)


def render_ascii_trajectory_graph(base: float, worsened: float, improved: float):
    print(f"\n{Colors.BOLD}{Colors.CYAN}--- NCD RISK TRAJECTORY EVOLUTION ---{Colors.RESET}")
    print("Risk %")
    print(f" 80 |              [*] Stage 3 ({int(worsened*100)}% HIGH - DETECTED)")
    print(" 70 |             / \\")
    print(" 60 |            /   \\")
    print(" 50 |           /     \\")
    print(f" 40 |  [*] Stage 1 ({int(base*100)}% MOD)   \\")
    print(f" 30 |                       \\")
    print(f" 20 |                        [*] Stage 7 ({int(improved*100)}% LOW - REVERSED)")
    print(" 10 |")
    print("  0 +---------------------------------------------------> Time")
    print("       Month 0          Month 6           Month 7")
    print("      (Baseline)     (Silent Drift)   (Post-Intervention)")


def render_attribution_waterfall():
    print(f"\n{Colors.BOLD}{Colors.YELLOW}--- EXPLAINABLE AI RISK ATTRIBUTION WATERFALL ---{Colors.RESET}")
    factors = [
        ("Prediabetic Impaired Glycemia (HbA1c 6.3%)", 28, "[==============]"),
        ("Prehypertension Vascular Strain (142/90 mmHg)", 24, "[============]  "),
        ("Severe Physical Inactivity (3,200 steps/day)", 20, "[==========]    "),
        ("Central Visceral Adiposity (BMI 27.6, +8.5kg)", 16, "[========]      "),
    ]
    for name, wt, bar in factors:
        print(f"  {bar:<16} +{wt}% : {name}")
    print("  " + "-" * 70)
    print("  " + f"{Colors.GREEN}Non-Causal Explanation Grounded in Biomarkers (No Black Box AI){Colors.RESET}")


def run_demo(interactive: bool = False):
    print_banner()

    start_clk = time.time()
    print(f"{Colors.BLUE}Initializing SevaHealth AI Engine and Seeding Synthetic Cohort...{Colors.RESET}")
    seed_all_demo_data()

    personas = get_persona_summary_list()
    print_personas_table(personas)

    if interactive:
        input(f"\n{Colors.BOLD}Press [ENTER] to begin the Hero Journey narrative...{Colors.RESET}")

    print(f"\n{Colors.BOLD}{Colors.HEADER}================================================================================")
    print(f"   THE HERO JOURNEY: CLINICAL NARRATIVE OF ARJUN MEHTA (AGE 45)")
    print(f"================================================================================{Colors.RESET}\n")

    result: DemoStoryResult = execute_demo_story(citizen_id="citizen-arjun-mehta-11")

    for stage in result.stages:
        print(f"{Colors.CYAN}{Colors.BOLD}[Stage {stage.step_number}/9] {stage.title}{Colors.RESET}")
        print(f"{stage.narrative}")
        print(f"{Colors.YELLOW}Telemetry Snapshot:{Colors.RESET}")
        for k, v in stage.data_snapshot.items():
            if isinstance(v, list):
                print(f"  - {k}: {len(v)} items")
            elif isinstance(v, str) and "\n" in v:
                lines = v.split("\n")
                print(f"  - {k}: {lines[0]}...")
            else:
                print(f"  - {k}: {v}")

        if stage.step_number == 3:
            render_ascii_trajectory_graph(
                result.baseline_risk_score,
                result.worsened_risk_score,
                result.improved_risk_score,
            )

        if stage.step_number == 4:
            render_attribution_waterfall()

        print("-" * 80)
        if interactive:
            input(f"{Colors.BOLD}Press [ENTER] for next stage...{Colors.RESET}\n")
        else:
            time.sleep(0.1)

    total_duration = round(time.time() - start_clk, 2)

    print(f"\n{Colors.GREEN}{Colors.BOLD}================================================================================")
    print(f"   DEMO STORY SUCCESSFULLY CONCLUDED IN {total_duration}s (TARGET: < 300s)")
    print(f"================================================================================{Colors.RESET}")
    print(f"  - Hero Citizen:                  {result.citizen_name} (citizen-arjun-mehta-11)")
    print(f"  - Baseline Risk (Stage 1):       {int(result.baseline_risk_score*100)}% (MODERATE)")
    print(f"  - Deteriorated Peak (Stage 3):   {int(result.worsened_risk_score*100)}% (HIGH)")
    print(f"  - Reversal Outcome (Stage 7):    {int(result.improved_risk_score*100)}% (LOW-MODERATE)")
    print(f"  - Net Relative Risk Reduction:   {result.net_risk_reduction_percentage}%")
    print(f"  - Clinician Sign-Off:            {result.clinician_review_status} by Dr. Anand Kulkarni, MD")
    print(f"  - Population ROI Projection:     INR 42,000 / citizen / year hospitalization cost avoidance")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    is_interactive = "--interactive" in sys.argv
    run_demo(interactive=is_interactive)
