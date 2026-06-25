# ADR-0005: GitHub OAuth + JWT cookie authentication

**Status:** Accepted

## Context
Users are developers exploring GitHub repos. We need identity (for ownership, stars,
profiles, private sessions) without managing passwords, and a session mechanism that's safe
against XSS token theft.

## Decision
Use **GitHub OAuth 2.0** (Authorization-Code) for login and a **stateless HS256 JWT** stored
in an **httpOnly cookie** (`codesensei_session`) for sessions. Provide a dev-only **mock
auth** and **dev-login** for local/CI.

## Alternatives considered
- **Email/password** — must store hashes, handle reset flows, fight credential stuffing.
- **JWT in localStorage** — readable by JS → XSS can exfiltrate the token.
- **Server-side sessions (Redis)** — stateful; the JWT-in-cookie approach is stateless and
  free-tier-friendly.
- **Auth0/Clerk** — great but an external dependency for a portfolio app.

## Consequences
- (+) No password management; stable `github_id` identity; avatar/username for profiles.
- (+) httpOnly cookie mitigates token theft via XSS; `SameSite=Lax` mitigates CSRF.
- (+) Stateless tokens → API replicas need no shared session store.
- (−) Token revocation before expiry is non-trivial (mitigated by modest TTL).
- (−) Tied to GitHub (acceptable for the audience; other providers slot into `AuthService`).
- Mock auth/dev login are **hard-disabled in production** to avoid auth bypass.
