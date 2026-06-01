# fa API E2E テスト

FastAPI 製 REST API (`fa API`) の E2E テストを Playwright（TypeScript / API テスト機能）で自動化したもの。

## 構成

```
.
├── docs/
│   ├── test-spec.en.md     # テスト仕様書（英語版）
│   └── test-spec.ja.md     # テスト仕様書（日本語版）
├── tests/
│   ├── helpers/auth.ts     # 認証（トークン取得）ヘルパー
│   ├── fixtures.ts         # 共通フィクスチャ（認証済み/匿名コンテキスト）
│   ├── auth.spec.ts        # /token, /token/refresh, /token/revoke, 共通401
│   ├── sites.spec.ts       # Sites の CRUD
│   ├── tokens.spec.ts      # site 配下 Tokens の CRUD
│   ├── users.spec.ts       # Users（admin限定操作・権限・自己削除不可）
│   └── user-sites.spec.ts  # ユーザーとサイトの紐付け・権限
├── global-setup.ts         # FA_PASSWORD 未設定時にプロンプトで入力を求める
├── playwright.config.ts
├── package.json
├── tsconfig.json
└── .env.example
```

## セットアップ

前提: Node.js 18 以上。

```bash
npm install
npx playwright install        # ブラウザ不要だが初回のみ実行推奨
cp .env.example .env          # Windows: copy .env.example .env
```

`.env` を編集して認証情報を設定:

```
BASE_URL=https://fa-api.nkn.tw
FA_USERNAME=your@email.com
FA_PASSWORD=（パスワード）
```

> パスワードは `.env` に保存し、Git にはコミットしないこと（`.gitignore` 済み）。CI では環境変数 / シークレットで渡す。`FA_PASSWORD` を省略するとテスト起動時にプロンプトで入力を求められる。

### ローカルデバッグ環境

VSCode デバッガーで起動したサーバーに対してテストを実行する場合:

1. `.env.example` を `.env.local` にコピーし、`BASE_URL=http://localhost:8000` を設定する。
2. VSCode の **"Python Debugger: FastAPI - API"** launch config でサーバーを起動する。
3. **"Playwright: E2E (localhost:8000)"** launch config でテストを実行する。または **"FastAPI + E2E (Test)"** Compound launch で両方を同時起動することもできる。

## 実行

```bash
npm test                                   # 全テスト実行
npx playwright test tests/auth.spec.ts     # ファイル単位
npx playwright test -g "AUTH-01"           # ケース名で絞り込み
npm run report                             # 直近の HTML レポートを表示
```

型チェックのみ:

```bash
npm run typecheck
```

## 設計メモ

- **認証**: `POST /token`（OAuth2 password grant）でトークン取得後、`Authorization: Bearer` を付けた `APIRequestContext` を `fixtures.ts` の `api` フィクスチャで提供。401系テスト用に未認証の `anon` も用意。
- **権限テスト**: 実行ユーザーが管理者かを `GET /users/me/` で判定し、admin 限定ケースは非adminだと自動 skip。非admin の 403 検証用に、テスト内で一時的な非adminユーザーを作成してログインする。
- **後始末**: 作成した Token / User / Site は依存関係の逆順（token → user → site）で `afterAll` にて削除。409 を検証する削除テスト（SITE-11/12 等）は `try/finally` でインライン後始末する。
- **直列実行**: データ競合を避けるため初期設定は `workers: 1`。安定後に並列化可能。

## 注意

- 仕様書は OpenAPI から逆算して作成。実レスポンスと差異があれば実行結果を正としてケースを更新する。
- `AUTH-09`（revoke 後トークンの即時失効）は即時失効を前提としている。遅延失効の仕様であれば該当ケースを調整する。
- 破壊的操作を含むため、可能なら**本番ではなくテスト環境**に対して実行することを推奨。
