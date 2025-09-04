# Simple Intercom System

シンプルなタブレット型インターコムシステム。Twilio Video APIを使用したワンクリックビデオ通話システム。

## 概要

来訪者がタブレット端末で呼び出しボタンを押すと、スタッフのSlackに通知が届き、ビデオ通話で応対できるインターコムシステムです。

**主な機能：**
- ワンクリックビデオ通話開始
- Slack通知による自動スタッフ呼び出し
- タブレット最適化されたインターコム端末UI
- リアルタイム双方向映像・音声通信

## 操作方法

### セットアップ

```bash
cd frontend
npm install
cp .env.example .env.local
# .env.localでTwilio APIキーとSlack設定を編集
npm run dev:dual
```

### 使用方法

1. **来訪者**: http://localhost:3000 で呼び出しボタンを押下
2. **スタッフ**: Slack通知のリンクをクリックしてビデオ通話に参加
3. **通話**: ブラウザ上でリアルタイム映像・音声通話

### 必要な設定

`.env.local`ファイルに以下を設定：

```bash
# Twilio Video API
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_API_KEY=your_api_key
TWILIO_API_SECRET=your_api_secret

# Slack通知
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/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

```