# fa API E2E Tests

End-to-end tests for the `fa API` (FastAPI-based REST API), automated with Playwright (TypeScript / API testing).

## Directory Structure

```
.
├── docs/
│   ├── test-spec.en.md     # Test specification — full case list per endpoint (English)
│   └── test-spec.ja.md     # Test specification (Japanese)
├── tests/
│   ├── helpers/auth.ts     # Authentication helper (token acquisition)
│   ├── fixtures.ts         # Shared fixtures (authenticated / anonymous contexts)
│   ├── auth.spec.ts        # /token, /token/refresh, /token/revoke, common 401 cases
│   ├── sites.spec.ts       # Sites CRUD
│   ├── tokens.spec.ts      # Tokens CRUD (site-scoped)
│   ├── users.spec.ts       # Users (admin-only operations, permissions, self-delete guard)
│   └── user-sites.spec.ts  # User–site permission bindings
├── global-setup.ts         # Prompts for FA_PASSWORD if not set
├── playwright.config.ts
├── package.json
├── tsconfig.json
└── .env.example
```

## Setup

Requires Node.js 18 or later.

```bash
npm install
npx playwright install        # Browsers not needed, but recommended on first run
cp .env.example .env          # Windows: copy .env.example .env
```

Edit `.env` with your credentials:

```
BASE_URL=https://fa-api.nkn.tw
FA_USERNAME=your@email.com
FA_PASSWORD=your-password
```

> Keep `.env` out of version control (already in `.gitignore`). In CI, pass credentials as environment variables or secrets. If `FA_PASSWORD` is omitted, you will be prompted at test startup.

### Local debug setup

To run tests against a locally running server (e.g. launched via the VSCode debugger):

1. Copy `.env.example` to `.env.local` and set `BASE_URL=http://localhost:8000`.
2. Start the FastAPI server via the **"Python Debugger: FastAPI - API"** VSCode launch config.
3. Run tests via the **"Playwright: E2E (localhost:8000)"** launch config, or use the **"FastAPI + E2E (Test)"** compound launch to start both together.

## Running Tests

```bash
npm test                                   # Run all tests
npx playwright test tests/auth.spec.ts     # Single file
npx playwright test -g "AUTH-01"           # Filter by test name
npm run report                             # Open the latest HTML report
```

Type-check only:

```bash
npm run typecheck
```

## Design Notes

- **Authentication**: `fixtures.ts` provides an `api` fixture — an `APIRequestContext` with `Authorization: Bearer` set after obtaining a token via `POST /token` (OAuth2 password grant). An unauthenticated `anon` fixture is also provided for 401 tests.
- **Permission tests**: Admin status is checked at runtime via `GET /users/me/`. Admin-only cases are automatically skipped for non-admin users. A temporary non-admin user is created within the test to verify 403 responses.
- **Teardown**: Tokens, users, and sites created during tests are deleted in `afterAll` in reverse dependency order (tokens → users → sites). Tests that verify 409 on deletion (e.g. SITE-11/12) perform inline cleanup via `try/finally`.
- **Serial execution**: `workers: 1` by default to avoid data races. Can be parallelised once the suite is stable.

## Notes

- The test specification was derived from the OpenAPI spec. If a live response differs, the actual behavior is treated as correct and the test is updated accordingly.
- `AUTH-09` (immediate token invalidation after revoke) assumes instant invalidation; adjust the case if the API uses delayed expiry.
- Tests include destructive operations. Running against a **test environment rather than production** is strongly recommended.
