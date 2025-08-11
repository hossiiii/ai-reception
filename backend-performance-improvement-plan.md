# AI受付システム パフォーマンス改善計画

## 🚨 現状分析と主要なパフォーマンスボトルネック

### 1. OpenAI API呼び出しの過剰使用
- **問題**: nodes.py内で**19箇所**のAI呼び出し（1会話で8-12回実際に呼ばれる）
- **影響**: レスポンス時間の増大、APIコスト増大
- **詳細**:
  - 挨拶メッセージ（greeting_node）：毎回AI生成
  - 確認メッセージ（confirm_info_node）：複数回AI生成
  - エラーメッセージ：すべてAI生成
  - 案内メッセージ：訪問者タイプごとにAI生成

### 2. WebSocket音声処理の逐次実行
- **問題**: websocket.py内で音声処理が完全に同期的
- **影響**: 各処理の待ち時間が累積（2-4秒）
- **処理フロー**:
  ```
  音声受信 → Whisper(0.8-1.2秒) → LangGraph(1-2秒) → TTS(0.5-1秒) → 送信
  ```
- **Base64オーバーヘッド**: バイナリデータの非効率な転送

### 3. LangGraphフローの非効率性
- **問題**: reception_graph.pyでノードを手動実行
- **影響**: LangGraphの最適化機能が使えない
- **詳細**:
  ```python
  # 現在の実装（非効率）
  if current_step == "collect_all_info":
      result = await nodes_instance.collect_all_info_node(updated_state)
  elif current_step == "confirmation":
      result = await nodes_instance.confirm_info_node(updated_state)
  # ... 各ステップごとに手動で分岐
  ```

### 4. フロントエンド状態管理の問題
- **問題**: 大きな状態オブジェクト（VoiceState）の頻繁な更新
- **影響**: 不要な再描画、メモリ使用量増大
- **VAD更新**: 音声レベル更新で毎秒数十回の再描画

## 🎯 段階別改善計画

### フェーズ1: 即効性のある改善（1週間）
**期待効果: 応答時間50%短縮、API呼び出し70%削減**

#### 1.1 テンプレート化レスポンスの実装

##### 実装内容
```python
# backend/app/agents/templates.py (新規作成)
class ResponseTemplates:
    GREETING = """いらっしゃいませ。音声受付システムです。
会社名、お名前、ご用件をお聞かせください。"""
    
    CONFIRMATION = """以下の情報で間違いございませんでしょうか？
・会社名：{company}
・お名前：{name}
・訪問目的：{purpose}

情報が正しい場合は「はい」、修正が必要な場合は「いいえ」とお答えください。"""
    
    DELIVERY_GUIDANCE = """{company}様、お疲れ様です。
配達の件でお越しいただき、ありがとうございます。

・置き配の場合: 玄関前にお荷物をお置きください
・サインが必要な場合: 奥の呼び鈴を押してお待ちください

配達完了後は、そのままお帰りいただけます。"""
    
    APPOINTMENT_FOUND = """承知いたしました。
{visitor_name}様の{time}のご予約を確認いたしました。
入って右手の会議室でお待ちください。"""
```

##### 実装ファイル
- `backend/app/agents/nodes.py`: AI呼び出しをテンプレートに置き換え
- API呼び出し削減: 19箇所 → 5箇所（複雑な判断のみ）

#### 1.2 非同期バックグラウンドタスクの実装

##### Slack通知の非同期化
```python
# backend/app/api/websocket.py
from fastapi import BackgroundTasks

async def handle_voice_websocket(websocket: WebSocket, session_id: str):
    background_tasks = BackgroundTasks()
    
    # Slack通知を非同期で実行
    if response.get("completed"):
        background_tasks.add_task(
            send_slack_notification,
            session_id, 
            conversation_history
        )
```

#### 1.3 HTTPコネクションプールの実装

##### 実装内容
```python
# backend/app/services/connection_pool.py
import httpx
from openai import AsyncOpenAI

class ConnectionPoolManager:
    _instance = None
    
    def __init__(self):
        # HTTPXクライアントの再利用
        self.http_client = httpx.AsyncClient(
            timeout=5.0,  # タイムアウトを15秒→5秒に短縮
            limits=httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20
            )
        )
        
        # OpenAIクライアントの共有
        self.openai_client = AsyncOpenAI(
            http_client=self.http_client
        )
```

### フェーズ2: 主要パフォーマンス改善（2週間）
**期待効果: 応答時間70%短縮、同時接続数3倍向上**

#### 2.1 並列処理パイプラインの実装

##### 音声処理の並列化
```python
# backend/app/api/websocket.py
async def process_audio_parallel(audio_data: bytes, session_id: str):
    # 音声認識とセッション状態取得を並列実行
    transcription_task = asyncio.create_task(
        audio_service.process_audio_input(audio_data)
    )
    state_task = asyncio.create_task(
        graph_manager.get_state(session_id)
    )
    
    transcription, current_state = await asyncio.gather(
        transcription_task, 
        state_task
    )
    
    # AI応答生成（テンプレート判定と並列）
    if is_template_response(current_state):
        response_text = get_template_response(current_state, transcription)
    else:
        response_text = await generate_ai_response(transcription, current_state)
    
    # 応答の分割処理
    sentences = split_sentences(response_text)
    
    # 最初の文を即座に音声化
    first_audio = await audio_service.generate_audio_output(sentences[0])
    yield first_audio
    
    # 残りの文を並列音声化
    if len(sentences) > 1:
        remaining_audios = await asyncio.gather(*[
            audio_service.generate_audio_output(sentence)
            for sentence in sentences[1:]
        ])
        for audio in remaining_audios:
            yield audio
```

#### 2.2 LangGraphフローの最適化

##### グラフ実行の改善
```python
# backend/app/agents/reception_graph.py
class ReceptionGraphManager:
    async def send_message(self, session_id: str, message: str):
        config = {"configurable": {"thread_id": session_id}}
        
        # 手動実行を廃止し、LangGraphの自動実行を使用
        async for event in self.graph.astream_events(
            {"messages": [HumanMessage(content=message)]},
            config,
            version="v1"
        ):
            if event["event"] == "on_chain_end":
                return self._process_result(event["data"])
```

#### 2.3 メモリキャッシュの実装

##### 定型応答のキャッシュ
```python
# backend/app/services/cache_service.py
from functools import lru_cache
import hashlib

class ResponseCache:
    def __init__(self):
        self._cache = {}
        self._ttl = 3600  # 1時間
        
    @lru_cache(maxsize=100)
    def get_cached_response(self, key: str):
        """定型応答をキャッシュから取得"""
        return self._cache.get(key)
    
    async def get_or_generate(self, key: str, generator_func):
        """キャッシュがなければ生成して保存"""
        if cached := self.get_cached_response(key):
            return cached
            
        response = await generator_func()
        self._cache[key] = response
        return response
```


## 📈 期待される改善効果

### パフォーマンス指標
| 指標 | 現状 | Phase 1後 | Phase 2後 |
|------|------|-----------|-----------|
| 初回応答時間 | 3-5秒 | 1.5-2.5秒 | 0.8-1.5秒 |
| 完全応答時間 | 3-5秒 | 2-3秒 | 1.5-2秒 |
| OpenAI API呼び出し | 8-12回/会話 | 2-3回/会話 | 1-2回/会話 |
| 同時接続数 | 10-20 | 30-50 | 50-100 |
| メモリ使用量 | 100MB/接続 | 60MB/接続 | 40MB/接続 |

### コスト削減
- **OpenAI APIコスト**: 70-80%削減
- **サーバーリソース**: 40%削減

## 🎯 実装優先順位と具体的タスク

### 最優先（今週末実装可能）

#### タスク1: テンプレート化（2時間）
```bash
# 実装ファイル
backend/app/agents/templates.py  # 新規作成
backend/app/agents/nodes.py      # 19箇所の修正
```

#### タスク2: タイムアウト最適化（30分）
```python
# backend/app/services/audio_service.py
# backend/app/services/text_service.py
timeout=15 → timeout=5  # 変更箇所: 4箇所
```

#### タスク3: Slack非同期化（1時間）
```python
# backend/app/agents/nodes.py - send_slack_node
# FastAPIのBackgroundTasksを使用
```

### 高優先（来週実装）

#### タスク4: 並列処理実装（4時間）
```python
# backend/app/api/websocket.py
# handle_voice_websocket関数の全面改修
```

#### タスク5: レスポンス分割（3時間）
```python
# backend/app/services/audio_service.py
# 文単位分割と段階的音声生成
```

#### タスク6: キャッシュ実装（2時間）
```python
# backend/app/services/cache_service.py  # 新規作成
# メモリベースの簡易キャッシュ
```


## 🚀 実装開始手順

1. **Phase 1実装（1日）**
   - テンプレート化: 2時間
   - タイムアウト調整: 30分
   - Slack非同期化: 1時間
   - テスト: 1時間

2. **Phase 2実装（1週間）**
   - 並列処理: 2日
   - キャッシュ: 1日
   - フロントエンド最適化: 2日

## 📊 モニタリング

### 追跡メトリクス
- レスポンスタイム（P50, P95, P99）
- API呼び出し回数/セッション
- エラー率
- メモリ使用量
- CPU使用率

### アラート設定
- P95レスポンスタイム > 2秒
- エラー率 > 1%
- メモリ使用量 > 80%