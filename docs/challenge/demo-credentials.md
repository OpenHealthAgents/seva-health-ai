# SevaHealth AI — Demonstration Access Points & Credentials

> **Mode**: Evaluation Demo Mode (Pre-Authenticated & Pre-Seeded)  
> **Host**: `http://localhost:8000` (or `http://localhost:80` when running under production reverse proxy)

---

## 1. Application Web Portals & Evaluation Entry Points

| User Persona / Role | Web Portal URL | Primary Demonstration Purpose |
|:---|:---|:---|
| **Citizen Mobile App** | [http://localhost:8000/citizen-app](http://localhost:8000/citizen-app) | Visual 4 vital questions, trajectory curves, bite-sized daily habits & vernacular audio. |
| **Health Worker Portal** | [http://localhost:8000/health-worker-app](http://localhost:8000/health-worker-app) | Rapid community screening (<3m), offline queue, and overdue follow-up rosters. |
| **Clinician Copilot** | [http://localhost:8000/clinician-app](http://localhost:8000/clinician-app) | Triage queue, automated SOAP notes, care plan approval with digital stamp. |
| **Public Health Dashboard** | [http://localhost:8000/public-health-app](http://localhost:8000/public-health-app) | District geospatial hotspot mapping, demographic clusters, and economic ROI. |
| **Telemetry & Observability** | [http://localhost:8000/observability](http://localhost:8000/observability) | Live system metrics, request tracing, AI token usage, and zero-PHI audit logs. |
| **Interactive API Documentation**| [http://localhost:8000/docs](http://localhost:8000/docs) | Swagger UI for executing REST endpoints, FHIR queries, and model inference. |

---

## 2. Pre-Seeded Evaluation Accounts & Credentials

In Demo Mode, all evaluation accounts use the standard test password: `password123`.

| Email Address | Password | Role | Assigned Health Jurisdiction |
|:---|:---|:---|:---|
| `citizen@sevahealth.ai` | `password123` | `CITIZEN` | Personal health record (Ramesh Patel / Devendra Sharma) |
| `worker@sevahealth.ai` | `password123` | `HEALTH_WORKER` | Nanjangud Taluk Sub-Centre 4, Mysuru District |
| `doctor@sevahealth.ai` | `password123` | `CLINICIAN` | Primary Health Centre, Nanjangud Hospital |
| `admin@sevahealth.ai` | `password123` | `PUBLIC_HEALTH_OFFICER` | District Health Office, Mysuru, Karnataka |

---

## 3. Pre-Authenticated Testing & Token Generation

If calling API endpoints directly via `curl` or Postman:

```bash
# Obtain Bearer JWT token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"email": "doctor@sevahealth.ai", "password": "password123"}'
```

*Response*:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "role": "CLINICIAN",
  "expires_in_minutes": 60
}
```
