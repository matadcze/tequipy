# ADR-0002: JWT-Based Authentication

## Status

Deprecated (January 2026)

> **Note**: This ADR is deprecated. The authentication layer was removed as part of the refactoring to a minimal API-only backend. Kept for historical reference.

## Context

We need an authentication mechanism for the Tequipy platform that:

- Works with a stateless backend architecture
- Supports horizontal scaling without sticky sessions
- Provides secure token-based authentication
- Handles token expiration and refresh securely
- Can be used by both web frontend and future mobile/API clients

## Decision

We implement **JWT (JSON Web Token) authentication** with access and refresh token rotation.

### Token Strategy

| Token Type    | Purpose                 | Expiration | Storage                         |
| ------------- | ----------------------- | ---------- | ------------------------------- |
| Access Token  | API authentication      | 15 minutes | Frontend localStorage           |
| Refresh Token | Obtain new access token | 7 days     | Frontend localStorage + DB hash |

### Implementation Details

1. **Token Generation**
   - Algorithm: HS256 (HMAC-SHA256)
   - Secret: Environment variable `JWT_SECRET_KEY`
   - Claims: `sub` (user ID), `type` (access/refresh), `exp`, `iat`

2. **Refresh Token Security**
   - SHA-256 hash stored in database (not the token itself)
   - Token rotation on each refresh (old token revoked, new issued)
   - All tokens revoked on password change

3. **Token Validation**
   - Signature verification
   - Expiration check
   - Token type verification
   - For refresh: database lookup to check revocation

### Authentication Flow

```
1. User logs in with email/password
2. Server validates credentials
3. Server issues access_token + refresh_token
4. Server stores refresh_token hash in DB
5. Frontend stores both tokens in localStorage
6. Frontend sends access_token in Authorization header
7. When access_token expires, frontend uses refresh_token
8. Server validates refresh_token, revokes it, issues new pair
```

## Consequences

### Positive

- **Stateless**: No server-side session storage needed for access tokens
- **Scalable**: Any backend instance can validate access tokens
- **Secure refresh**: Token rotation limits impact of leaked refresh tokens
- **Flexibility**: Works with any client (web, mobile, CLI)
- **Revocation**: Can revoke all sessions on password change

### Negative

- **Token exposure**: JWTs in localStorage vulnerable to XSS
- **Cannot revoke access tokens**: Valid until expiration (mitigated by short lifetime)
- **Token size**: JWTs larger than simple session IDs
- **Complexity**: Refresh flow requires careful implementation

### Neutral

- Requires database lookup for refresh token validation
- Frontend must implement token refresh logic

## Alternatives Considered

### Alternative 1: Session-Based Authentication

Server-side sessions with session ID in HTTP-only cookie.

**Rejected because**:

- Requires shared session store (Redis) for horizontal scaling
- Less suitable for non-browser clients
- Sticky sessions or session replication needed

### Alternative 2: JWT in HTTP-Only Cookie

Store JWT in HTTP-only cookie instead of localStorage.

**Considered but deferred**:

- Better XSS protection
- Requires CSRF protection
- Complicates non-browser clients
- Can be added later if XSS becomes a concern

### Alternative 3: OAuth 2.0 / OIDC

Full OAuth 2.0 implementation with external identity providers.

**Rejected because**:

- Overkill for initial requirements
- Adds significant complexity
- Can be added later for social login features

### Alternative 4: Opaque Tokens

Random tokens with server-side lookup.

**Rejected because**:

- Requires database lookup on every request
- Doesn't leverage JWT ecosystem tooling

## Security Considerations

1. **Short access token lifetime** (15 minutes) limits exposure window
2. **Token rotation** invalidates old refresh tokens
3. **Password change revokes all tokens** for account security
4. **Rate limiting** on login endpoint prevents brute force
5. **Account lockout** after failed attempts

## References

- [RFC 7519 - JSON Web Token](https://tools.ietf.org/html/rfc7519)
- [OWASP JWT Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html)
- [Auth0 Token Best Practices](https://auth0.com/docs/secure/tokens/token-best-practices)
- ADR-0001: Layered Architecture (dependency injection for auth service)
