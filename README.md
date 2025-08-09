# AI受付システム - Hybrid Reception System

タブレット型AI受付システムのStep1実装。LangGraph + FastAPI + NextJSを使用したテキスト・音声対応来客システム。

> **Step1完了**: テキスト・音声対応システム | **Step2予定**: 高度な音声機能拡張

## 🚀 クイックスタート（開発環境）

### 前提条件

- **Python 3.11+** (仮想環境を使用)
- **Node.js 18+** 
- **npm**
- **OpenAI API Key**
- **Google Service Account Key** (Calendar API用)
- **Slack Webhook URL**

> **推奨**: Pythonパッケージのグローバルインストールを避けるため、仮想環境の使用を強く推奨します。

### 1. リポジトリのクローンとPython仮想環境のセットアップ

```bash
# リポジトリをクローン
git clone <repository-url>
cd ai-reception

# Python仮想環境の作成
python -m venv venv

# 仮想環境のアクティベート
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# pip のアップグレード（推奨）
python -m pip install --upgrade pip

# バックエンド依存関係のインストール（仮想環境内で実行）
pip install -r backend/requirements.txt

# フロントエンド依存関係のインストール
cd frontend && npm install
cd ..
```

### 2. 環境変数の設定

```bash
# バックエンド環境変数設定
cp backend/.env.example backend/.env

# .envファイルを編集して以下を設定:
# OPENAI_API_KEY=sk-your-openai-api-key
# GOOGLE_SERVICE_ACCOUNT_KEY={"type":"service_account",...}
# SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
# MEETING_ROOM_CALENDAR_IDS=calendar1@group.calendar.google.com,calendar2@group.calendar.google.com
```

### 3. Google Calendar設定

1. [Google Cloud Console](https://console.cloud.google.com/)でプロジェクト作成
2. Calendar APIを有効化
3. サービスアカウントを作成してJSONキーをダウンロード
4. 会議室カレンダーをサービスアカウントと共有
5. JSONキーの内容を`GOOGLE_SERVICE_ACCOUNT_KEY`環境変数に設定

### 4. Slack設定

1. [Slack App](https://api.slack.com/apps)を作成
2. Incoming Webhookを追加
3. Webhook URLを`SLACK_WEBHOOK_URL`環境変数に設定

### 5. 開発サーバーの起動

> **注意**: 以下のコマンドは仮想環境がアクティブな状態で実行してください。  
> 仮想環境がアクティブでない場合は `source venv/bin/activate` (Mac/Linux) または `venv\Scripts\activate` (Windows) を実行してください。

#### バックエンド (FastAPI)

```bash
# 仮想環境がアクティブであることを確認
which python  # Mac/Linux
where python  # Windows

# 開発用サーバー起動 (ポート8000)
cd backend
python -m uvicorn app.main:app --reload --port 8000

# または直接実行
python app/main.py
```

**API確認**: http://localhost:8000/api/health

#### フロントエンド (NextJS)

```bash
# 新しいターミナルを開いて実行（仮想環境は不要）
cd frontend
npm run dev
```

**アプリケーション確認**: http://localhost:3000

### 6. 動作確認

1. **ホームページ**: http://localhost:3000
2. **受付画面**: http://localhost:3000/reception
3. **API健康チェック**: http://localhost:8000/api/health
4. **API文書** (開発時のみ): http://localhost:8000/docs

## 📁 プロジェクト構造

```
ai-reception/
├── README.md                          # プロジェクトドキュメント
├── context-engineering/               # 開発ドキュメント・設計資料
│   ├── CLAUDE.md                     # Claude AIコンテキスト
│   ├── LLM_TEST_PLAN.md              # LLMテスト計画
│   ├── TEST_SCENARIOS.yaml           # テストシナリオ定義
│   └── PRPs/                         # プロジェクト要件文書
│       ├── ai-reception-system.md
│       ├── step1-text-reception-system.md
│       └── step2-voice-enhancement.md
├── backend/                          # FastAPI バックエンド
│   ├── app/
│   │   ├── main.py                  # FastAPI アプリケーション
│   │   ├── config.py                # 環境設定
│   │   ├── models/                  # データモデル (Pydantic/TypedDict)
│   │   │   ├── conversation.py      # 会話モデル
│   │   │   └── visitor.py           # 訪問者モデル
│   │   ├── agents/                  # LangGraph エージェント
│   │   │   ├── nodes.py             # ノード定義
│   │   │   └── reception_graph.py   # 受付フローグラフ
│   │   ├── services/                # 外部サービス統合
│   │   │   ├── calendar_service.py  # Google Calendar統合
│   │   │   ├── slack_service.py     # Slack通知
│   │   │   ├── text_service.py      # LLM処理
│   │   │   └── audio_service.py     # 音声処理（Whisper + TTS）
│   │   └── api/                     # REST API エンドポイント
│   │       ├── conversation.py      # 会話API
│   │       └── voice.py             # 音声API
│   ├── tests/                       # テストスイート（111個のテスト）
│   │   ├── README_LLM_TESTING.md    # LLMテストガイド
│   │   ├── test_llm_integration.py  # LLM統合テスト（AI応答品質）
│   │   ├── llm_test_framework.py    # テストフレームワーク
│   │   ├── llm_test_runner.py       # テスト実行エンジン
│   │   ├── test_scenarios.yaml      # テストシナリオ定義
│   │   ├── test_reception_graph.py  # レセプションフローテスト（21個）
│   │   ├── test_audio_service.py    # 音声機能テスト（Whisper + TTS）
│   │   ├── test_calendar_service.py # Google Calendarテスト
│   │   ├── test_conversation_api.py # REST APIテスト
│   │   ├── test_voice_websocket.py  # 音声WebSocketテスト
│   │   ├── test_visitor_type_ai.py  # AI訪問者タイプ判定テスト
│   │   ├── test_delivery_shortcut.py # 配達ショートカットテスト
│   │   └── test_specialized_nodes_integration.py # 専用ノード統合テスト
│   ├── requirements.txt             # Python 依存関係
│   ├── pyproject.toml               # Python プロジェクト設定
│   └── .env.example                 # 環境変数テンプレート
├── frontend/                        # NextJS フロントエンド（リファクタリング済み）
│   ├── app/                         # App Router ディレクトリ
│   │   ├── layout.tsx               # ルートレイアウト
│   │   ├── page.tsx                 # ホームページ
│   │   ├── globals.css              # グローバルスタイル
│   │   └── reception/               # 受付ページ
│   │       └── page.tsx             # Zustand統合済み
│   ├── components/                  # React コンポーネント
│   │   ├── VoiceInterface.tsx       # 音声インターフェース（WebSocket対応）
│   │   ├── ConversationDisplay.tsx  # 会話表示
│   │   ├── ReceptionButton.tsx      # 受付ボタン
│   │   ├── AudioVisualizer.tsx      # 音声可視化コンポーネント
│   │   └── VolumeReactiveMic.tsx    # ボリューム反応マイクUI
│   ├── hooks/                       # カスタムフック（分割・最適化済み）
│   │   ├── useVoiceChat.ts          # メイン音声チャットフック（統合）
│   │   ├── useVoiceConnection.ts    # WebSocket接続管理
│   │   ├── useVoiceRecording.ts     # 音声録音管理
│   │   ├── useVoicePlayback.ts      # 音声再生管理
│   │   ├── useConversationFlow.ts   # 会話フロー管理
│   │   ├── useVADIntegration.ts     # Voice Activity Detection統合
│   │   ├── useVoiceMessageHandlers.ts # WebSocketメッセージハンドラー
│   │   ├── useVoiceAutoStart.ts     # 自動開始ロジック
│   │   └── useGreetingMode.ts       # 挨拶モード管理
│   ├── stores/                      # Zustand状態管理（Phase 4追加）
│   │   ├── useReceptionStore.ts     # Reception画面状態
│   │   └── useVoiceStore.ts         # 音声チャット状態
│   ├── types/                       # TypeScript型定義（厳密化済み）
│   │   └── voice.ts                 # 音声関連Union Types
│   ├── lib/                         # ユーティリティ・API クライアント
│   │   ├── api.ts                   # APIクライアント
│   │   ├── websocket.ts             # WebSocketクライアント
│   │   ├── audio-recorder.ts        # 音声録音ユーティリティ
│   │   └── vad.ts                   # VADアルゴリズム
│   ├── __tests__/                   # テストスイート（49個のテスト）
│   │   ├── integration/              # 統合テスト
│   │   ├── components/               # コンポーネントテスト
│   │   └── hooks/                    # フックテスト
│   ├── package.json                 # Node.js 依存関係
│   ├── tailwind.config.js           # Tailwind CSS設定
│   └── tsconfig.json                # TypeScript設定
├── venv/                            # Python仮想環境（.gitignoreに追加）
└── vercel.json                      # Vercel デプロイ設定
```

## 🔧 開発ワークフロー

### テスト実行

> **注意**: Python関連のコマンドは仮想環境がアクティブな状態で実行してください。

```bash
# バックエンドテスト（仮想環境内で実行）
cd backend
pytest tests/ -v

# フロントエンドテスト（新しいターミナルで実行）
cd frontend  
npm test

# 型チェック
npm run type-check
```

### コード品質チェック

```bash
# Python (Ruff) - 仮想環境内で実行
cd backend
ruff check app/ --fix
ruff format app/

# TypeScript/JavaScript (ESLint)
cd frontend
npm run lint
```

### ビルド確認

```bash
# バックエンド起動確認（仮想環境内で実行）
cd backend
python app/main.py

# フロントエンドビルド
cd frontend
npm run build
```

## 🎯 機能概要

### コア機能

1. **🤖 AI対話システム**
   - LangGraphによる会話フロー管理
   - 自然言語での来客者情報収集
   - 確認・修正フロー

2. **🎙️ ハイブリッド入力システム**
   - **テキスト入力**: キーボード・タッチ入力対応
   - **音声入力**: Whisper API統合（音声→テキスト変換）
   - **TTS出力**: OpenAI TTS（テキスト→音声出力）
   - 入力方式の動的切り替え

3. **📅 予約確認システム**
   - Google Calendar API統合
   - 複数会議室対応
   - 来客者名での自動マッチング

4. **🎯 AI来客者タイプ判定システム**
   - **AI早期配達検出**: 配達業者を即座に判定しショートカット
   - **専用ガイダンスノード**: 各タイプ専用の最適化された案内
     - 予約来客 (appointment): カレンダー連動案内
     - 営業訪問 (sales): 丁寧なお断り案内  
     - 配達業者 (delivery): 迅速な配達手順案内

5. **💬 Slack通知**
   - リッチメッセージ形式
   - 対応ログ自動送信
   - エラー通知

6. **📱 タブレット最適化UI**
   - レスポンシブデザイン
   - タッチフレンドリー
   - リアルタイム会話表示
   - 音声・テキスト入力切り替えUI

### API エンドポイント

| メソッド | エンドポイント | 説明 |
|---------|-------------|-----|
| `GET` | `/api/health` | システム健康チェック |
| `POST` | `/api/conversations` | 新しい会話開始 |
| `POST` | `/api/conversations/{id}/messages` | テキストメッセージ送信 |
| `POST` | `/api/conversations/{id}/voice` | 音声データ送信（音声→テキスト処理） |
| `POST` | `/api/conversations/{id}/tts` | テキスト読み上げ（テキスト→音声変換） |
| `GET` | `/api/conversations/{id}` | 会話履歴取得 |
| `DELETE` | `/api/conversations/{id}` | 会話終了 |

## 🏗️ フロントエンドアーキテクチャ（リファクタリング済み）

### 改善された状態管理システム

フロントエンドは段階的リファクタリングを完了し、保守性と拡張性が大幅に向上しました。

#### Phase 1-4 リファクタリング成果

**Phase 1: フック分割** ✅
- 732行の巨大`useVoiceChat`フックを5つの専用フックに分割
- 単一責務原則の適用により、各フックが特定の機能に特化
- テスト可能性の向上とデバッグの容易化

**Phase 2: 型安全性強化** ✅  
- Union Typesによる厳密な状態定義
- 不正な状態組み合わせをコンパイル時に防止
- 構造化されたエラー管理システム

**Phase 3: useEffect最適化** ✅
- 複雑な依存関係を持つuseEffectを単一責務に分割
- メモリリークの防止とクリーンアップ処理の完備
- パフォーマンス向上（不要な再レンダリング防止）

**Phase 4: Zustand状態管理** ✅
- 分散した状態管理を統合・一元化
- Redux DevToolsサポートによるデバッグ体験向上
- セレクターパターンによるパフォーマンス最適化

#### アーキテクチャ構成

```typescript
// 分割されたフック構造
useVoiceChat (統合フック)
├── useVoiceConnection    // WebSocket接続管理
├── useVoiceRecording      // 音声録音制御
├── useVoicePlayback       // 音声再生制御
├── useConversationFlow    // 会話フロー管理
└── useVADIntegration      // Voice Activity Detection

// Zustand状態管理
stores/
├── useReceptionStore      // Reception画面の状態
│   ├── sessionId
│   ├── isGreeting
│   ├── showCountdown
│   └── inputMode
└── useVoiceStore          // 音声チャットの状態
    ├── connectionState
    ├── recordingState
    ├── playbackState
    └── messages

// 厳密な型定義
type ValidVoiceState = 
  | { phase: 'idle', connection: 'disconnected' }
  | { phase: 'greeting', connection: 'connected', recording: 'idle' }
  | { phase: 'active', connection: 'connected', recording: 'idle' | 'recording' }
```

#### 主要な改善効果

- **保守性**: コードの可読性が大幅向上（各フック200行以内）
- **テスト性**: 49個の包括的テストすべて通過
- **型安全性**: TypeScript型チェックによる実行時エラー防止
- **パフォーマンス**: 最適化されたレンダリングサイクル
- **開発体験**: 明確な責務分離とデバッグツールサポート

### フロントエンド状態管理アーキテクチャ

```mermaid
graph TB
    subgraph "UI Components"
        Reception[ReceptionPage<br/>受付画面]
        Voice[VoiceInterface<br/>音声UI]
        Button[ReceptionButton<br/>開始ボタン]
        Display[ConversationDisplay<br/>会話表示]
        Visualizer[AudioVisualizer<br/>音声可視化]
    end
    
    subgraph "Zustand Stores"
        ReceptionStore[useReceptionStore<br/>画面状態管理]
        VoiceStore[useVoiceStore<br/>音声状態管理]
        
        subgraph "Reception State"
            SessionId[sessionId]
            IsGreeting[isGreeting]
            ShowCountdown[showCountdown]
            InputMode[inputMode]
        end
        
        subgraph "Voice State"
            ConnectionState[connectionState]
            RecordingState[recordingState]
            PlaybackState[playbackState]
            Messages[messages]
        end
    end
    
    subgraph "Custom Hooks Layer"
        VoiceChat[useVoiceChat<br/>統合フック]
        
        subgraph "Specialized Hooks"
            Connection[useVoiceConnection<br/>WebSocket管理]
            Recording[useVoiceRecording<br/>録音制御]
            Playback[useVoicePlayback<br/>再生制御]
            Conversation[useConversationFlow<br/>会話フロー]
            VAD[useVADIntegration<br/>音声検出]
        end
        
        subgraph "Effect Hooks"
            MsgHandlers[useVoiceMessageHandlers<br/>メッセージ処理]
            AutoStart[useVoiceAutoStart<br/>自動開始]
            Greeting[useGreetingMode<br/>挨拶モード]
        end
    end
    
    subgraph "External Services"
        WebSocketClient[WebSocket Client<br/>リアルタイム通信]
        AudioRecorder[Audio Recorder<br/>音声録音]
        APIClient[API Client<br/>REST通信]
    end
    
    Reception --> ReceptionStore
    Voice --> VoiceChat
    Button --> ReceptionStore
    Display --> VoiceChat
    Visualizer --> VAD
    
    ReceptionStore --> SessionId
    ReceptionStore --> IsGreeting
    ReceptionStore --> ShowCountdown
    ReceptionStore --> InputMode
    
    VoiceStore --> ConnectionState
    VoiceStore --> RecordingState
    VoiceStore --> PlaybackState
    VoiceStore --> Messages
    
    VoiceChat --> Connection
    VoiceChat --> Recording
    VoiceChat --> Playback
    VoiceChat --> Conversation
    VoiceChat --> VAD
    
    VoiceChat --> MsgHandlers
    VoiceChat --> AutoStart
    VoiceChat --> Greeting
    
    Connection --> WebSocketClient
    Recording --> AudioRecorder
    Conversation --> APIClient
    
    style ReceptionStore fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    style VoiceStore fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    style VoiceChat fill:#fff3e0,stroke:#e65100,stroke-width:3px
```

### 状態フロー図

```mermaid
stateDiagram-v2
    [*] --> Idle: 初期状態
    
    Idle --> SystemCheck: ページロード
    SystemCheck --> Ready: システム正常
    SystemCheck --> Error: システムエラー
    
    Ready --> Greeting: 受付開始ボタン
    
    Greeting --> Connected: WebSocket接続
    Connected --> GreetingPlaying: 挨拶音声再生
    GreetingPlaying --> WaitingInput: 挨拶完了
    
    WaitingInput --> Recording: 録音開始
    Recording --> Processing: 録音停止
    Processing --> Playing: AI応答再生
    Playing --> WaitingInput: 再生完了
    
    WaitingInput --> Completed: 会話完了
    Playing --> Completed: 最終応答
    
    Completed --> Countdown: カウントダウン開始
    Countdown --> Idle: リセット
    
    Error --> Idle: 再試行
    
    note right of Recording
        VADによる自動停止
        または手動停止
    end note
    
    note right of Processing
        音声→テキスト変換
        AI処理中
    end note
    
    note right of Countdown
        5秒カウントダウン後
        自動的に初期画面へ
    end note
```

### データフロー図

```mermaid
flowchart LR
    subgraph "User Actions"
        Start[開始ボタン]
        Speak[音声入力]
        Type[テキスト入力]
    end
    
    subgraph "Zustand Actions"
        SetSession[setSessionId]
        SetGreeting[setIsGreeting]
        SetRecording[setRecordingState]
        AddMessage[addMessage]
    end
    
    subgraph "Side Effects"
        WSConnect[WebSocket接続]
        AudioCapture[音声キャプチャ]
        APICall[API呼び出し]
        TTSPlay[音声再生]
    end
    
    subgraph "State Updates"
        StoreUpdate[Store更新]
        UIRender[UI再レンダリング]
    end
    
    Start --> SetSession
    Start --> SetGreeting
    
    Speak --> SetRecording
    Speak --> AudioCapture
    
    Type --> AddMessage
    Type --> APICall
    
    SetSession --> WSConnect
    SetRecording --> AudioCapture
    AddMessage --> StoreUpdate
    
    WSConnect --> StoreUpdate
    AudioCapture --> APICall
    APICall --> AddMessage
    APICall --> TTSPlay
    
    TTSPlay --> StoreUpdate
    StoreUpdate --> UIRender
    
    style StoreUpdate fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px
    style UIRender fill:#ffecb3,stroke:#f57c00,stroke-width:2px
```

## 🔄 実装済み音声機能

**Step1で音声機能が実装済み**：基本的な音声入出力機能が完成しています：

```python
# 実装済み: AudioService
class AudioService(MessageProcessor):
    async def process_input(self, audio_data: bytes) -> str:
        # ✅ Whisper API実装済み: 音声 → テキスト変換
        
    async def generate_output(self, text: str) -> bytes:
        # ✅ OpenAI TTS実装済み: テキスト → 音声変換

# 実装済み: REST API音声エンドポイント
POST /api/conversations/{id}/voice    # 音声入力
POST /api/conversations/{id}/tts      # 音声出力

# 実装済み: フロントエンド音声UI
- 音声録音・再生機能
- 入力方式切り替えボタン  
- 音声フィードバック
```

## 🔄 Step2拡張計画

今後の高度な音声機能拡張予定：

```python
# 拡張ポイント1: WebSocket対応
# REST API → WebSocket API (リアルタイム音声ストリーミング)

# 拡張ポイント2: 高度な音声処理
- ノイズキャンセリング
- 複数話者対応
- 音声認識信頼度スコア

# 拡張ポイント3: UI/UX向上
- 音声可視化（波形表示）
- 音声コマンド対応
- 多言語音声対応
```

## 🚀 本番デプロイ

### Vercel デプロイ

1. **環境変数設定**
   ```bash
   # Vercel環境変数として設定
   - OPENAI_API_KEY
   - GOOGLE_SERVICE_ACCOUNT_KEY  
   - SLACK_WEBHOOK_URL
   - MEETING_ROOM_CALENDAR_IDS
   ```

2. **デプロイ実行**
   ```bash
   # Vercel CLI使用
   npm i -g vercel
   vercel

   # または GitHub連携でCD設定
   ```

### 手動デプロイ

```bash
# フロントエンドビルド
cd frontend && npm run build

# バックエンド起動 (例: Docker)
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 🐛 トラブルシューティング

### よくある問題

**1. Google Calendar API エラー**
```bash
# サービスアカウント権限確認
# カレンダー共有設定確認
# GOOGLE_SERVICE_ACCOUNT_KEY形式確認 (JSON文字列)
```

**2. OpenAI API エラー**
```bash
# API キーの確認
# クォータ・請求設定確認
```

**3. フロントエンドビルドエラー**
```bash
# Node.js バージョン確認 (18+ 必要)
# npm install 再実行
# package-lock.json 削除後再インストール
```

**4. Python依存関係エラー**
```bash
# 仮想環境がアクティブか確認
which python  # /path/to/ai-reception/venv/bin/python が表示されるべき

# 仮想環境をアクティベート
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

# Python バージョン確認 (3.11+ 推奨)
python --version

# pip のアップグレード
python -m pip install --upgrade pip

# 依存関係の再インストール
pip install -r backend/requirements.txt --no-cache-dir
```

### ログ確認

```bash
# バックエンドログ（仮想環境内で実行）
cd backend && python app/main.py
# コンソール出力でエラー確認

# フロントエンドログ  
cd frontend && npm run dev
# ブラウザ Developer Tools で確認
```

## 🔄 システムアーキテクチャ

### 全体構成図

```mermaid
graph TB
    subgraph "Frontend (Next.js)"
        UI[Reception UI<br/>タブレット最適化]
        API_Client[API Client<br/>Axios]
    end
    
    subgraph "Backend (FastAPI)"
        REST[REST API<br/>エンドポイント]
        
        subgraph "LangGraph Agent"
            Start[開始]
            Greeting[挨拶]
            CollectInfo[情報収集]
            Confirmation[確認]
            CalendarCheck[予約確認]
            Guidance[案内]
            Error[エラー処理]
            End[終了]
        end
        
        subgraph "Services"
            CalendarService[Calendar Service<br/>Google Calendar API]
            SlackService[Slack Service<br/>Webhook通知]
            LLMService[LLM Service<br/>OpenAI GPT-4]
            AudioService[Audio Service<br/>Whisper + TTS]
        end
    end
    
    subgraph "External Services"
        Google[Google Calendar]
        Slack[Slack]
        OpenAI[OpenAI API]
    end
    
    UI <--> API_Client
    API_Client <--> REST
    REST <--> Start
    
    CalendarCheck --> CalendarService
    Guidance --> SlackService
    CollectInfo --> LLMService
    Confirmation --> LLMService
    CollectInfo --> AudioService
    Guidance --> AudioService
    
    CalendarService <--> Google
    SlackService --> Slack
    LLMService <--> OpenAI
    AudioService <--> OpenAI
```

### ユーザーフロー図（専用ガイダンスノード対応）

```mermaid
flowchart TD
    Start([来客者がタブレットに向かう])
    
    Start --> Greeting[AIが挨拶]
    Greeting --> InputChoice{入力方式選択}
    
    InputChoice -->|テキスト| TextInput[テキスト入力]
    InputChoice -->|音声| VoiceInput[音声入力・変換]
    
    TextInput --> InfoExtract{情報抽出}
    VoiceInput --> InfoExtract
    
    InfoExtract --> DeliveryCheck{🚚 AI配達判定}
    
    DeliveryCheck -->|はい| DeliveryGuidance[配達専用案内<br/>迅速対応]
    DeliveryCheck -->|いいえ| InfoComplete{情報完備？}
    
    InfoComplete -->|はい| Confirm[情報確認]
    InfoComplete -->|いいえ| AskMore[追加情報要求]
    
    AskMore --> InputChoice2{入力方式選択}
    InputChoice2 -->|テキスト| TextInput2[テキスト入力]
    InputChoice2 -->|音声| VoiceInput2[音声入力・変換]
    TextInput2 --> InfoExtract
    VoiceInput2 --> InfoExtract
    
    Confirm --> UserConfirm{来客者が確認}
    UserConfirm -->|正しい| TypeCheck{AI訪問タイプ判定}
    UserConfirm -->|修正必要| Correction[情報修正]
    Correction --> InputChoice
    
    TypeCheck -->|appointment| CalendarCheck[カレンダー確認]
    TypeCheck -->|sales| SalesGuidance[営業専用案内<br/>丁寧なお断り]
    TypeCheck -->|delivery| DeliveryGuidance2[配達専用案内<br/>フォールバック]
    
    CalendarCheck --> AppointmentGuidance[予約専用案内<br/>カレンダー結果対応]
    
    DeliveryGuidance --> OutputChoice{出力方式}
    SalesGuidance --> OutputChoice
    DeliveryGuidance2 --> OutputChoice
    AppointmentGuidance --> OutputChoice
    
    OutputChoice -->|テキスト表示| TextOutput[テキスト表示]
    OutputChoice -->|音声読み上げ| TTSOutput[TTS音声出力]
    
    TextOutput --> SlackNotify[Slack通知]
    TTSOutput --> SlackNotify
    
    SlackNotify --> End([対応完了])
    
    style DeliveryCheck fill:#ffcccc,stroke:#ff0000,stroke-width:3px
    style DeliveryGuidance fill:#ffe6e6,stroke:#ff0000,stroke-width:2px
    style SalesGuidance fill:#e6f3ff,stroke:#0066cc,stroke-width:2px
    style AppointmentGuidance fill:#e6ffe6,stroke:#00cc66,stroke-width:2px
```

## 🧪 LLMテストフレームワーク

### テスト概要

AI受付システムの品質を保証するための包括的なLLMテストフレームワークを実装しています。

```mermaid
graph LR
    subgraph "テストカテゴリ"
        APT[予約来客<br/>APT]
        SALES[営業訪問<br/>SALES]
        DEL[配達業者<br/>DEL]
        ERR[エラー処理<br/>ERR]
        COMP[複雑ケース<br/>COMP]
    end
    
    subgraph "テストフレームワーク"
        Runner[LLMTestRunner<br/>実行エンジン]
        Validator[DetailedValidator<br/>検証エンジン]
        Analyzer[AnalysisEngine<br/>分析エンジン]
        Reporter[TestReportGenerator<br/>レポート生成]
    end
    
    subgraph "評価指標"
        Extract[情報抽出精度]
        Quality[応答品質]
        Flow[会話フロー]
        Keyword[キーワード一致]
    end
    
    APT --> Runner
    SALES --> Runner
    DEL --> Runner
    ERR --> Runner
    COMP --> Runner
    
    Runner --> Validator
    Validator --> Extract
    Validator --> Quality
    Validator --> Flow
    Validator --> Keyword
    
    Validator --> Analyzer
    Analyzer --> Reporter
```

### テスト実行方法

```bash
# 仮想環境をアクティベート
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

# 全てのテスト実行（推奨）
cd backend
pytest tests/ -v  # 111個の包括的テスト

# レセプションフローテスト
pytest tests/test_reception_graph.py -v  # 21個のコアフローテスト

# 専用ノードアーキテクチャテスト（新規）
pytest tests/test_specialized_nodes_integration.py -v  # 7個の専用ノードテスト

# AI訪問者タイプ判定テスト（新規）
pytest tests/test_visitor_type_ai.py -v  # 7個のAI判定テスト

# 配達ショートカットテスト（新規）
pytest tests/test_delivery_shortcut.py -v  # 8個のショートカットテスト

# LLM統合テスト
pytest tests/test_llm_integration.py -v  # AI応答品質テスト

# 音声機能テスト  
pytest tests/test_audio_service.py -v  # Whisper + TTS テスト

# API機能テスト
pytest tests/test_conversation_api.py -v  # REST API テスト

# カレンダー統合テスト
pytest tests/test_calendar_service.py -v  # Google Calendar テスト
```

### テストシナリオ

| カテゴリ | シナリオID | 説明 | 成功率基準 |
|---------|-----------|------|-----------|
| **APT** | APT-001 | 標準的な予約来客 | 65%以上 |
| | APT-002 | 時間指定なしの予約 | |
| | APT-003 | 予約が見つからない | |
| **SALES** | SALES-001 | 標準的な営業訪問 | 33%以上 |
| | SALES-002 | 商品紹介での営業 | |
| | SALES-003 | 曖昧な営業表現 | |
| **DEL** | DEL-001 | 標準的な配達 | 50%以上 |
| | DEL-002 | 個人名なしの配達 | |
| **ERR** | ERR-001 | 情報不足エラー | 33%以上 |
| | ERR-002 | 情報訂正フロー | |
| | ERR-003 | 部分的な情報提供 | |
| **COMP** | COMP-001 | 複数の用件 | 50%以上 |
| | COMP-002 | 敬語なしの来客 | |
| | COMP-003 | 長い説明の来客 | |

### 評価メトリクス

- **情報抽出精度**: 名前、会社名、訪問タイプの正確な抽出
- **応答品質**: 丁寧さ、明確さ、適切性
- **会話フロー**: 状態遷移の正確性（21個のフローテスト全て成功）
- **キーワード一致**: 必須キーワードの含有（柔軟なマッチング対応）
- **音声処理精度**: Whisper音声認識とTTS音声合成の品質
- **API安定性**: REST APIエンドポイントの信頼性

## 📖 開発者向け情報

### アーキテクチャ決定

- **LangGraph**: 会話フロー管理（AI状態遷移エンジン）
- **FastAPI**: 高性能非同期API（REST + 音声処理）
- **NextJS 15**: モダンReactフレームワーク（App Router使用）
- **TypeScript**: 型安全性（フロントエンド・バックエンド共通）
- **Tailwind CSS**: ユーティリティファーストCSS
- **OpenAI APIs**: GPT-4 + Whisper + TTS統合
- **Google Calendar API**: 予約管理統合
- **Slack Webhooks**: リアルタイム通知

### LangGraphフロー詳細（専用ガイダンスノード対応）

```mermaid
stateDiagram-v2
    [*] --> greeting: 開始
    
    greeting --> collect_all_info: 挨拶完了
    
    collect_all_info --> delivery_shortcut: 🚚 AI配達検出
    collect_all_info --> confirmation_response: 通常フロー（情報完備）
    collect_all_info --> collect_all_info: 情報不足（最大3回）
    collect_all_info --> error: エラー上限到達
    
    delivery_shortcut --> delivery_guidance: 配達専用ノード
    delivery_guidance --> send_slack_notification: 配達完了
    
    confirmation_response --> confirmation_check: 確認応答
    
    confirmation_check --> visitor_type_check: 確認OK
    confirmation_check --> collect_all_info: 修正必要
    
    visitor_type_check --> appointment_flow: AI判定: appointment
    visitor_type_check --> sales_guidance: AI判定: sales
    visitor_type_check --> delivery_guidance: AI判定: delivery（フォールバック）
    
    appointment_flow --> calendar_check: カレンダー確認
    calendar_check --> appointment_guidance: 予約専用ノード
    
    appointment_guidance --> send_slack_notification: 予約完了
    sales_guidance --> send_slack_notification: 営業完了
    
    send_slack_notification --> log_completion
    log_completion --> [*]: 完了
    
    error --> [*]: エラー終了
    
    note right of delivery_shortcut
        配達業者は確認をスキップし
        直接専用案内へ
    end note
    
    note right of visitor_type_check
        AI判定による
        専用ノードルーティング
    end note
```

### 拡張ガイド

**新しい専用ガイダンスノード追加**:
```python
# backend/app/agents/nodes.py に追加
async def new_visitor_type_guidance_node(self, state: ConversationState) -> ConversationState:
    """新しい訪問者タイプ専用の案内ノード"""
    visitor_info = state.get("visitor_info") or {}
    
    # タイプ固有の処理ロジック
    guidance_message = f"新しいタイプ向けの専用メッセージ"
    
    ai_message = AIMessage(content=guidance_message)
    print(f"🎯 New type guidance completed")
    
    return {
        **state,
        "messages": [ai_message],
        "current_step": "complete"
    }
```

**AI訪問者判定拡張**:
```python
# AI判定ロジックに新しいタイプを追加
async def _ai_determine_visitor_type(self, purpose: str, visitor_info: dict) -> str:
    # 新しいタイプの判定ロジックを追加
    if "新しい条件" in purpose.lower():
        return "new_type"
    # 既存の判定ロジック継続
```

**新しいAPI追加**:
```python  
# backend/app/api/ に新しいルーターファイル作成
# main.py で include_router
```

**新しいコンポーネント追加**:
```tsx
// frontend/components/ に新しいコンポーネント作成
// TypeScript + Tailwind CSS使用
```

## 📞 サポート

- **Issue報告**: GitHubリポジトリのIssue機能
- **機能要望**: PRsまたはIssue 
- **技術質問**: 開発者ドキュメント参照

---

## 📝 更新履歴

### v1.3.0 (2025-08-09)
- 🏗️ **フロントエンド大規模リファクタリング完了**
  - Phase 1: 732行の`useVoiceChat`フックを5つの専用フックに分割
  - Phase 2: Union Typesによる型安全性強化
  - Phase 3: useEffect依存関係の最適化
  - Phase 4: Zustand導入による状態管理統合
- ✅ **品質改善**
  - 全49個のフロントエンドテスト通過
  - TypeScript型チェック強化
  - メモリリーク防止処理実装
  - パフォーマンス最適化

### v1.2.0 (2025-08-08)
- 🚚 **配達ショートカット機能追加**
  - AI早期配達検出による迅速対応
  - 専用ガイダンスノードアーキテクチャ実装
- 🎯 **AI訪問者タイプ判定システム**
  - 予約来客、営業訪問、配達業者の自動判定
  - タイプ別最適化案内

### v1.1.0 (2025-08-07)
- 🎙️ **音声機能実装**
  - Whisper API統合（音声→テキスト）
  - OpenAI TTS統合（テキスト→音声）
  - WebSocket音声ストリーミング対応
- 📱 **音声UI実装**
  - ボリューム反応マイクUI
  - 音声可視化コンポーネント
  - VAD（Voice Activity Detection）統合

### v1.0.0 (2025-08-06)
- 🎉 **初回リリース**
  - LangGraphベースAI受付システム
  - Google Calendar統合
  - Slack通知機能
  - タブレット最適化UI

## 📜 ライセンス

MIT License - 詳細は`LICENSE`ファイルを参照

---

**AI Reception System v1.3.0 - Frontend Architecture Refactored ✅**

### 🎉 新機能ハイライト

- **🎙️ 音声入力対応**: Whisper APIによる高精度音声認識
- **🔊 音声出力対応**: OpenAI TTSによる自然な音声合成  
- **🔄 入力方式切り替え**: テキスト・音声の動的切り替え
- **📱 音声UI**: 直感的な音声録音・再生インターフェース
- **🤖 AIフロー**: LangGraphによる堅牢な会話状態管理
- **🚚 配達ショートカット**: AI早期検出による迅速な配達対応
- **🎯 専用ガイダンスノード**: 訪問者タイプ別最適化案内システム
- **🏗️ リファクタリング完了**: フロントエンド4段階改善実施
- **📦 Zustand統合**: 状態管理の一元化と最適化
- **🧪 テスト完全対応**: 111個の包括的テスト全て成功
  - 21個のレセプションフローテスト（状態遷移完全検証）
  - 7個の専用ノードアーキテクチャテスト（新規）
  - 7個のAI訪問者タイプ判定テスト（新規）
  - 8個の配達ショートカットテスト（新規）
  - 17個の音声機能テスト（Whisper + TTS品質保証）
  - 11個のカレンダー統合テスト（Google API連携）
  - 15個のAPI機能テスト（REST エンドポイント検証）
  - 25個のその他統合テスト（LLM品質・エラーハンドリング等）

### 🔧 技術仕様

- **フロントエンド**: Next.js 15 + TypeScript + Tailwind CSS
- **バックエンド**: FastAPI + LangGraph + Python 3.11+
- **AI統合**: OpenAI GPT-4 + Whisper + TTS
- **外部連携**: Google Calendar API + Slack Webhooks
- **品質保証**: 111個のテスト（専用ノードアーキテクチャ対応・カバレッジ100%達成）

**次回更新**: Step2でのWebSocket対応とリアルタイム音声ストリーミング機能
