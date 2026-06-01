import { test, expect, unique } from './fixtures';
import { createAuthedContext, fetchToken } from './helpers/auth';
import { request } from '@playwright/test';
import type { APIRequestContext } from '@playwright/test';

interface UserRead {
  id: number; email: string; display_name: string;
  disabled: boolean; is_admin: boolean;
}

test.describe('Users', () => {
  let api: APIRequestContext;
  let me: UserRead;
  let isAdmin = false;
  const createdUserIds: number[] = [];

  test.beforeAll(async ({ baseURL }) => {
    const authed = await createAuthedContext(baseURL!);
    api = authed.ctx;
    const res = await api.get('/users/me/');
    me = (await res.json()) as UserRead;
    isAdmin = !!me.is_admin;
  });

  test.afterAll(async () => {
    for (const id of createdUserIds) {
      await api.delete(`/users/${id}/`).catch(() => {});
    }
    await api.dispose();
  });

  test('USR-01 自分の情報を取得', async () => {
    const res = await api.get('/users/me/');
    expect(res.status()).toBe(200);
    const body = (await res.json()) as UserRead;
    expect(body.email).toBeTruthy();
    expect(body.id).toBeGreaterThan(0);
  });

  test('USR-02 自分のdisplay_nameを更新して戻す', async () => {
    const original = me.display_name;
    const upd = await api.patch('/users/me/', { data: { display_name: 'E2E Temp Name' } });
    expect(upd.status()).toBe(200);
    expect(((await upd.json()) as UserRead).display_name).toBe('E2E Temp Name');
    // Restore original value
    const revert = await api.patch('/users/me/', { data: { display_name: original } });
    expect(revert.status()).toBe(200);
  });

  test('USR-03 ユーザー作成 (admin限定)', async () => {
    test.skip(!isAdmin, '管理者権限が必要');
    const email = `${unique('e2e-user')}@example.com`;
    const res = await api.post('/users/', {
      data: { email, display_name: 'E2E User', password: 'Passw0rd!x', is_admin: false },
    });
    expect(res.status()).toBe(201);
    const body = (await res.json()) as UserRead;
    expect(body.email).toBe(email);
    createdUserIds.push(body.id);
  });

  test('USR-05 不正なemailで422', async () => {
    test.skip(!isAdmin, '管理者権限が必要');
    const res = await api.post('/users/', {
      data: { email: 'not-an-email', display_name: 'x', password: 'Passw0rd!x' },
    });
    expect(res.status()).toBe(422);
  });

  test('USR-06/07 ユーザー取得 (admin限定)', async () => {
    test.skip(!isAdmin, '管理者権限が必要');
    const email = `${unique('e2e-user')}@example.com`;
    const created = await api.post('/users/', {
      data: { email, display_name: 'E2E Get', password: 'Passw0rd!x' },
    });
    const id = ((await created.json()) as UserRead).id;
    createdUserIds.push(id);

    const ok = await api.get(`/users/${id}/`);
    expect(ok.status()).toBe(200);

    const notFound = await api.get('/users/999999999/');
    expect(notFound.status()).toBe(404);
  });

  test('USR-09/10 email でユーザー取得 (admin限定)', async () => {
    test.skip(!isAdmin, '管理者権限が必要');
    const email = `${unique('e2e-user')}@example.com`;
    const created = await api.post('/users/', {
      data: { email, display_name: 'E2E Email', password: 'Passw0rd!x' },
    });
    createdUserIds.push(((await created.json()) as UserRead).id);

    const ok = await api.get(`/users/email/${encodeURIComponent(email)}/`);
    expect(ok.status()).toBe(200);

    const notFound = await api.get('/users/email/no-such@example.invalid/');
    expect(notFound.status()).toBe(404);
  });

  test('USR-11/12 ユーザー更新 (admin限定)', async () => {
    test.skip(!isAdmin, '管理者権限が必要');
    const created = await api.post('/users/', {
      data: { email: `${unique('e2e-user')}@example.com`, display_name: 'before', password: 'Passw0rd!x' },
    });
    const id = ((await created.json()) as UserRead).id;
    createdUserIds.push(id);

    const upd = await api.patch(`/users/${id}/`, { data: { display_name: 'after' } });
    expect(upd.status()).toBe(200);
    expect(((await upd.json()) as UserRead).display_name).toBe('after');

    const notFound = await api.patch('/users/999999999/', { data: { display_name: 'x' } });
    expect(notFound.status()).toBe(404);
  });

  test('USR-13 ユーザー削除 (admin限定)', async () => {
    test.skip(!isAdmin, '管理者権限が必要');
    const created = await api.post('/users/', {
      data: { email: `${unique('e2e-user')}@example.com`, display_name: 'todelete', password: 'Passw0rd!x' },
    });
    const id = ((await created.json()) as UserRead).id;

    const del = await api.delete(`/users/${id}/`);
    expect(del.status()).toBe(204);

    const after = await api.get(`/users/${id}/`);
    expect(after.status()).toBe(404);
  });

  test('USR-14 自分自身は削除できない (400)', async () => {
    const res = await api.delete(`/users/${me.id}/`);
    expect(res.status()).toBe(400);
  });

  test('USR-04/08 非adminによる操作は403', async ({ baseURL }) => {
    test.skip(!isAdmin, 'テスト用の非adminユーザーを作成するため管理者権限が必要');
    // Create a non-admin user and log in as them
    const email = `${unique('e2e-nonadmin')}@example.com`;
    const password = 'Passw0rd!x';
    const created = await api.post('/users/', {
      data: { email, display_name: 'NonAdmin', password, is_admin: false },
    });
    const id = ((await created.json()) as UserRead).id;
    createdUserIds.push(id);

    const anon = await request.newContext({ baseURL: baseURL! });
    const tokenRes = await fetchToken(anon, email, password);
    const token = (await tokenRes.json()).access_token as string;
    await anon.dispose();

    const nonAdmin = await request.newContext({
      baseURL: baseURL!,
      extraHTTPHeaders: { Authorization: `Bearer ${token}` },
    });

    // USR-04: non-admin attempting to create a user → 403
    const createRes = await nonAdmin.post('/users/', {
      data: { email: `${unique('x')}@example.com`, display_name: 'x', password: 'Passw0rd!x' },
    });
    expect(createRes.status()).toBe(403);

    // USR-08: non-admin accessing another user → 403
    const readRes = await nonAdmin.get(`/users/${me.id}/`);
    expect(readRes.status()).toBe(403);

    await nonAdmin.dispose();
  });
});
