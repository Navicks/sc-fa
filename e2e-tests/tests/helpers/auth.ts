import { APIRequestContext, request } from '@playwright/test';

export interface TokenResponse {
  access_token: string;
  access_token_expires: string;
  refresh_token: string;
  refresh_token_expires: string;
  token_type: string;
}

export function getCredentials() {
  const username = process.env.FA_USERNAME;
  const password = process.env.FA_PASSWORD;
  if (!username || !password) {
    throw new Error('FA_USERNAME / FA_PASSWORD is not set. Check your .env file.');
  }
  return { username, password };
}

/**
 * Obtain a full token set via password grant.
 * Returns the raw response so callers that need to inspect failure responses can do so.
 */
export async function fetchToken(
  ctx: APIRequestContext,
  username: string,
  password: string,
) {
  return ctx.post('/token', {
    form: { grant_type: 'password', username, password },
  });
}

/** Log in and return the token set. Throws on failure. */
export async function login(ctx: APIRequestContext): Promise<TokenResponse> {
  const { username, password } = getCredentials();
  const res = await fetchToken(ctx, username, password);
  if (!res.ok()) {
    throw new Error(`Login failed: ${res.status()} ${await res.text()}`);
  }
  return (await res.json()) as TokenResponse;
}

/** Create a new APIRequestContext with a Bearer token attached. */
export async function createAuthedContext(baseURL: string): Promise<{
  ctx: APIRequestContext;
  token: TokenResponse;
}> {
  const anon = await request.newContext({ baseURL });
  const token = await login(anon);
  await anon.dispose();
  const ctx = await request.newContext({
    baseURL,
    extraHTTPHeaders: {
      Authorization: `Bearer ${token.access_token}`,
      Accept: 'application/json',
    },
  });
  return { ctx, token };
}

export function authHeader(accessToken: string) {
  return { Authorization: `Bearer ${accessToken}` };
}
