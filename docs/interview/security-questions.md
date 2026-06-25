# Security Interview Questions & Answers

### "How do you authenticate users?"
GitHub OAuth 2.0 Authorization-Code flow. On callback I verify an anti-CSRF state cookie,
exchange the code for a token, fetch the profile, upsert the user, and mint an HS256 JWT
stored in an **httpOnly** cookie. The JWT is stateless (`sub`, `gh`, `iat`, `exp`), so API
replicas need no shared session store. Dev has a mock-auth mode that's hard-disabled in
production.

### "Why a cookie instead of a bearer token in localStorage?"
An httpOnly cookie isn't readable by JavaScript, so an XSS bug can't exfiltrate the session.
I pair it with `SameSite=Lax` (CSRF mitigation) and `secure` in production. A bearer token in
localStorage is XSS-exfiltratable.

### "How do you prevent IDOR / broken access control?"
Identity always comes from the verified cookie, never from request params/bodies. "My" lists
filter by that identity. Owned mutations check ownership in the service. Reads go through
`verify_repository_access` (owner or `is_public`). Non-permitted access returns `404`, not
`403`, so I don't even leak that a resource exists.

### "You clone arbitrary GitHub URLs — how do you prevent SSRF?"
`validate_github_url` accepts only canonical HTTPS GitHub URLs and rejects SSH, custom ports,
userinfo, query strings, and non-GitHub hosts before any network call. Branch names are
validated against path tricks, and clones use slugged, `safe_join`-ed workspace paths to
prevent traversal.

### "How do you prevent XSS?"
React escapes by default; I don't use `dangerouslySetInnerHTML` for user/repo content. The
session token isn't in JS. Derived artifacts (Mermaid diagrams, markdown) come from controlled
backend output, not raw user HTML.

### "Rate limiting / DoS?"
A sliding-window per-IP middleware (`API_RATE_LIMIT_PER_MINUTE`) returns `429` with
`Retry-After`, exempting health endpoints and honoring `X-Forwarded-For` behind the proxy.
Repo size/file caps bound analysis cost. **Honest gap:** the limiter is in-memory per process,
so behind multiple replicas it's per-replica — production should move it to Redis.

### "How do you isolate users / handle multi-tenancy?"
Repos, chat sessions, and stars are scoped by the authenticated user; sessions are private and
ownership is re-checked on every session route. Each repo's embeddings live in its own Chroma
collection, which is dropped on repository delete so embedded code doesn't linger.

### "What about prompt injection in the AI chat?"
Repository content is untrusted and could contain adversarial instructions. Mitigations: a
constrained system prompt, a strictly **read-only** surface (the model can't take actions),
and informational output only. I treat it as mitigated, not eliminated — it's inherent to LLMs
over untrusted text, and I'd add output filtering / stronger prompt isolation before a real
launch.

### "How are secrets managed?"
Only via environment variables (`APP_SECRET_KEY`, OAuth secret, `GROQ_API_KEY`,
`HUGGINGFACE_API_KEY`, DB/Redis passwords), never committed. Production guards refuse to boot
with the default secret key or DB password and force secure cookies.

### "Public vs. private repository access?"
A repo is readable by its owner always, and by anyone only if `is_public`. Discover and
profiles surface only public repos. Visibility is owner-controlled via a dedicated endpoint.
