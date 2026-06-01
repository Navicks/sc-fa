import 'dotenv/config';

const BASE = process.env.BASE_URL ?? 'https://fa-api.nkn.tw';
const U = process.env.FA_USERNAME;
const P = process.env.FA_PASSWORD;

const log = (label, res, body) =>
  console.log(`\n[${label}] ${res.status} ${res.statusText}\n${typeof body === 'string' ? body : JSON.stringify(body)}`);

async function jsonOrText(res) {
  const t = await res.text();
  try { return JSON.parse(t); } catch { return t; }
}

const uniq = (p) => `${p}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;

async function main() {
  // 1) login
  const tokRes = await fetch(`${BASE}/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ grant_type: 'password', username: U, password: P }),
  });
  const tok = await tokRes.json();
  const auth = { Authorization: `Bearer ${tok.access_token}`, Accept: 'application/json' };
  const jh = { ...auth, 'Content-Type': 'application/json' };

  // me
  let r = await fetch(`${BASE}/users/me/`, { headers: auth });
  log('GET /users/me/', r, await jsonOrText(r));

  // USR-02: patch me
  r = await fetch(`${BASE}/users/me/`, { method: 'PATCH', headers: jh, body: JSON.stringify({ display_name: 'E2E Temp Name' }) });
  log('PATCH /users/me/ {display_name}', r, await jsonOrText(r));

  // TOK-09: tokens of nonexistent site
  r = await fetch(`${BASE}/sites/999999999/tokens/`, { headers: auth });
  log('GET /sites/999999999/tokens/', r, await jsonOrText(r));

  // ---- User-Sites flow ----
  const u = await fetch(`${BASE}/users/`, { method: 'POST', headers: jh, body: JSON.stringify({ email: `${uniq('diag')}@example.com`, display_name: 'Diag', password: 'Passw0rd!x' }) });
  const user = await jsonOrText(u);
  log('POST /users/', u, user);
  const userId = user.id;

  const s = await fetch(`${BASE}/sites/`, { method: 'POST', headers: jh, body: JSON.stringify({ fqdn: `${uniq('diag')}.example.com`, name: 'Diag Site' }) });
  const site = await jsonOrText(s);
  log('POST /sites/', s, site);
  const siteId = site.id;

  // US-01 assign
  r = await fetch(`${BASE}/users/${userId}/sites/`, { method: 'POST', headers: jh, body: JSON.stringify({ site_id: siteId, permission: 1 }) });
  log(`POST /users/${userId}/sites/ {site_id:${siteId}}`, r, await jsonOrText(r));

  // US-05 list
  r = await fetch(`${BASE}/users/${userId}/sites/`, { headers: auth });
  log(`GET /users/${userId}/sites/`, r, await jsonOrText(r));

  // US-08 patch permission
  r = await fetch(`${BASE}/users/${userId}/sites/${siteId}/`, { method: 'PATCH', headers: jh, body: JSON.stringify({ permission: 2 }) });
  log(`PATCH /users/${userId}/sites/${siteId}/`, r, await jsonOrText(r));

  // US-03 assign nonexistent site
  r = await fetch(`${BASE}/users/${userId}/sites/`, { method: 'POST', headers: jh, body: JSON.stringify({ site_id: 999999999, permission: 1 }) });
  log(`POST /users/${userId}/sites/ {site_id:999999999}`, r, await jsonOrText(r));

  // cleanup user
  r = await fetch(`${BASE}/users/${userId}/`, { method: 'DELETE', headers: auth });
  log(`DELETE /users/${userId}/`, r, await jsonOrText(r));

  console.log('\n--- done ---');
}
main().catch((e) => { console.error(e); process.exit(1); });
