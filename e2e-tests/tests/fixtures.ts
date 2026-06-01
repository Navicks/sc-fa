import { test as base, APIRequestContext, request } from '@playwright/test';
import { createAuthedContext, TokenResponse } from './helpers/auth';

/**
 * Shared fixtures:
 *  - api:   Authenticated APIRequestContext (with Bearer token)
 *  - token: Full token set from login (used in refresh/revoke tests)
 *  - anon:  Unauthenticated APIRequestContext (for 401 tests)
 */
type Fixtures = {
  api: APIRequestContext;
  token: TokenResponse;
  anon: APIRequestContext;
};

export const test = base.extend<Fixtures>({
  api: async ({ baseURL }, use) => {
    const { ctx, token } = await createAuthedContext(baseURL!);
    // Stash token so it can be accessed from the token fixture
    (ctx as any).__token = token;
    await use(ctx);
    await ctx.dispose();
  },
  token: async ({ api }, use) => {
    await use((api as any).__token as TokenResponse);
  },
  anon: async ({ baseURL }, use) => {
    const ctx = await request.newContext({ baseURL: baseURL! });
    await use(ctx);
    await ctx.dispose();
  },
});

export const expect = test.expect;

/** Returns a unique test identifier that avoids collisions across runs. */
export function unique(prefix: string): string {
  const stamp = Date.now().toString(36);
  const rand = Math.random().toString(36).slice(2, 7);
  return `${prefix}-${stamp}-${rand}`;
}
