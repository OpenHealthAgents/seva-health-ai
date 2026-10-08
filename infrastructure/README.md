# SevaHealth AI Infrastructure Architecture

This directory defines the production and local containerized deployment configurations for SevaHealth AI:

```
infrastructure/
├── docker/           # Multi-stage Dockerfiles for API Gateway and web services
├── postgres/         # PostgreSQL 16 init scripts, schema migrations, and JSONB index tuning
├── ehrbase/          # openEHR REST & Archetype bridge configurations (ABDM compliant)
├── redis/            # Redis 7 cache, sliding-window rate limiter, and task queue configurations
├── object-storage/   # MinIO / S3 medical document vault initialization scripts
└── monitoring/       # Prometheus metrics scraper and OpenTelemetry collector pipeline
```
