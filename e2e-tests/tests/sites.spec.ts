import { test, expect, unique } from './fixtures';
import { createAuthedContext } from './helpers/auth';
import type { APIRequestContext } from '@playwright/test';

interface SiteRead { id: number; fqdn: string; name: string; }
interface TokenRead { id: number; site_id: number; }
interface UserRead { id: number; is_admin: boolean; }

test.describe('Sites', () => {
  let api: APIRequestContext;
  let isAdmin = false;
  let siteId: number;
  let fqdn: string;
  const createdSiteIds: number[] = [];

  test.beforeAll(async ({ baseURL }) => {
    const authed = await createAuthedContext(baseURL!);
    api = authed.ctx;
    const me = (await (await api.get('/users/me/')).json()) as UserRead;
    isAdmin = !!me.is_admin;
  });

  test.afterAll(async () => {
    for (const id of createdSiteIds) {
      await api.delete(`/sites/${id}/`).catch(() => {});
    }
    await api.dispose();
  });

  test('SITE-01 サイト作成', async () => {
    test.skip(!isAdmin, '管理者権限が必要');
    fqdn = `${unique('e2e')}.example.com`;
    const res = await api.post('/sites/', {
      data: { fqdn, name: 'E2E Test Site' },
    });
    expect(res.status()).toBe(201);
    const body = (await res.json()) as SiteRead;
    expect(body.id).toBeGreaterThan(0);
    expect(body.fqdn).toBe(fqdn);
    expect(body.name).toBe('E2E Test Site');
    siteId = body.id;
    createdSiteIds.push(siteId);
  });

  test('SITE-02 fqdn欠如で422', async () => {
    const res = await api.post('/sites/', { data: { name: 'no fqdn' } });
    expect(res.status()).toBe(422);
  });

  test('SITE-03 name 256文字以上で422', async () => {
    const res = await api.post('/sites/', {
      data: { fqdn: `${unique('e2e')}.example.com`, name: 'a'.repeat(256) },
    });
    expect(res.status()).toBe(422);
  });

  test('SITE-04 IDで取得', async () => {
    test.skip(!siteId, 'SITE-01 が先に成功している必要あり');
    const res = await api.get(`/sites/${siteId}/`);
    expect(res.status()).toBe(200);
    const body = (await res.json()) as SiteRead;
    expect(body.id).toBe(siteId);
    expect(body.fqdn).toBe(fqdn);
  });

  test('SITE-05 存在しないIDで404', async () => {
    const res = await api.get('/sites/999999999/');
    expect(res.status()).toBe(404);
  });

  test('C-VALID-01 非整数IDで422', async () => {
    const res = await api.get('/sites/not-an-int/');
    expect(res.status()).toBe(422);
  });

  test('SITE-06 FQDNで取得', async () => {
    test.skip(!siteId, 'SITE-01 が先に成功している必要あり');
    const res = await api.get(`/sites/fqdn/${fqdn}/`);
    expect(res.status()).toBe(200);
    const body = (await res.json()) as SiteRead;
    expect(body.id).toBe(siteId);
  });

  test('SITE-07 存在しないFQDNで404', async () => {
    const res = await api.get('/sites/fqdn/no-such-host.example.invalid/');
    expect(res.status()).toBe(404);
  });

  test('SITE-08 name更新', async () => {
    test.skip(!siteId, 'SITE-01 が先に成功している必要あり');
    const res = await api.patch(`/sites/${siteId}/`, {
      data: { name: 'E2E Updated Name' },
    });
    expect(res.status()).toBe(200);
    const body = (await res.json()) as SiteRead;
    expect(body.name).toBe('E2E Updated Name');
  });

  test('SITE-09 fqdn更新', async () => {
    test.skip(!siteId, 'SITE-01 が先に成功している必要あり');
    const newFqdn = `${unique('e2e-upd')}.example.com`;
    const res = await api.patch(`/sites/${siteId}/`, { data: { fqdn: newFqdn } });
    expect(res.status()).toBe(200);
    const body = (await res.json()) as SiteRead;
    expect(body.fqdn).toBe(newFqdn);
    fqdn = newFqdn;
  });

  test('SITE-10 存在しないIDの更新で404', async () => {
    const res = await api.patch('/sites/999999999/', { data: { name: 'x' } });
    expect(res.status()).toBe(404);
  });

  test('SITE-11 user_siteがあると409', async () => {
    test.skip(!isAdmin, '管理者権限が必要');
    const s = await api.post('/sites/', {
      data: { fqdn: `${unique('e2e-del')}.example.com`, name: 'Del Test' },
    });
    const tmpSiteId = ((await s.json()) as SiteRead).id;
    // Create a separate user and assign them; deleting the user cascades the user_site
    const u = await api.post('/users/', {
      data: { email: `${unique('e2e-del')}@example.com`, display_name: 'Del Test', password: 'Passw0rd!x' },
    });
    const tmpUserId = ((await u.json()) as UserRead).id;
    await api.post(`/users/${tmpUserId}/sites/`, { data: { site_id: tmpSiteId, permission: 1 } });
    try {
      const del = await api.delete(`/sites/${tmpSiteId}/`);
      expect(del.status()).toBe(409);
    } finally {
      await api.delete(`/users/${tmpUserId}/`).catch(() => {});
      await api.delete(`/sites/${tmpSiteId}/`).catch(() => {});
    }
  });

  test('SITE-12 tokenがあると409', async () => {
    test.skip(!isAdmin, '管理者権限が必要');
    const s = await api.post('/sites/', {
      data: { fqdn: `${unique('e2e-del')}.example.com`, name: 'Del Test Token' },
    });
    const tmpSiteId = ((await s.json()) as SiteRead).id;
    const t = await api.post(`/sites/${tmpSiteId}/tokens/`, {
      data: { token: unique('tok').replace(/-/g, '_') },
    });
    const tokenId = ((await t.json()) as TokenRead).id;
    try {
      const del = await api.delete(`/sites/${tmpSiteId}/`);
      expect(del.status()).toBe(409);
    } finally {
      await api.delete(`/sites/${tmpSiteId}/tokens/id/${tokenId}/`).catch(() => {});
      await api.delete(`/sites/${tmpSiteId}/`).catch(() => {});
    }
  });

  test('SITE-13 正常に削除できる', async () => {
    test.skip(!isAdmin, '管理者権限が必要');
    const s = await api.post('/sites/', {
      data: { fqdn: `${unique('e2e-del')}.example.com`, name: 'To Delete' },
    });
    const tmpSiteId = ((await s.json()) as SiteRead).id;
    const del = await api.delete(`/sites/${tmpSiteId}/`);
    expect(del.status()).toBe(204);
    const get = await api.get(`/sites/${tmpSiteId}/`);
    expect(get.status()).toBe(404);
  });

  test('SITE-14 存在しないIDの削除で404', async () => {
    test.skip(!isAdmin, '管理者権限が必要');
    const del = await api.delete('/sites/999999999/');
    expect(del.status()).toBe(404);
  });
});
