# Performance Guide

> **Status:** Outline (filled in Phase 9 with measured numbers from Phase 6 load tests).

## Performance budgets (targets)

| Operation                                     | p50    | p99       |
| --------------------------------------------- | ------ | --------- |
| `GET /api/v1/repositories`                    | 20 ms  | 80 ms     |
| `GET /api/v1/repositories/{id}/dependencies`  | 30 ms  | 100 ms    |
| `POST /api/v1/repositories` (enqueue)         | 40 ms  | 120 ms    |
| Full analysis of 1,000-file Python repo       | 90 s   | 180 s     |
| Full analysis of 5,000-file repo              | 6 min  | 10 min    |
| AI chat first token (cache miss)              | 1.5 s  | 4 s       |
| AI chat full answer                           | 6 s    | 15 s      |

## Planned sections

1. Profiling methodology — `pyinstrument` for backend, `py-spy` for workers
2. Hot paths and their optimizations (parser cache, graph memoization, prepared statements)
3. Database tuning — indexes per query, connection pool sizing
4. Redis tuning — eviction policy, memory ceiling
5. Ollama tuning — model selection, `num_ctx`, parallel request limit
6. Frontend perf — bundle analysis, code splitting (Monaco lazy load)
7. Load test results — Locust reports
8. Capacity planning matrices — repo size × worker count
