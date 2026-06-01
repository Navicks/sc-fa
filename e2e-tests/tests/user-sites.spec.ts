import { test, expect, unique } from './fixtures';
import { createAuthedContext } from './helpers/auth';
import type { APIRequestContext } from '@playwright/test';

interface UserRead { id: number; is_admin: boolean; }
interface SiteRead { id: number; }
interface UserSiteRead { user_id: number; site_id: number; permission: number; }

test.describe('User-Sites', () => {
  let api: APIRequestContext;
  let isAdmin = false;
  let userId: number;
  let siteId: number;
  const createdUserIds: number[] = [];

  test.beforeAll(async ({ baseURL }) => {
    const authed = await createAuthedContext(baseURL!);
    api = authed.ctx;
    const meRes = await api.get('/users/me/');
    const me = (await meRes.json()) as UserRead;
    isAdmin = !!me.is_admin;
    if (!isAdmin) return;

    // Prepare test user and site
    const u = await api.post('/users/', {
      data: { email: `${unique('e2e-us')}@example.com`, display_name: 'US Test', password: 'Passw0rd!x' },
    });
    userId = ((await u.json()) as UserRead).id;
    createdUserIds.push(userId);

    const s = await api.post('/sites/', {
      data: { fqdn: `${unique('e2e-us')}.example.com`, name: 'US Test Site' },
    });
    siteId = ((await s.json()) as SiteRead).id;
  });

  test.afterAll(async () => {
    for (const id of createdUserIds) {
      await api.delete(`/users/${id}/`).catch(() => {});
    }
    // Delete site after user deletion cascades the user_site records
    if (siteId) await api.delete(`/sites/${siteId}/`).catch(() => {});
    await api.dispose();
  });

  test('US-01 サイトをユーザーに割当', async () => {
    test.skip(!isAdmin, '管理者権限が必要');
    const res = await api.post(`/users/${userId}/sites/`, {
      data: { site_id: siteId, permission: 1 },
    });
    expect(res.status()).toBe(201);
    const body = (await res.json()) as UserSiteRead;
    expect(body.user_id).toBe(userId);
    expect(body.site_id).toBe(siteId);
  });

  test('US-02 重複割当で409', async () => {
    test.skip(!isAdmin, '管理者権限が必要');
    const res = await api.post(`/users/${userId}/sites/`, {
      data: { site_id: siteId, permission: 1 },
    });
    expect(res.status()).toBe(409);
  });

  test('US-03 存在しないsite_idで404', async () => {
    test.skip(!isAdmin, '管理者権限が必要');
    const res = await api.post(`/users/${userId}/sites/`, {
      data: { site_id: 999999999, permission: 1 },
    });
    expect(res.status()).toBe(404);
  });

  test('US-05 ユーザーのサイト一覧', async () => {
    test.skip(!isAdmin, '管理者権限が必要');
    const res = await api.get(`/users/${userId}/sites/`);
    expect(res.status()).toBe(200);
    const body = (await res.json()) as UserSiteRead[];
    expect(Array.isArray(body)).toBe(true);
    expect(body.some((x) => x.site_id === siteId)).toBe(true);
  });

  test('US-07 自分のサイト一覧', async () => {
    const res = await api.get('/users/me/sites/');
    expect(res.status()).toBe(200);
    expect(Array.isArray(await res.json())).toBe(true);
  });

  test('US-08 権限を更新 (1→2)', async () => {
    test.skip(!isAdmin, '管理者権限が必要');
    const res = await api.patch(`/users/${userId}/sites/${siteId}/`, {
      data: { permission: 2 },
    });
    expect(res.status()).toBe(200);
    expect(((await res.json()) as UserSiteRead).permission).toBe(2);
  });

  test('US-09 存在しない組合せの更新で404', async () => {
    test.skip(!isAdmin, '管理者権限が必要');
    const res = await api.patch(`/users/${userId}/sites/999999999/`, {
      data: { permission: 2 },
    });
    expect(res.status()).toBe(404);
  });
});
