"""Test Suite for SevaHealth Citizen Mobile Application.

Verifies:
1. Web delivery of mobile application at `/citizen-app`.
2. Clean SevaHealth Design System structure & color tokens.
3. Presence and coverage of all 17 primary screens:
   - Welcome, Registration, Consent, Health profile, Screening,
   - Health dashboard, NCD risk, Risk trajectory, Today's priorities,
   - Prevention plan, AI health assistant, Wearable connection,
   - Measurements, Check-in, Notifications, Appointments/referrals,
   - Privacy/data controls.
4. Home Screen 3 Core Questions:
   - "How am I doing?"
   - "What's changing?"
   - "What should I do today?"
5. Multi-lingual selection & low digital literacy design.
6. Citizen API integrations:
   - Profile retrieval, daily care plan habits, vitals, AI assistant, and consent management.
"""

import pytest
from starlette.testclient import TestClient
from pathlib import Path

from packages.types.enums import UserRole
from packages.auth.jwt import create_access_token
from services.api.main import app
from services.store import store
from scripts.seed_data import seed_all_demo_data

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_seed():
    seed_all_demo_data()


@pytest.fixture
def ramesh_token():
    return create_access_token(
        subject="citizen-user-01",
        tenant_id="karnataka_state_health",
        role=UserRole.CITIZEN,
    )


class TestCitizenMobileAppWebDelivery:
    """Tests 1, 2, 3: Web app hosting, design system tokens, and 17 primary screens."""

    def test_serve_citizen_app_endpoint(self):
        response = client.get("/citizen-app")
        assert response.status_code == 200
        content = response.text

        # Verify Design System & Branding
        assert "SevaHealth" in content
        assert "Sky Medical Blue" in content or "#0284c7" in content
        assert "phone-frame" in content

        # Verify the 17 Primary Screens are cataloged
        screens = [
            "1. Welcome",
            "2. Registration",
            "3. Consent",
            "4. Health Profile",
            "5. Screening",
            "6. Health Dashboard",
            "7. NCD Risk",
            "8. Risk Trajectory",
            "9. Today's Priorities",
            "10. Prevention Plan",
            "11. AI Health Assistant",
            "12. Wearables",
            "13. Measurements",
            "14. Check-in",
            "15. Notifications",
            "16. Referrals & Appointments",
            "17. Privacy & Controls",
        ]
        for screen in screens:
            assert screen in content, f"Screen '{screen}' missing from app catalog!"

    def test_home_screen_answers_the_three_vital_questions(self):
        response = client.get("/citizen-app")
        assert response.status_code == 200
        content = response.text

        # Core Question 1: How am I doing?
        assert "HOW AM I DOING?" in content
        assert "doingHeadline" in content or "Sugar needs a little care" in content

        # Core Question 2: What changed?
        assert "WHAT CHANGED?" in content or "WHAT'S CHANGING?" in content
        assert "changingText" in content or "Walking increased" in content or "question-what-changed" in content

        # Core Question 3: What should I do today?
        assert "WHAT SHOULD I DO TODAY?" in content
        assert "todayTasks" in content

    def test_multilingual_and_low_digital_literacy_support(self):
        response = client.get("/citizen-app")
        assert response.status_code == 200
        content = response.text

        # Indian vernacular languages
        assert "हिंदी" in content
        assert "ಕನ್ನಡ" in content
        assert "தமிழ்" in content

        # Voice audio read-aloud support
        assert "speakText" in content
        assert "audio-btn" in content or "Listen" in content

        # No terrifying medical jargon; simple risk metaphors
        assert "Sugar Balance" in content
        assert "Needs Care" in content or "Mild Caution" in content


class TestCitizenAPIFlows:
    """Verifies backend API connectivity supporting citizen mobile interactions."""

    def test_citizen_profile_access(self, ramesh_token):
        response = client.get(
            "/api/v1/citizens/citizen-ramesh-patel-01",
            headers={"Authorization": f"Bearer {ramesh_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Ramesh"
        assert data["last_name"] == "Patel"
        assert data["abha_id"] == "91-4829-1029-4820"

    def test_citizen_care_plan_and_today_tasks(self, ramesh_token):
        response = client.get(
            "/api/v1/intervention/plan/citizen-ramesh-patel-01",
            headers={"Authorization": f"Bearer {ramesh_token}"},
        )
        assert response.status_code == 200
        plan = response.json()
        assert "daily_tasks" in plan
        assert len(plan["daily_tasks"]) > 0

    def test_citizen_ai_assistant_dialogue(self, ramesh_token):
        payload = {
            "citizen_id": "citizen-ramesh-patel-01",
            "query": "Can I eat a mango today?",
            "language": "en",
        }
        response = client.post(
            "/api/v1/ai/prevention-agent/chat",
            headers={"Authorization": f"Bearer {ramesh_token}"},
            json=payload,
        )
        assert response.status_code == 200
        res = response.json()
        assert "answer" in res
        assert len(res["answer"]) > 10

    def test_citizen_consent_directives_retrieval(self, ramesh_token):
        response = client.get(
            "/api/v1/auth/consent/citizen-ramesh-patel-01",
            headers={"Authorization": f"Bearer {ramesh_token}"},
        )
        assert response.status_code == 200
        directives = response.json()
        assert isinstance(directives, list)

    def test_citizen_least_privilege_cannot_access_other_citizen(self, ramesh_token):
        # Ramesh cannot access Lakshmi's private record
        response = client.get(
            "/api/v1/citizens/citizen-lakshmi-devi-02",
            headers={"Authorization": f"Bearer {ramesh_token}"},
        )
        assert response.status_code == 403
