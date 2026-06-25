# Tests — Cross-service integration & load

Service-local tests live next to their code (`backend/tests/`,
`frontend/tests/`, `analysis-engine/tests/`). This folder is reserved for
**system-level** tests that exercise multiple services together.

```
tests/
├── integration/
│   ├── conftest.py                # docker-compose spinup via pytest-docker
│   ├── test_full_pipeline.py      # POST repo → poll → assert graph + metrics
│   ├── test_ai_chat_flow.py       # Embed → query → assert citation accuracy
│   └── test_failure_recovery.py   # Kill worker mid-job → assert retry
├── load/
│   ├── locustfile.py              # Locust scenarios (5k file repos, 50 concurrent users)
│   └── README.md
└── README.md
```
