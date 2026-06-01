# fa API E2E Test Specification

- Target: `fa API` v0.1.10
- Base URL: `https://fa-api.nkn.tw`
- Swagger: `https://fa-api.nkn.tw/int/docs`
- OpenAPI: `https://fa-api.nkn.tw/openapi.json`
- Authentication: OAuth2 password flow (`POST /token` to obtain access token → `Authorization: Bearer <token>`)
- Created: 2026-06-01

This specification was derived from the OpenAPI spec. Behaviors marked "TBD" were confirmed against the live server during test execution.

---

## 0. Legend & Assumptions

- **Priority**: P1=Required (critical paths, must not regress) / P2=Important / P3=Nice to have
- **Type**: Normal / Error (validation, permission, not-found)
- Test user: `knamiki@groove.ne.jp` (some tests require admin; `is_admin` is verified at runtime via `GET /users/me/`)
- Destructive operations (create/update/delete) follow the pattern: **create test data → verify → always clean up**, to avoid polluting production data.
- All secure endpoints share the common case "401 without/invalid token" (common case C-AUTH).

### Common Cases

| ID | Target | Condition | Expected | Priority |
|----|--------|-----------|----------|----------|
| C-AUTH-01 | All secure EPs | No `Authorization` header | 401 | P1 |
| C-AUTH-02 | All secure EPs | Invalid or expired token | 401 | P1 |
| C-VALID-01 | EPs with integer `{id}` path param | Non-integer `id` (e.g. `abc`) | 422 | P2 |

---

## 1. Auth

| ID | Endpoint | Type | Precondition / Input | Expected | Priority |
|----|----------|------|----------------------|----------|----------|
| AUTH-01 | `POST /token` | Normal | Valid username/password, `grant_type=password` | 200. Contains `access_token` / `refresh_token` / `*_expires` / `token_type` | P1 |
| AUTH-02 | `POST /token` | Error | Wrong password | 401 | P1 |
| AUTH-03 | `POST /token` | Error | Missing `username` | 422 | P2 |
| AUTH-04 | `POST /token` | Error | Missing `password` | 422 | P2 |
| AUTH-05 | `GET /token/refresh` | Normal | Valid refresh_token as Bearer | 200. New full token set | P1 |
| AUTH-06 | `GET /token/refresh` | Error | Invalid or expired refresh_token | 401 | P2 |
| AUTH-07 | `GET /token/revoke` | Normal | Valid access token | 204 | P2 |
| AUTH-08 | `GET /token/revoke` | Error | Invalid token | 401 | P2 |
| AUTH-09 | Post-revoke reuse | Error | Call protected API with revoked token | 401 (immediate invalidation expected) | P2 |

---

## 2. Sites

`SiteCreate`: `fqdn` (required, string), `name` (required, ≤255)

| ID | Endpoint | Type | Precondition / Input | Expected | Priority |
|----|----------|------|----------------------|----------|----------|
| SITE-01 | `POST /sites/` | Normal | Unique fqdn + name | 201. Returns `id`/`fqdn`/`name` | P1 |
| SITE-02 | `POST /sites/` | Error | Missing `fqdn` | 422 | P2 |
| SITE-03 | `POST /sites/` | Error | `name` ≥ 256 characters | 422 | P3 |
| SITE-04 | `GET /sites/{site_id}/` | Normal | Existing site_id | 200. Matches created data | P1 |
| SITE-05 | `GET /sites/{site_id}/` | Error | Non-existent site_id | 404 | P1 |
| SITE-06 | `GET /sites/fqdn/{fqdn}/` | Normal | Existing fqdn | 200. Same site | P2 |
| SITE-07 | `GET /sites/fqdn/{fqdn}/` | Error | Non-existent fqdn | 404 | P2 |
| SITE-08 | `PATCH /sites/{site_id}/` | Normal | Change `name` | 200. Updated name | P1 |
| SITE-09 | `PATCH /sites/{site_id}/` | Normal | Change `fqdn` | 200. Updated fqdn | P2 |
| SITE-10 | `PATCH /sites/{site_id}/` | Error | Non-existent site_id | 404 | P2 |
| SITE-11 | `DELETE /sites/{site_id}/` | Error | Site has user_site associations | 409 | P1 |
| SITE-12 | `DELETE /sites/{site_id}/` | Error | Site has token associations | 409 | P1 |
| SITE-13 | `DELETE /sites/{site_id}/` | Normal | Site with no dependencies | 204. Subsequent GET returns 404 | P1 |
| SITE-14 | `DELETE /sites/{site_id}/` | Error | Non-existent site_id | 404 | P2 |

---

## 3. Tokens (site-scoped)

`TokenCreate`: `token` (required, `^[0-9A-Za-z_-]{1,255}$`), `redirect_uri` (optional, URI), `subject` (optional), `status_code` (301/302/303/308, default 302), `valid_from`/`valid_to` (optional, datetime)

| ID | Endpoint | Type | Precondition / Input | Expected | Priority |
|----|----------|------|----------------------|----------|----------|
| TOK-01 | `POST /sites/{site_id}/tokens/` | Normal | Valid token string | 201. Returns `id`/`site_id`/`token` | P1 |
| TOK-02 | `POST /sites/{site_id}/tokens/` | Normal | redirect_uri + status_code=301 | 201. Values reflected | P2 |
| TOK-03 | `POST /sites/{site_id}/tokens/` | Error | Invalid token characters (e.g. space) | 422 | P2 |
| TOK-04 | `POST /sites/{site_id}/tokens/` | Error | Malformed redirect_uri | 422 | P3 |
| TOK-05 | `POST /sites/{site_id}/tokens/` | Error | Non-existent site_id | 404 | P2 |
| TOK-06 | `GET /sites/{site_id}/tokens/` | Normal | At least 2 tokens created | 200. Array returned | P1 |
| TOK-07 | `GET /sites/{site_id}/tokens/` | Normal | `l=1&o=0` / `o=1` | Pagination works (count and offset respected) | P2 |
| TOK-08 | `GET /sites/{site_id}/tokens/` | Error | `l=0` or `l>1000` | 422 (constraint 0<l≤1000) | P3 |
| TOK-09 | `GET /sites/{site_id}/tokens/` | Error | Non-existent site_id | 404 | P2 |
| TOK-10 | `GET /sites/{site_id}/tokens/{token}/` | Normal | Fetch by token string | 200. Match | P1 |
| TOK-11 | `GET /sites/{site_id}/tokens/{token}/` | Error | Non-existent token | 404 | P2 |
| TOK-12 | `GET /sites/{site_id}/tokens/id/{token_id}/` | Normal | Fetch by token_id | 200. Match | P1 |
| TOK-13 | `GET /sites/{site_id}/tokens/id/{token_id}/` | Error | Non-existent token_id | 404 | P2 |
| TOK-14 | `PATCH /sites/{site_id}/tokens/id/{token_id}/` | Normal | Change `subject` | 200. Updated | P1 |
| TOK-15 | `PATCH /sites/{site_id}/tokens/id/{token_id}/` | Error | Non-existent token_id | 404 | P2 |
| TOK-16 | `PATCH /sites/{site_id}/tokens/id/{token_id}/` | Error | Disallowed status_code (e.g. 400) | 422 | P3 |
| TOK-17 | `DELETE /sites/{site_id}/tokens/id/{token_id}/` | Normal | Existing token_id | 204. Subsequent GET returns 404 | P1 |
| TOK-18 | `DELETE /sites/{site_id}/tokens/id/{token_id}/` | Error | Non-existent token_id | 404 | P2 |

---

## 4. Users

`UserCreate`: `email` (required, email), `display_name` (required, ≤255), `password` (required), `disabled` (default false), `is_admin` (default false). Create, read others, and delete are **admin-only**.

| ID | Endpoint | Type | Precondition / Input | Expected | Priority |
|----|----------|------|----------------------|----------|----------|
| USR-01 | `GET /users/me/` | Normal | Authenticated | 200. Own info (used to verify `is_admin`) | P1 |
| USR-02 | `PATCH /users/me/` | Normal | Change `display_name` then restore | 200. Updated | P2 |
| USR-03 | `POST /users/` | Normal (admin) | New user with unique email | 201. Deleted in teardown | P1 |
| USR-04 | `POST /users/` | Error | Called by non-admin | 403 | P2 |
| USR-05 | `POST /users/` | Error | Malformed email | 422 | P2 |
| USR-06 | `GET /users/{user_id}/` | Normal (admin) | Existing user_id | 200 | P1 |
| USR-07 | `GET /users/{user_id}/` | Error | Non-existent user_id | 404 | P2 |
| USR-08 | `GET /users/{user_id}/` | Error | Non-admin accessing another user | 403 | P2 |
| USR-09 | `GET /users/email/{email}/` | Normal (admin) | Existing email | 200 | P2 |
| USR-10 | `GET /users/email/{email}/` | Error | Non-existent email | 404 | P2 |
| USR-11 | `PATCH /users/{user_id}/` | Normal (admin) | Change display_name | 200 | P2 |
| USR-12 | `PATCH /users/{user_id}/` | Error | Non-existent user_id | 404 | P3 |
| USR-13 | `DELETE /users/{user_id}/` | Normal (admin) | Test-created user | 204 | P1 |
| USR-14 | `DELETE /users/{user_id}/` | Error | Delete self | 400 | P1 |
| USR-15 | `DELETE /users/{user_id}/` | Error | Non-existent user_id | 404 | P3 |

---

## 5. User-Sites (user–site permission bindings)

`SitePermission`: 1/2/3. `UserSiteCreateWithoutUser`: `site_id` (required), `permission` (default 1). Assign and read are admin-only.

| ID | Endpoint | Type | Precondition / Input | Expected | Priority |
|----|----------|------|----------------------|----------|----------|
| US-01 | `POST /users/{user_id}/sites/` | Normal (admin) | Test user + test site | 201. Returns `user_id`/`site_id`/`permission` | P1 |
| US-02 | `POST /users/{user_id}/sites/` | Error | Duplicate assignment for same site | 409 | P2 |
| US-03 | `POST /users/{user_id}/sites/` | Error | Non-existent user_id or site_id | 404 | P2 |
| US-04 | `POST /users/{user_id}/sites/` | Error | Called by non-admin | 403 | P2 |
| US-05 | `GET /users/{user_id}/sites/` | Normal (admin) | After assignment | 200. Array contains the entry | P1 |
| US-06 | `GET /users/{user_id}/sites/` | Normal | Pagination with `l`/`o` | Count and offset respected | P3 |
| US-07 | `GET /users/me/sites/` | Normal | Authenticated | 200. Array | P1 |
| US-08 | `PATCH /users/{user_id}/sites/{site_id}/` | Normal (admin) | Change permission 1→2 | 200. Updated | P2 |
| US-09 | `PATCH /users/{user_id}/sites/{site_id}/` | Error | Non-existent combination | 404 | P3 |

---

## 6. Teardown Policy

Resources created during tests are deleted in reverse dependency order.

1. Delete tokens (`DELETE /sites/{site_id}/tokens/id/{token_id}/`)
2. Delete test users (`DELETE /users/{user_id}/`) → cascades user_site records in the DB
3. Delete sites (`DELETE /sites/{site_id}/`) → succeeds (204) once user_site and token dependencies are gone

Each spec tracks created IDs in `createdSiteIds` / `createdTokenIds` / `createdUserIds` in `afterAll`, ignoring errors with `.catch(() => {})` so subsequent cleanup continues.

Tests that verify 409 on deletion (SITE-11/12) perform inline cleanup via `try/finally` — the site is not registered in `createdSiteIds`.

---

## 7. Findings from Initial Test Run (2026-06-01)

The initial run (54 cases total) and the diagnostic script (`scripts/diagnose.mjs`) detected the following API bugs and spec discrepancies.

### A. API Bugs (detected and fixed)

| ID | Description | Expected | Actual | Status |
|----|-------------|----------|--------|--------|
| USR-02 | `PATCH /users/me/` returned 500 even for valid input. Root cause: `current_user` deserialized from Redis cache was a transient object outside the SQLAlchemy session, causing `session.refresh()` to throw. | 200 | 500 | **Fixed.** Re-fetch via `session.get(User, current_user.id)` before mutating. `test.fail()` removed. |
| US-03 | Assigning a non-existent `site_id` triggered the duplicate-check before the site-existence check, returning 409 instead of 404. Root cause: `IntegrityError` did not distinguish FK violations from PK duplicates. | 404 | 409 | **Fixed.** Added `session.get(Site, site_id)` check before `session.flush()`. `test.fail()` removed. |

### B. OpenAPI / Implementation Discrepancies (fixed)

| ID | Description | OpenAPI | Actual | Resolution |
|----|-------------|---------|--------|------------|
| TOK-09 | Token list for a non-existent site. Implementation skipped site existence check and returned an empty array with 200. | 404 | 200 `[]` | **Fixed.** Added site existence check via `select(func.count())` returning 404. Test updated to expect 404. |

### C. Test Design Fixes

| ID | Description |
|----|-------------|
| US-05 / US-08 | Passed in isolation but failed in the suite because US-03 (which returned 409 due to the bug) left the shared user in a dirty state. Fixed by isolating US-03 to a dedicated user. |

> All API bugs and spec discrepancies detected in the initial run have been resolved.
