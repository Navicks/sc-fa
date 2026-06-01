# fa API E2E テスト仕様書

- 対象: `fa API` v0.1.10
- ベースURL: `https://fa-api.nkn.tw`
- Swagger: `https://fa-api.nkn.tw/int/docs`
- OpenAPI: `https://fa-api.nkn.tw/openapi.json`
- 認証方式: OAuth2 password flow（`POST /token` でアクセストークン取得 → `Authorization: Bearer <token>`）
- 作成日: 2026-06-01

本仕様書は OpenAPI スペックから逆算して作成した。実サイト未確認の挙動（「TBD」）は、テスト実行時に実際のレスポンスで確定させること。

---

## 0. 凡例・前提

- **優先度**: P1=必須（主要導線・回帰必須）/ P2=重要 / P3=余裕があれば
- **種別**: 正常系 / 異常系（バリデーション・権限・未存在）
- テスト実行ユーザー: `knamiki@groove.ne.jp`（管理者権限を前提とするテストあり。`is_admin` の状態は `GET /users/me/` で実行時に確認する）
- 破壊的操作（作成・更新・削除）は **テスト用データを作成 → 検証 → 必ず削除** の流れで完結させ、本番データを汚さない。
- 各セキュアエンドポイントは共通で「トークン無し/不正トークンで 401」を確認する（共通ケース C-AUTH）。

### 共通ケース

| ID | 対象 | 条件 | 期待結果 | 優先度 |
|----|------|------|----------|--------|
| C-AUTH-01 | 全セキュアEP | `Authorization` ヘッダ無し | 401 | P1 |
| C-AUTH-02 | 全セキュアEP | 不正・期限切れトークン | 401 | P1 |
| C-VALID-01 | パスパラメータ`{id}` が整数のEP | `id` に非整数（例 `abc`）を指定 | 422 | P2 |

---

## 1. Auth（認証）

| ID | エンドポイント | 種別 | 前提・入力 | 期待結果 | 優先度 |
|----|----------------|------|-----------|----------|--------|
| AUTH-01 | `POST /token` | 正常 | 正しい username/password、`grant_type=password` | 200。`access_token` / `refresh_token` / 各 `*_expires` / `token_type` を含む | P1 |
| AUTH-02 | `POST /token` | 異常 | 誤ったパスワード | 401 | P1 |
| AUTH-03 | `POST /token` | 異常 | `username` 欠如 | 422 | P2 |
| AUTH-04 | `POST /token` | 異常 | `password` 欠如 | 422 | P2 |
| AUTH-05 | `GET /token/refresh` | 正常 | 有効な refresh_token を Bearer 指定 | 200。新しいトークン一式 | P1 |
| AUTH-06 | `GET /token/refresh` | 異常 | 無効・期限切れ refresh_token | 401 | P2 |
| AUTH-07 | `GET /token/revoke` | 正常 | 有効なアクセストークン | 204 | P2 |
| AUTH-08 | `GET /token/revoke` | 異常 | 無効トークン | 401 | P2 |
| AUTH-09 | revoke後の再利用 | 異常 | revoke 済みトークンで保護APIを呼ぶ | 401（TBD: 即時失効か要確認） | P2 |

---

## 2. Sites

`SiteCreate`: `fqdn`(必須, string), `name`(必須, ≤255)

| ID | エンドポイント | 種別 | 前提・入力 | 期待結果 | 優先度 |
|----|----------------|------|-----------|----------|--------|
| SITE-01 | `POST /sites/` | 正常 | 一意な fqdn + name | 201。`id`/`fqdn`/`name` 返却 | P1 |
| SITE-02 | `POST /sites/` | 異常 | `fqdn` 欠如 | 422 | P2 |
| SITE-03 | `POST /sites/` | 異常 | `name` が256文字以上 | 422 | P3 |
| SITE-04 | `GET /sites/{site_id}/` | 正常 | 作成済み site_id | 200。作成内容と一致 | P1 |
| SITE-05 | `GET /sites/{site_id}/` | 異常 | 存在しない site_id | 404 | P1 |
| SITE-06 | `GET /sites/fqdn/{fqdn}/` | 正常 | 作成済み fqdn | 200。同一 site | P2 |
| SITE-07 | `GET /sites/fqdn/{fqdn}/` | 異常 | 存在しない fqdn | 404 | P2 |
| SITE-08 | `PATCH /sites/{site_id}/` | 正常 | `name` 変更 | 200。name 更新済み | P1 |
| SITE-09 | `PATCH /sites/{site_id}/` | 正常 | `fqdn` 変更 | 200。fqdn 更新済み | P2 |
| SITE-10 | `PATCH /sites/{site_id}/` | 異常 | 存在しない site_id | 404 | P2 |
| SITE-11 | `DELETE /sites/{site_id}/` | 異常 | user_site が存在する site を削除 | 409 | P1 |
| SITE-12 | `DELETE /sites/{site_id}/` | 異常 | token が存在する site を削除 | 409 | P1 |
| SITE-13 | `DELETE /sites/{site_id}/` | 正常 | 依存なし site を削除 | 204。再 GET で 404 | P1 |
| SITE-14 | `DELETE /sites/{site_id}/` | 異常 | 存在しない site_id | 404 | P2 |

---

## 3. Tokens（site配下）

`TokenCreate`: `token`(必須, `^[0-9A-Za-z_-]{1,255}$`), `redirect_uri`(任意, URI), `subject`(任意), `status_code`(301/302/303/308, 既定302), `valid_from`/`valid_to`(任意, datetime)

| ID | エンドポイント | 種別 | 前提・入力 | 期待結果 | 優先度 |
|----|----------------|------|-----------|----------|--------|
| TOK-01 | `POST /sites/{site_id}/tokens/` | 正常 | 有効な token 文字列 | 201。`id`/`site_id`/`token` 返却 | P1 |
| TOK-02 | `POST /sites/{site_id}/tokens/` | 正常 | redirect_uri + status_code=301 指定 | 201。指定値が反映 | P2 |
| TOK-03 | `POST /sites/{site_id}/tokens/` | 異常 | token に不正文字（例 スペース） | 422 | P2 |
| TOK-04 | `POST /sites/{site_id}/tokens/` | 異常 | redirect_uri が不正URI | 422 | P3 |
| TOK-05 | `POST /sites/{site_id}/tokens/` | 異常 | 存在しない site_id | 404 | P2 |
| TOK-06 | `GET /sites/{site_id}/tokens/` | 正常 | トークン2件以上作成済み | 200。配列で返却 | P1 |
| TOK-07 | `GET /sites/{site_id}/tokens/` | 正常 | `l=1&o=0` / `o=1` | ページング動作（件数・オフセット反映） | P2 |
| TOK-08 | `GET /sites/{site_id}/tokens/` | 異常 | `l=0` または `l>1000` | 422（制約 0<l≤1000） | P3 |
| TOK-09 | `GET /sites/{site_id}/tokens/` | 異常 | 存在しない site_id | 404 | P2 |
| TOK-10 | `GET /sites/{site_id}/tokens/{token}/` | 正常 | token文字列で取得 | 200。一致 | P1 |
| TOK-11 | `GET /sites/{site_id}/tokens/{token}/` | 異常 | 存在しない token | 404 | P2 |
| TOK-12 | `GET /sites/{site_id}/tokens/id/{token_id}/` | 正常 | token_id で取得 | 200。一致 | P1 |
| TOK-13 | `GET /sites/{site_id}/tokens/id/{token_id}/` | 異常 | 存在しない token_id | 404 | P2 |
| TOK-14 | `PATCH /sites/{site_id}/tokens/id/{token_id}/` | 正常 | `subject` 変更 | 200。更新済み | P1 |
| TOK-15 | `PATCH /sites/{site_id}/tokens/id/{token_id}/` | 異常 | 存在しない token_id | 404 | P2 |
| TOK-16 | `PATCH /sites/{site_id}/tokens/id/{token_id}/` | 異常 | status_code に許可外値（例400） | 422 | P3 |
| TOK-17 | `DELETE /sites/{site_id}/tokens/id/{token_id}/` | 正常 | 作成済み token_id | 204。再GETで404 | P1 |
| TOK-18 | `DELETE /sites/{site_id}/tokens/id/{token_id}/` | 異常 | 存在しない token_id | 404 | P2 |

---

## 4. Users

`UserCreate`: `email`(必須, email), `display_name`(必須, ≤255), `password`(必須), `disabled`(既定false), `is_admin`(既定false)。作成・他ユーザー参照・削除は **admin 限定**。

| ID | エンドポイント | 種別 | 前提・入力 | 期待結果 | 優先度 |
|----|----------------|------|-----------|----------|--------|
| USR-01 | `GET /users/me/` | 正常 | 認証済み | 200。自分の情報（`is_admin` 確認に使用） | P1 |
| USR-02 | `PATCH /users/me/` | 正常 | `display_name` 変更 → 元に戻す | 200。更新済み | P2 |
| USR-03 | `POST /users/` | 正常(admin) | 一意 email の新規ユーザー | 201。作成後 USR-09 で削除 | P1 |
| USR-04 | `POST /users/` | 異常 | 非admin 実行 | 403 | P2 |
| USR-05 | `POST /users/` | 異常 | email 形式不正 | 422 | P2 |
| USR-06 | `GET /users/{user_id}/` | 正常(admin) | 作成済み user_id | 200 | P1 |
| USR-07 | `GET /users/{user_id}/` | 異常 | 存在しない user_id | 404 | P2 |
| USR-08 | `GET /users/{user_id}/` | 異常 | 非admin が他ユーザー参照 | 403 | P2 |
| USR-09 | `GET /users/email/{email}/` | 正常(admin) | 作成済み email | 200 | P2 |
| USR-10 | `GET /users/email/{email}/` | 異常 | 存在しない email | 404 | P2 |
| USR-11 | `PATCH /users/{user_id}/` | 正常(admin) | display_name 変更 | 200 | P2 |
| USR-12 | `PATCH /users/{user_id}/` | 異常 | 存在しない user_id | 404 | P3 |
| USR-13 | `DELETE /users/{user_id}/` | 正常(admin) | テスト作成ユーザー | 204 | P1 |
| USR-14 | `DELETE /users/{user_id}/` | 異常 | 自分自身を削除 | 400 | P1 |
| USR-15 | `DELETE /users/{user_id}/` | 異常 | 存在しない user_id | 404 | P3 |

---

## 5. User-Sites（ユーザーとサイトの紐付け・権限）

`SitePermission`: 1/2/3。`UserSiteCreateWithoutUser`: `site_id`(必須), `permission`(既定1)。割当・参照は admin 限定。

| ID | エンドポイント | 種別 | 前提・入力 | 期待結果 | 優先度 |
|----|----------------|------|-----------|----------|--------|
| US-01 | `POST /users/{user_id}/sites/` | 正常(admin) | テストユーザー + テストsite | 201。`user_id`/`site_id`/`permission` | P1 |
| US-02 | `POST /users/{user_id}/sites/` | 異常 | 同一 site を重複割当 | 409 | P2 |
| US-03 | `POST /users/{user_id}/sites/` | 異常 | 存在しない user_id または site_id | 404 | P2 |
| US-04 | `POST /users/{user_id}/sites/` | 異常 | 非admin 実行 | 403 | P2 |
| US-05 | `GET /users/{user_id}/sites/` | 正常(admin) | 割当済み | 200。配列に含まれる | P1 |
| US-06 | `GET /users/{user_id}/sites/` | 正常 | `l`/`o` ページング | 件数・オフセット反映 | P3 |
| US-07 | `GET /users/me/sites/` | 正常 | 認証済み | 200。配列 | P1 |
| US-08 | `PATCH /users/{user_id}/sites/{site_id}/` | 正常(admin) | permission を 1→2 | 200。更新済み | P2 |
| US-09 | `PATCH /users/{user_id}/sites/{site_id}/` | 異常 | 存在しない組合せ | 404 | P3 |

---

## 6. 後始末（teardown）方針

テスト内で作成したリソースは、依存関係の逆順で削除する。

1. Token 削除（`DELETE /sites/{site_id}/tokens/id/{token_id}/`）
2. テストユーザー削除（`DELETE /users/{user_id}/`）→ user_site が DB カスケードで自動削除される
3. Site 削除（`DELETE /sites/{site_id}/`）→ user_site・token がなければ 204

各 spec の `afterAll` で `createdSiteIds` / `createdTokenIds` / `createdUserIds` を追跡し、エラーは `.catch(() => {})` で無視して後続の後始末を続ける。

SITE-11/12 のような「依存あり削除の 409 テスト」は、テスト内の `try/finally` で依存リソースを削除してからサイトを削除する（`afterAll` には登録しない）。

---

## 7. 実行結果と判明事項（2026-06-01 初回実行）

初回実行（全54ケース）と診断スクリプト（`scripts/diagnose.mjs`）で、以下のAPI側の問題・仕様不一致を検出した。

### A. APIバグ（検出・修正済み）

| ID | 内容 | 期待 | 実際 | 状態 |
|----|------|------|------|------|
| USR-02 | `PATCH /users/me/` が有効な入力でも 500 を返す。Redis キャッシュから復元した `current_user` がセッション外トランジェントオブジェクトのため `session.refresh()` が例外。 | 200 | 500 | **修正済み**。`session.get(User, current_user.id)` で再取得するよう変更。`test.fail()` 解除。 |
| US-03 | 存在しない `site_id` の割当で、site 存在チェックより先に重複チェックが誤発火し 409 を返す。`IntegrityError` の FK 違反と PK 重複を区別していなかった。 | 404 | 409 | **修正済み**。`session.flush()` 前に `session.get(Site, site_id)` で存在確認を追加。`test.fail()` 解除。 |

### B. 仕様（OpenAPI）とAPIの不一致（修正済み）

| ID | 内容 | OpenAPI | 実際 | 対応 |
|----|------|---------|------|------|
| TOK-09 | 存在しない site の token 一覧。実装が site 存在チェックをせず空配列で 200 を返していた。 | 404 | 200 `[]` | **修正済み**。`select(func.exists())` で site 存在確認を追加し 404 を返すよう変更。テストも 404 期待に更新。 |

### C. テスト設計上の修正

| ID | 内容 |
|----|------|
| US-05 / US-08 | 単独実行では成功。スイートで失敗したのは、直前のUS-03（バグで409を返す割当）が共有ユーザーの状態を汚していたため。US-03を専用ユーザーに隔離して解消。 |

> 初回実行で検出した API バグ・仕様不一致はすべて修正済み。
