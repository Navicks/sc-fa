import { test, expect, unique } from './fixtures';
import { createAuthedContext } from './helpers/auth';
import type { APIRequestContext } from '@playwright/test';

interface SiteRead { id: number; fqdn: string; name: string; }
interface TokenRead {
  id: number; site_id: number; token: string;
  redirect_uri: string | null; subject: string | null; status_code: number;
}

test.describe('Tokens', () => {
  let api: APIRequestContext;
  let siteId: number;
  const createdTokenIds: number[] = [];

  test.beforeAll(async ({ baseURL }) => {
    const authed = await createAuthedContext(baseURL!);
    api = authed.ctx;
    const res = await api.post('/sites/', {
      data: { fqdn: `${unique('e2e-tok')}.example.com`, name: 'Token Test Site' },
    });
    expect(res.status()).toBe(201);
    siteId = ((await res.json()) as SiteRead).id;
  });

  test.afterAll(async () => {
    for (const id of createdTokenIds) {
      await api.delete(`/sites/${siteId}/tokens/id/${id}/`).catch(() => {});
    }
    // Delete site after all tokens have been removed
    if (siteId) await api.delete(`/sites/${siteId}/`).catch(() => {});
    await api.dispose();
  });

  test('TOK-01 トークン作成', async () => {
    const tokenStr = unique('tok').replace(/-/g, '_');
    const res = await api.post(`/sites/${siteId}/tokens/`, { data: { token: tokenStr } });
    expect(res.status()).toBe(201);
    const body = (await res.json()) as TokenRead;
    expect(body.id).toBeGreaterThan(0);
    expect(body.site_id).toBe(siteId);
    expect(body.token).toBe(tokenStr);
    createdTokenIds.push(body.id);
  });

  test('TOK-02 redirect_uri と status_code 指定', async () => {
    const res = await api.post(`/sites/${siteId}/tokens/`, {
      data: {
        token: unique('tok').replace(/-/g, '_'),
        redirect_uri: 'https://example.com/landing',
        status_code: 301,
      },
    });
    expect(res.status()).toBe(201);
    const body = (await res.json()) as TokenRead;
    expect(body.redirect_uri).toBe('https://example.com/landing');
    expect(body.status_code).toBe(301);
    createdTokenIds.push(body.id);
  });

  test('TOK-03 不正な token 文字で422', async () => {
    const res = await api.post(`/sites/${siteId}/tokens/`, {
      data: { token: 'has space!' },
    });
    expect(res.status()).toBe(422);
  });

  test('TOK-04 不正な redirect_uri で422', async () => {
    const res = await api.post(`/sites/${siteId}/tokens/`, {
      data: { token: unique('tok').replace(/-/g, '_'), redirect_uri: 'not a uri' },
    });
    expect(res.status()).toBe(422);
  });

  test('TOK-05 存在しない site_id で404', async () => {
    const res = await api.post('/sites/999999999/tokens/', {
      data: { token: unique('tok').replace(/-/g, '_') },
    });
    expect(res.status()).toBe(404);
  });

  test('TOK-06 一覧取得は配列', async () => {
    const res = await api.get(`/sites/${siteId}/tokens/`);
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(Array.isArray(body)).toBe(true);
    expect(body.length).toBeGreaterThanOrEqual(1);
  });

  test('TOK-07 ページング l/o', async () => {
    const res = await api.get(`/sites/${siteId}/tokens/`, { params: { l: 1, o: 0 } });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(Array.isArray(body)).toBe(true);
    expect(body.length).toBeLessThanOrEqual(1);
  });

  test('TOK-08 l=0 は422', async () => {
    const res = await api.get(`/sites/${siteId}/tokens/`, { params: { l: 0 } });
    expect(res.status()).toBe(422);
  });

  test('TOK-09 存在しない site_id で404', async () => {
    const res = await api.get('/sites/999999999/tokens/');
    expect(res.status()).toBe(404);
  });

  test('TOK-10/11 token文字列で取得', async () => {
    const tokenStr = unique('tok').replace(/-/g, '_');
    const created = await api.post(`/sites/${siteId}/tokens/`, { data: { token: tokenStr } });
    const id = ((await created.json()) as TokenRead).id;
    createdTokenIds.push(id);

    const ok = await api.get(`/sites/${siteId}/tokens/${tokenStr}/`);
    expect(ok.status()).toBe(200);
    expect(((await ok.json()) as TokenRead).token).toBe(tokenStr);

    const notFound = await api.get(`/sites/${siteId}/tokens/no_such_token_xyz/`);
    expect(notFound.status()).toBe(404);
  });

  test('TOK-12/13 token_idで取得', async () => {
    const created = await api.post(`/sites/${siteId}/tokens/`, {
      data: { token: unique('tok').replace(/-/g, '_') },
    });
    const id = ((await created.json()) as TokenRead).id;
    createdTokenIds.push(id);

    const ok = await api.get(`/sites/${siteId}/tokens/id/${id}/`);
    expect(ok.status()).toBe(200);
    expect(((await ok.json()) as TokenRead).id).toBe(id);

    const notFound = await api.get(`/sites/${siteId}/tokens/id/999999999/`);
    expect(notFound.status()).toBe(404);
  });

  test('TOK-14 subject 更新', async () => {
    const created = await api.post(`/sites/${siteId}/tokens/`, {
      data: { token: unique('tok').replace(/-/g, '_') },
    });
    const id = ((await created.json()) as TokenRead).id;
    createdTokenIds.push(id);

    const res = await api.patch(`/sites/${siteId}/tokens/id/${id}/`, {
      data: { subject: 'updated-subject' },
    });
    expect(res.status()).toBe(200);
    expect(((await res.json()) as TokenRead).subject).toBe('updated-subject');
  });

  test('TOK-15 存在しない token_id の更新で404', async () => {
    const res = await api.patch(`/sites/${siteId}/tokens/id/999999999/`, {
      data: { subject: 'x' },
    });
    expect(res.status()).toBe(404);
  });

  test('TOK-16 許可外 status_code で422', async () => {
    const created = await api.post(`/sites/${siteId}/tokens/`, {
      data: { token: unique('tok').replace(/-/g, '_') },
    });
    const id = ((await created.json()) as TokenRead).id;
    createdTokenIds.push(id);

    const res = await api.patch(`/sites/${siteId}/tokens/id/${id}/`, {
      data: { status_code: 400 },
    });
    expect(res.status()).toBe(422);
  });

  test('TOK-17 削除すると以後404', async () => {
    const created = await api.post(`/sites/${siteId}/tokens/`, {
      data: { token: unique('tok').replace(/-/g, '_') },
    });
    const id = ((await created.json()) as TokenRead).id;

    const del = await api.delete(`/sites/${siteId}/tokens/id/${id}/`);
    expect(del.status()).toBe(204);

    const after = await api.get(`/sites/${siteId}/tokens/id/${id}/`);
    expect(after.status()).toBe(404);
  });

  test('TOK-18 存在しない token_id の削除で404', async () => {
    const res = await api.delete(`/sites/${siteId}/tokens/id/999999999/`);
    expect(res.status()).toBe(404);
  });
});
