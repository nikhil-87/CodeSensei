# Risks & Limitations

> **Status:** Outline (filled in Phase 9). Selected entries below already firm.

## Known limitations (v1)

| # | Limitation                                                     | Mitigation                                              |
|---|----------------------------------------------------------------|---------------------------------------------------------|
| 1 | Public repos only                                              | Documented; v2 adds OAuth + private repo support        |
| 2 | Max 5,000 files per repo                                       | Enforced via `API_MAX_REPO_FILES`; configurable         |
| 3 | No authentication built-in                                     | Front with oauth2-proxy / Tailscale (see IAM doc)       |
| 4 | LLM quality bounded by the selected model (free-tier default: Groq Llama 3.3 70B; local default: DeepSeek-Coder 6.7B) | Switch `LLM_PROVIDER` / model via config; opt into larger models |
| 5 | Tree-sitter does not do type resolution                        | Symbol references use lexical matching; documented      |
| 6 | Single Redis = single point of failure for the queue           | Operators use managed Redis with replicas in prod       |
| 7 | ChromaDB embedded mode does not cluster                        | Migration path to pgvector or Qdrant documented (ADR-0005) |

## Planned sections

1. Risk register with likelihood × impact scoring
2. Performance limits with measured numbers
3. Security limitations (what we explicitly don't defend against)
4. Operational limitations (no live multi-tenancy, no per-repo quotas)
5. Roadmap items that retire each limitation
