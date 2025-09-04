# シンプルインターフォンシステム - 開発ガイド

## 開発環境の起動

### 1. 通常の開発（単一ポート）
```bash
npm run dev
```
- ポート3000で起動
- 一般的な開発用

### 2. 訪問者専用サーバー
```bash
npm run dev:visitor
```
- ポート3000で起動
- インターフォンデバイス用（訪問者が使用）

### 3. スタッフ専用サーバー
```bash
npm run dev:staff
```
- ポート3001で起動
- スタッフのビデオ通話参加用

### 4. デュアルサーバー（推奨）
```bash
npm run dev:dual
```
- **訪問者サーバー**: http://localhost:3000
- **スタッフサーバー**: http://localhost:3001
- 両方を同時起動して完全なインターフォン体験をテスト

## 使用方法

1. **訪問者フロー:**
   - http://localhost:3000 でインターフォン画面を表示
   - 呼出ボタンを押してビデオ通話開始

2. **スタッフフロー:**
   - Slackに送信されるURL（http://localhost:3001/video-call?room=xxx&staff=true）をクリック
   - ビデオ通話に参加

## 環境設定

`.env.local` ファイルに以下の設定が必要：

```env
# アプリ設定
NODE_ENV=development
FRONTEND_URL=http://localhost:3000

# 開発設定（デュアルサーバーモード用）
STAFF_PORT=3001

# Twilio設定
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_API_KEY=your_api_key
TWILIO_API_SECRET=your_api_secret
```

**重要**: 開発時は `STAFF_PORT=3001` を設定することで、Slackに送信されるURLが自動的に3001番ポートになります。

## その他のコマンド

- `npm run build` - 本番用ビルド
- `npm run test` - テスト実行
- `npm run lint` - コード品質チェック
- `npm run type-check` - TypeScript型チェック

## アーキテクチャ

- **フロントエンド**: Next.js 15 + TypeScript + Tailwind CSS
- **ビデオ通話**: Twilio Video API
- **状態管理**: Zustand
- **通知**: Slack Webhook
- **UI**: sample.tsxベースのインターフォンデザイン