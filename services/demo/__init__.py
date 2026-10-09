"""SevaHealth AI Demo Mode Package.

Provides comprehensive synthetic personas and executable narrative workflows
for challenge demonstrations and clinical evaluation.
"""

from services.demo.personas import (
    SYNTHETIC_PERSONAS,
    seed_all_synthetic_personas,
    get_persona_summary_list,
)
from services.demo.story_runner import (
    execute_demo_story,
    DemoStoryResult,
    DemoStoryStage,
)
from services.demo.challenge_workflow import (
    execute_challenge_step,
    execute_all_challenge_steps,
    reset_challenge_demo,
    get_challenge_demo_state,
    ChallengeStepRecord,
    ChallengeWorkflowSummary,
)

__all__ = [
    "SYNTHETIC_PERSONAS",
    "seed_all_synthetic_personas",
    "get_persona_summary_list",
    "execute_demo_story",
    "DemoStoryResult",
    "DemoStoryStage",
    "execute_challenge_step",
    "execute_all_challenge_steps",
    "reset_challenge_demo",
    "get_challenge_demo_state",
    "ChallengeStepRecord",
    "ChallengeWorkflowSummary",
]

