"""
OpenAI Realtime API専用音声処理エンジン

このモジュールは以下の機能を提供:
1. OpenAI Realtime APIとのWebSocket接続管理
2. リアルタイム音声ストリーミング処理
3. Function Callsを使ったLangGraphブリッジ連携
4. コスト追跡とレート制限管理
"""

import asyncio
import json
import time
import base64
import websockets
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field
from enum import Enum

from ...config.realtime_settings import RealtimeSettings


class RealtimeSessionState(Enum):
    """Realtimeセッション状態"""
    INITIALIZING = "initializing"
    CONNECTED = "connected"
    STREAMING = "streaming"
    FUNCTION_CALLING = "function_calling"
    ERROR = "error"
    DISCONNECTED = "disconnected"


@dataclass
class RealtimeSession:
    """Realtimeセッション管理"""
    session_id: str
    websocket: Optional[websockets.WebSocketServerProtocol] = None
    state: RealtimeSessionState = RealtimeSessionState.INITIALIZING
    start_time: float = field(default_factory=time.time)
    cost_usd: float = 0.0
    message_count: int = 0
    pending_functions: Dict[str, Dict] = field(default_factory=dict)


class RealtimeAudioProcessor:
    """OpenAI Realtime API音声処理エンジン"""

    def __init__(self):
        self.settings = RealtimeSettings()
        self.active_sessions: Dict[str, RealtimeSession] = {}
        
        # Realtime API接続設定
        self.realtime_url = "wss://api.openai.com/v1/realtime"
        self.api_headers = {
            "Authorization": f"Bearer {self.settings.realtime_api_key}",
            "OpenAI-Beta": "realtime=v1"
        }
        
        print("✅ RealtimeAudioProcessor initialized")

    async def health_check(self) -> bool:
        """Realtime API利用可能性チェック"""
        try:
            # シンプルな接続テスト
            async with websockets.connect(
                self.realtime_url,
                extra_headers=self.api_headers,
                timeout=5
            ) as websocket:
                # セッション初期化メッセージ
                init_message = {
                    "type": "session.update",
                    "session": {
                        "modalities": ["text", "audio"],
                        "instructions": "You are a helpful assistant.",
                        "voice": "alloy",
                        "input_audio_format": "pcm16",
                        "output_audio_format": "pcm16",
                        "input_audio_transcription": {
                            "model": "whisper-1"
                        }
                    }
                }
                await websocket.send(json.dumps(init_message))
                
                # 応答を待機
                response = await asyncio.wait_for(websocket.recv(), timeout=3)
                response_data = json.loads(response)
                
                # 正常な応答かチェック
                return response_data.get("type") == "session.updated"
                
        except Exception as e:
            print(f"❌ Realtime API health check failed: {e}")
            return False

    async def initialize_session(self, session_id: str) -> Dict[str, Any]:
        """Realtimeセッション初期化"""
        try:
            # 既存セッションクリーンアップ
            if session_id in self.active_sessions:
                await self.cleanup_session(session_id)
            
            # 新しいセッション作成
            session = RealtimeSession(session_id=session_id)
            self.active_sessions[session_id] = session
            
            # WebSocket接続確立
            session.websocket = await websockets.connect(
                self.realtime_url,
                extra_headers=self.api_headers,
                timeout=10
            )
            
            # セッション設定
            session_config = {
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "instructions": self._get_reception_instructions(),
                    "voice": "alloy",
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "input_audio_transcription": {
                        "model": "whisper-1"
                    },
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 500
                    },
                    "tools": self._get_langgraph_tools()
                }
            }
            
            await session.websocket.send(json.dumps(session_config))
            
            # 初期化応答を待機
            response = await asyncio.wait_for(session.websocket.recv(), timeout=5)
            response_data = json.loads(response)
            
            if response_data.get("type") == "session.updated":
                session.state = RealtimeSessionState.CONNECTED
                print(f"✅ Realtime session initialized: {session_id}")
                
                return {
                    "success": True,
                    "session_id": session_id,
                    "capabilities": {
                        "real_time_audio": True,
                        "function_calling": True,
                        "turn_detection": True,
                        "low_latency": True
                    }
                }
            else:
                raise Exception(f"Session initialization failed: {response_data}")
                
        except Exception as e:
            print(f"❌ Realtime session init error: {e}")
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            
            return {
                "success": False,
                "session_id": session_id,
                "error": str(e)
            }

    async def process_audio_stream(self, session_id: str, audio_data: bytes) -> Dict[str, Any]:
        """リアルタイム音声ストリーム処理"""
        if session_id not in self.active_sessions:
            return {"success": False, "error": "Session not found"}
        
        session = self.active_sessions[session_id]
        
        if not session.websocket or session.state not in [RealtimeSessionState.CONNECTED, RealtimeSessionState.STREAMING]:
            return {"success": False, "error": "Session not ready"}
        
        try:
            session.state = RealtimeSessionState.STREAMING
            start_time = time.time()
            
            # 音声データをRealtimeAPIに送信
            audio_message = {
                "type": "input_audio_buffer.append",
                "audio": base64.b64encode(audio_data).decode()
            }
            await session.websocket.send(json.dumps(audio_message))
            
            # 音声入力完了を通知
            commit_message = {"type": "input_audio_buffer.commit"}
            await session.websocket.send(json.dumps(commit_message))
            
            # レスポンス作成開始をリクエスト
            response_create = {
                "type": "response.create",
                "response": {
                    "modalities": ["text", "audio"],
                    "instructions": "Please respond naturally in Japanese as a reception AI."
                }
            }
            await session.websocket.send(json.dumps(response_create))
            
            # 応答を収集
            result = await self._collect_realtime_response(session)
            
            # コスト計算
            processing_time = time.time() - start_time
            estimated_cost = self._calculate_cost(processing_time, len(audio_data))
            session.cost_usd += estimated_cost
            session.message_count += 1
            
            result.update({
                "latency_ms": int(processing_time * 1000),
                "cost": estimated_cost,
                "session_cost_total": session.cost_usd
            })
            
            return result
            
        except Exception as e:
            session.state = RealtimeSessionState.ERROR
            print(f"❌ Realtime streaming error: {e}")
            return {"success": False, "error": str(e)}

    async def _collect_realtime_response(self, session: RealtimeSession) -> Dict[str, Any]:
        """Realtimeレスポンス収集"""
        transcription = ""
        ai_response_text = ""
        audio_chunks = []
        function_calls = []
        
        timeout = 10  # 10秒でタイムアウト
        
        try:
            while True:
                response = await asyncio.wait_for(session.websocket.recv(), timeout=timeout)
                data = json.loads(response)
                
                event_type = data.get("type")
                
                if event_type == "conversation.item.input_audio_transcription.completed":
                    # 音声認識結果
                    transcription = data.get("transcript", "")
                    
                elif event_type == "response.audio.delta":
                    # 音声レスポンスのチャンク
                    if "delta" in data:
                        audio_chunks.append(base64.b64decode(data["delta"]))
                        
                elif event_type == "response.text.delta":
                    # テキストレスポンスのチャンク
                    if "delta" in data:
                        ai_response_text += data["delta"]
                        
                elif event_type == "response.function_call_arguments.delta":
                    # Function Call引数の収集
                    call_id = data.get("call_id")
                    if call_id not in session.pending_functions:
                        session.pending_functions[call_id] = {
                            "name": data.get("name", ""),
                            "arguments": ""
                        }
                    session.pending_functions[call_id]["arguments"] += data.get("delta", "")
                    
                elif event_type == "response.function_call_arguments.done":
                    # Function Call完了
                    call_id = data.get("call_id")
                    if call_id in session.pending_functions:
                        function_call = session.pending_functions[call_id]
                        function_calls.append({
                            "call_id": call_id,
                            "name": function_call["name"],
                            "parameters": json.loads(function_call["arguments"])
                        })
                        
                elif event_type == "response.done":
                    # レスポンス完了
                    break
                    
                elif event_type == "error":
                    # エラー発生
                    raise Exception(f"Realtime API error: {data.get('error', {}).get('message', 'Unknown error')}")
                    
        except asyncio.TimeoutError:
            print(f"⚠️ Realtime response timeout for session {session.session_id}")
        
        # 音声データ結合
        complete_audio = b"".join(audio_chunks) if audio_chunks else b""
        
        # Function Callsが必要かチェック
        requires_langgraph = len(function_calls) > 0
        
        return {
            "success": True,
            "transcription": transcription,
            "ai_response": ai_response_text,
            "audio_data": complete_audio,
            "function_calls": function_calls,
            "requires_langgraph": requires_langgraph,
            "features": ["real_time_audio", "auto_transcription", "low_latency"]
        }

    async def send_function_result(self, session_id: str, function_result: Dict[str, Any]):
        """Function Call結果をRealtimeAPIに送信"""
        if session_id not in self.active_sessions:
            return
        
        session = self.active_sessions[session_id]
        
        if not session.websocket:
            return
        
        try:
            # Function Call結果を送信
            result_message = {
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": function_result.get("call_id"),
                    "output": json.dumps(function_result.get("result", {}))
                }
            }
            
            await session.websocket.send(json.dumps(result_message))
            
            # 新しいレスポンスを生成リクエスト
            response_create = {
                "type": "response.create",
                "response": {
                    "modalities": ["text", "audio"]
                }
            }
            await session.websocket.send(json.dumps(response_create))
            
        except Exception as e:
            print(f"❌ Function result send error: {e}")

    def _get_reception_instructions(self) -> str:
        """受付AI用のインストラクション"""
        return """あなたは日本の企業の受付AIアシスタントです。以下のルールに従って対応してください:

1. 常に丁寧な敬語を使用し、親しみやすく応対する
2. 来客者の名前、会社名、来訪目的を確認する
3. 必要に応じてFunction Callsを使ってシステム機能を実行する
4. 音声での自然な会話を心がけ、聞き取りやすく話す
5. 来客者のタイプ（予約、営業、配達等）を判断して適切に案内する
6. システムエラーの場合は丁寧に謝罪し、代替手段を提案する

あなたは以下の機能を使用できます:
- collect_visitor_info: 来客者情報の収集
- check_appointment: 予約確認
- send_notification: スタッフへの通知
- guide_visitor: 来客者案内"""

    def _get_langgraph_tools(self) -> List[Dict[str, Any]]:
        """LangGraph統合用のFunction Callsツール定義"""
        return [
            {
                "type": "function",
                "name": "collect_visitor_info",
                "description": "来客者の基本情報（名前、会社名、来訪目的）を収集・確認する",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "visitor_name": {
                            "type": "string",
                            "description": "来客者の名前"
                        },
                        "company_name": {
                            "type": "string", 
                            "description": "来客者の会社名"
                        },
                        "purpose": {
                            "type": "string",
                            "description": "来訪目的"
                        }
                    },
                    "required": ["visitor_name"]
                }
            },
            {
                "type": "function",
                "name": "check_appointment",
                "description": "Googleカレンダーで予約を確認する",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "visitor_name": {
                            "type": "string",
                            "description": "確認する来客者の名前"
                        },
                        "date": {
                            "type": "string",
                            "description": "確認する日付 (YYYY-MM-DD形式)"
                        }
                    },
                    "required": ["visitor_name"]
                }
            },
            {
                "type": "function", 
                "name": "send_notification",
                "description": "担当者やスタッフにSlack通知を送信する",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "visitor_info": {
                            "type": "object",
                            "description": "来客者情報"
                        },
                        "message": {
                            "type": "string",
                            "description": "通知メッセージ"
                        }
                    },
                    "required": ["visitor_info", "message"]
                }
            },
            {
                "type": "function",
                "name": "guide_visitor", 
                "description": "来客者に案内情報を提供する",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "visitor_type": {
                            "type": "string",
                            "enum": ["appointment", "sales", "delivery", "other"],
                            "description": "来客者のタイプ"
                        },
                        "location": {
                            "type": "string",
                            "description": "案内先の場所"
                        }
                    },
                    "required": ["visitor_type"]
                }
            }
        ]

    def _calculate_cost(self, processing_time: float, audio_size: int) -> float:
        """コスト計算（概算）"""
        # OpenAI Realtime API料金体系に基づく概算
        # 実際の料金は使用量とレート制限により変動
        base_cost = 0.06  # 基本料金（分あたり）
        audio_cost = audio_size / 1024 / 1024 * 0.006  # 音声データサイズベース
        time_cost = processing_time / 60 * base_cost
        
        return round(audio_cost + time_cost, 4)

    async def cleanup_session(self, session_id: str):
        """セッションクリーンアップ"""
        if session_id not in self.active_sessions:
            return
        
        session = self.active_sessions[session_id]
        
        try:
            if session.websocket and not session.websocket.closed:
                await session.websocket.close()
                
        except Exception as e:
            print(f"⚠️ Session cleanup error: {e}")
        
        finally:
            session.state = RealtimeSessionState.DISCONNECTED
            del self.active_sessions[session_id]
            print(f"🧹 Realtime session cleaned up: {session_id}")