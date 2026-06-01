import { test, expect } from './fixtures';
import { fetchToken, getCredentials, TokenResponse } from './helpers/auth';

test.describe('Auth /token', () => {
  test('AUTH-01 正しい資格情報でトークン取得', async ({ anon }) => {
    const { username, password } = getCredentials();
    const res = await fetchToken(anon, username, password);
    expect(res.status()).toBe(200);
    const body = (await res.json()) as TokenResponse;
    expect(body.access_token).toBeTruthy();
    expect(body.refresh_token).toBeTruthy();
    expect(body.access_token_expires).toBeTruthy();
    expect(body.refresh_token_expires).toBeTruthy();
    expect(body.token_type).toBeTruthy();
  });

  test('AUTH-02 誤ったパスワードで401', async ({ anon }) => {
    const { username } = getCredentials();
    const res = await fetchToken(anon, username, 'definitely-wrong-password');
    expect(res.status()).toBe(401);
  });

  test('AUTH-03 username欠如で422', async ({ anon }) => {
    const res = await anon.post('/token', {
      form: { grant_type: 'password', password: 'x' },
    });
    expect(res.status()).toBe(422);
  });

  test('AUTH-04 password欠如で422', async ({ anon }) => {
    const res = await anon.post('/token', {
      form: { grant_type: 'password', username: 'x@example.com' },
    });
    expect(res.status()).toBe(422);
  });
});

test.describe('Auth /token/refresh, /token/revoke', () => {
  test('AUTH-05 refreshで新トークン取得', async ({ token, anon }) => {
    const res = await anon.get('/token/refresh', {
      headers: { Authorization: `Bearer ${token.refresh_token}` },
    });
    expect(res.status()).toBe(200);
    const body = (await res.json()) as TokenResponse;
    expect(body.access_token).toBeTruthy();
  });

  test('AUTH-06 無効なrefresh_tokenで401', async ({ anon }) => {
    const res = await anon.get('/token/refresh', {
      headers: { Authorization: 'Bearer invalid.refresh.token' },
    });
    expect(res.status()).toBe(401);
  });

  test('AUTH-07/09 revokeで204、失効後は401', async ({ anon }) => {
    // Obtain a dedicated token for this test to avoid revoking the shared api context
    const { username, password } = getCredentials();
    const loginRes = await fetchToken(anon, username, password);
    const tok = (await loginRes.json()) as TokenResponse;
    const auth = { Authorization: `Bearer ${tok.access_token}` };

    const revokeRes = await anon.get('/token/revoke', { headers: auth });
    expect(revokeRes.status()).toBe(204);

    // AUTH-09: using a revoked token on a protected endpoint should return 401 (expects immediate invalidation)
    const meRes = await anon.get('/users/me/', { headers: auth });
    expect(meRes.status()).toBe(401);
  });

  test('AUTH-08 無効トークンでrevokeは401', async ({ anon }) => {
    const res = await anon.get('/token/revoke', {
      headers: { Authorization: 'Bearer invalid.access.token' },
    });
    expect(res.status()).toBe(401);
  });
});

test.describe('共通: 認証なしアクセス', () => {
  test('C-AUTH-01 トークン無しで /users/me/ は401', async ({ anon }) => {
    const res = await anon.get('/users/me/');
    expect(res.status()).toBe(401);
  });

  test('C-AUTH-02 不正トークンで /users/me/ は401', async ({ anon }) => {
    const res = await anon.get('/users/me/', {
      headers: { Authorization: 'Bearer garbage' },
    });
    expect(res.status()).toBe(401);
  });
});
