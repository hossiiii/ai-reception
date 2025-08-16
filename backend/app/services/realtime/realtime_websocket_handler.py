"""
OpenAI Realtime API専用WebSocketハンドラー

このハンドラーは以下の機能を提供:
1. OpenAI Realtime APIとのWebSocket接続管理
2. 音声データの双方向ストリーミング
3. Function Callsの処理とLangGraphとの統合
4. 既存WebSocketとの共存
"""

import asyncio
import json
import base64
import time
import uuid
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

import websockets
from fastapi import WebSocket, WebSocketDisconnect

from .realtime_audio_processor import RealtimeAudioProcessor, RealtimeSessionState
from .langgraph_bridge import LangGraphBridge
from ...config.realtime_settings import RealtimeSettings
from ...config.feature_flags import FeatureFlags
from ..metrics_collector import MetricsCollector


class WebSocketConnectionState(Enum):
    """WebSocket接続状態"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    ERROR = "error"


@dataclass
class RealtimeWebSocketSession:
    """Realtime WebSocket セッション管理"""
    session_id: str
    client_websocket: Optional[WebSocket] = None
    realtime_websocket: Optional[websockets.WebSocketServerProtocol] = None
    state: WebSocketConnectionState = WebSocketConnectionState.DISCONNECTED
    start_time: float = field(default_factory=time.time)
    message_count: int = 0
    error_count: int = 0
    function_calls_active: bool = False


class RealtimeWebSocketHandler:
    """OpenAI Realtime API専用WebSocketハンドラー"""

    def __init__(self):
        self.settings = RealtimeSettings()
        self.feature_flags = FeatureFlags()
        self.metrics_collector = MetricsCollector()
        
        # コア処理エンジン
        self.audio_processor = RealtimeAudioProcessor()
        self.langgraph_bridge = LangGraphBridge()
        
        # セッション管理
        self.active_sessions: Dict[str, RealtimeWebSocketSession] = {}
        
        # WebSocket接続設定
        self.realtime_url = "wss://api.openai.com/v1/realtime"
        self.api_headers = {
            "Authorization": f"Bearer {self.settings.realtime_api_key}",
            "OpenAI-Beta": "realtime=v1"
        }
        
        print("✅ RealtimeWebSocketHandler initialized")

    async def handle_client_connection(self, websocket: WebSocket, session_id: str) -> None:
        """
        クライアントからのWebSocket接続を処理
        
        Args:
            websocket: クライアントWebSocket
            session_id: セッションID
        """
        # セッション初期化
        session = RealtimeWebSocketSession(
            session_id=session_id,
            client_websocket=websocket
        )
        self.active_sessions[session_id] = session
        
        try:
            # WebSocket接続受け入れ
            await websocket.accept()
            session.state = WebSocketConnectionState.CONNECTED
            
            print(f"🔌 Realtime WebSocket connected: {session_id}")
            
            # OpenAI Realtime APIとの接続確立
            connection_result = await self._establish_realtime_connection(session_id)
            
            if not connection_result["success"]:
                await self._send_error_to_client(session_id, {
                    "error": "Failed to connect to Realtime API",
                    "details": connection_result.get("error", "Unknown error")
                })
                return
            
            # 成功の通知
            await self._send_to_client(session_id, {
                "type": "realtime_connected",
                "session_id": session_id,
                "capabilities": connection_result["capabilities"],
                "processing_mode": "realtime"
            })
            
            # メイン処理ループ
            await self._handle_session_loop(session_id)
            
        except WebSocketDisconnect:
            print(f"🔌 Realtime WebSocket disconnected: {session_id}")
            
        except Exception as e:
            print(f"❌ Realtime WebSocket error: {e}")
            await self._send_error_to_client(session_id, {
                "error": "WebSocket handling error",
                "details": str(e)
            })
            
        finally:
            await self._cleanup_session(session_id)

    async def _establish_realtime_connection(self, session_id: str) -> Dict[str, Any]:
        """OpenAI Realtime APIとの接続確立"""
        session = self.active_sessions[session_id]
        
        try:
            session.state = WebSocketConnectionState.CONNECTING
            
            # OpenAI Realtime API接続
            session.realtime_websocket = await websockets.connect(
                self.realtime_url,
                extra_headers=self.api_headers,
                timeout=self.settings.connection_timeout
            )
            
            # セッション設定
            session_config = {
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "instructions": self._get_reception_instructions(),
                    "voice": self.settings.voice_model,
                    "input_audio_format": self.settings.input_audio_format,
                    "output_audio_format": self.settings.output_audio_format,
                    "input_audio_transcription": {
                        "model": "whisper-1"
                    },
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": self.settings.turn_detection_threshold,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": self.settings.silence_duration_ms
                    },
                    "tools": self._get_function_call_tools() if self.settings.enable_function_calls else []
                }
            }
            
            await session.realtime_websocket.send(json.dumps(session_config))
            
            # 初期化レスポンス待機
            response = await asyncio.wait_for(
                session.realtime_websocket.recv(), 
                timeout=self.settings.response_timeout
            )
            response_data = json.loads(response)
            
            if response_data.get("type") == "session.updated":
                session.state = WebSocketConnectionState.AUTHENTICATED
                
                return {
                    "success": True,
                    "capabilities": {
                        "real_time_audio": True,
                        "function_calling": self.settings.enable_function_calls,
                        "turn_detection": True,
                        "low_latency": True,
                        "voice_model": self.settings.voice_model
                    }
                }
            else:
                raise Exception(f"Session initialization failed: {response_data}")
                
        except Exception as e:
            session.state = WebSocketConnectionState.ERROR
            print(f"❌ Realtime connection error: {e}")
            
            return {
                "success": False,
                "error": str(e)
            }

    async def _handle_session_loop(self, session_id: str) -> None:
        """セッションのメイン処理ループ"""
        session = self.active_sessions[session_id]
        
        # 同時処理のためのタスク作成
        client_task = asyncio.create_task(self._handle_client_messages(session_id))
        realtime_task = asyncio.create_task(self._handle_realtime_messages(session_id))
        
        try:
            # どちらかのタスクが完了するまで待機
            done, pending = await asyncio.wait(
                [client_task, realtime_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # 残りのタスクをキャンセル
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                    
        except Exception as e:
            print(f"❌ Session loop error: {e}")
            session.error_count += 1

    async def _handle_client_messages(self, session_id: str) -> None:
        """クライアントからのメッセージ処理"""
        session = self.active_sessions[session_id]
        
        while session.state == WebSocketConnectionState.AUTHENTICATED:
            try:
                # クライアントからのメッセージ受信
                data = await session.client_websocket.receive()
                
                if "bytes" in data:
                    # 音声データをRealtime APIに転送
                    await self._forward_audio_to_realtime(session_id, data["bytes"])
                    
                elif "text" in data:
                    # テキストメッセージ処理
                    message = json.loads(data["text"])
                    await self._handle_client_text_message(session_id, message)
                    
                session.message_count += 1
                
                # メトリクス記録
                await self.metrics_collector.record_message_processed(
                    session_id, 0, 0, "realtime"
                )
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"❌ Client message error: {e}")
                session.error_count += 1
                if session.error_count >= 5:
                    break

    async def _handle_realtime_messages(self, session_id: str) -> None:
        """Realtime APIからのメッセージ処理"""
        session = self.active_sessions[session_id]
        
        while session.state == WebSocketConnectionState.AUTHENTICATED:
            try:
                # Realtime APIからのメッセージ受信
                response = await asyncio.wait_for(
                    session.realtime_websocket.recv(),
                    timeout=self.settings.response_timeout
                )
                response_data = json.loads(response)
                
                # メッセージタイプ別処理
                await self._process_realtime_event(session_id, response_data)
                
            except asyncio.TimeoutError:
                print(f"⚠️ Realtime API timeout for session {session_id}")
                break
            except Exception as e:
                print(f"❌ Realtime message error: {e}")
                session.error_count += 1
                if session.error_count >= 5:
                    break

    async def _process_realtime_event(self, session_id: str, event_data: Dict[str, Any]) -> None:
        """Realtime APIイベントの処理"""
        event_type = event_data.get("type")
        
        try:
            if event_type == "conversation.item.input_audio_transcription.completed":
                # 音声認識結果をクライアントに送信
                await self._send_to_client(session_id, {
                    "type": "transcription",
                    "text": event_data.get("transcript", ""),
                    "item_id": event_data.get("item_id")
                })
                
            elif event_type == "response.audio.delta":
                # 音声レスポンスのストリーミング
                await self._send_to_client(session_id, {
                    "type": "audio_delta",
                    "audio": event_data.get("delta", ""),
                    "response_id": event_data.get("response_id")
                })
                
            elif event_type == "response.text.delta":
                # テキストレスポンスのストリーミング
                await self._send_to_client(session_id, {
                    "type": "text_delta",
                    "text": event_data.get("delta", ""),
                    "response_id": event_data.get("response_id")
                })
                
            elif event_type == "response.function_call_arguments.delta":
                # Function Call引数の収集
                await self._handle_function_call_delta(session_id, event_data)
                
            elif event_type == "response.function_call_arguments.done":
                # Function Call実行
                await self._execute_function_call(session_id, event_data)
                
            elif event_type == "response.done":
                # レスポンス完了
                await self._send_to_client(session_id, {
                    "type": "response_completed",
                    "response_id": event_data.get("response_id"),
                    "status": event_data.get("status")
                })
                
            elif event_type == "error":
                # エラー処理
                await self._handle_realtime_error(session_id, event_data)
                
            else:
                # その他のイベントはそのまま転送
                await self._send_to_client(session_id, {
                    "type": "realtime_event",
                    "event": event_data
                })
                
        except Exception as e:
            print(f"❌ Event processing error: {e}")
            await self._send_error_to_client(session_id, {
                "error": "Event processing failed",
                "details": str(e),
                "event_type": event_type
            })

    async def _forward_audio_to_realtime(self, session_id: str, audio_data: bytes) -> None:
        """音声データをRealtime APIに転送"""
        session = self.active_sessions[session_id]
        
        if not session.realtime_websocket:
            return
            
        try:
            # 音声データチャンクサイズ制限
            if len(audio_data) > self.settings.max_audio_chunk_size:
                audio_data = audio_data[:self.settings.max_audio_chunk_size]
            
            # Realtime APIに音声データ送信
            audio_message = {
                "type": "input_audio_buffer.append",
                "audio": base64.b64encode(audio_data).decode()
            }
            await session.realtime_websocket.send(json.dumps(audio_message))
            
        except Exception as e:
            print(f"❌ Audio forwarding error: {e}")

    async def _handle_client_text_message(self, session_id: str, message: Dict[str, Any]) -> None:
        """クライアントからのテキストメッセージ処理"""
        session = self.active_sessions[session_id]
        command = message.get("command")
        
        try:
            if command == "commit_audio":
                # 音声入力確定
                commit_message = {"type": "input_audio_buffer.commit"}
                await session.realtime_websocket.send(json.dumps(commit_message))
                
                # レスポンス生成をリクエスト
                response_create = {
                    "type": "response.create",
                    "response": {
                        "modalities": ["text", "audio"],
                        "instructions": "Please respond naturally in Japanese as a reception AI."
                    }
                }
                await session.realtime_websocket.send(json.dumps(response_create))
                
            elif command == "clear_audio":
                # 音声バッファクリア
                clear_message = {"type": "input_audio_buffer.clear"}
                await session.realtime_websocket.send(json.dumps(clear_message))
                
            elif command == "ping":
                # ping/pong
                await self._send_to_client(session_id, {
                    "type": "pong",
                    "timestamp": time.time()
                })
                
            elif command == "get_session_status":
                # セッション状態取得
                await self._send_session_status(session_id)
                
            else:
                print(f"⚠️ Unknown client command: {command}")
                
        except Exception as e:
            print(f"❌ Client message handling error: {e}")

    async def _handle_function_call_delta(self, session_id: str, event_data: Dict[str, Any]) -> None:
        """Function Call引数デルタの処理"""
        # Function Call実行フラグ設定
        session = self.active_sessions[session_id]
        session.function_calls_active = True
        
        # クライアントに進行状況を通知
        await self._send_to_client(session_id, {
            "type": "function_call_progress",
            "call_id": event_data.get("call_id"),
            "name": event_data.get("name"),
            "progress": "collecting_arguments"
        })

    async def _execute_function_call(self, session_id: str, event_data: Dict[str, Any]) -> None:
        """Function Callの実行"""
        session = self.active_sessions[session_id]
        
        try:
            call_id = event_data.get("call_id")
            function_name = event_data.get("name")
            arguments_str = event_data.get("arguments", "{}")
            
            # 引数をパース
            try:
                arguments = json.loads(arguments_str)
            except json.JSONDecodeError:
                arguments = {}
            
            print(f"🔧 Executing function call: {function_name} with args: {arguments}")
            
            # LangGraphブリッジを通してFunction Call実行
            bridge_result = await self.langgraph_bridge.execute_function_call(
                session_id=session_id,
                function_name=function_name,
                parameters=arguments,
                call_id=call_id
            )
            
            # 実行結果をRealtime APIに送信
            if bridge_result["success"]:
                result_message = {
                    "type": "conversation.item.create",
                    "item": {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": json.dumps(bridge_result["result"])
                    }
                }
                await session.realtime_websocket.send(json.dumps(result_message))
                
                # クライアントに成功を通知
                await self._send_to_client(session_id, {
                    "type": "function_call_completed",
                    "call_id": call_id,
                    "function_name": function_name,
                    "success": True,
                    "result": bridge_result["result"]
                })
            else:
                # エラー結果をRealtime APIに送信
                error_message = {
                    "type": "conversation.item.create",
                    "item": {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": json.dumps({"error": bridge_result["error"]})
                    }
                }
                await session.realtime_websocket.send(json.dumps(error_message))
                
                # クライアントにエラーを通知
                await self._send_to_client(session_id, {
                    "type": "function_call_error",
                    "call_id": call_id,
                    "function_name": function_name,
                    "error": bridge_result["error"]
                })
            
            # 新しいレスポンス生成をリクエスト
            response_create = {
                "type": "response.create",
                "response": {
                    "modalities": ["text", "audio"]
                }
            }
            await session.realtime_websocket.send(json.dumps(response_create))
            
        except Exception as e:
            print(f"❌ Function call execution error: {e}")
            
            # エラーをクライアントとRealtime APIに通知
            await self._send_to_client(session_id, {
                "type": "function_call_error",
                "call_id": event_data.get("call_id"),
                "error": str(e)
            })
            
        finally:
            session.function_calls_active = False

    async def _handle_realtime_error(self, session_id: str, error_data: Dict[str, Any]) -> None:
        """Realtime APIエラーの処理"""
        session = self.active_sessions[session_id]
        session.error_count += 1
        
        error_info = error_data.get("error", {})
        error_message = error_info.get("message", "Unknown Realtime API error")
        error_code = error_info.get("code", "unknown")
        
        print(f"❌ Realtime API error: {error_code} - {error_message}")
        
        # エラーをクライアントに転送
        await self._send_error_to_client(session_id, {
            "error": "Realtime API error",
            "code": error_code,
            "message": error_message,
            "details": error_info
        })
        
        # 重大なエラーの場合は接続終了
        if error_code in ["invalid_api_key", "insufficient_quota", "rate_limit_exceeded"]:
            session.state = WebSocketConnectionState.ERROR

    async def _send_to_client(self, session_id: str, message: Dict[str, Any]) -> None:
        """クライアントにメッセージ送信"""
        session = self.active_sessions.get(session_id)
        
        if not session or not session.client_websocket:
            return
            
        try:
            message["timestamp"] = time.time()
            await session.client_websocket.send_text(json.dumps(message))
        except Exception as e:
            print(f"❌ Failed to send to client {session_id}: {e}")

    async def _send_error_to_client(self, session_id: str, error_info: Dict[str, Any]) -> None:
        """クライアントにエラー送信"""
        await self._send_to_client(session_id, {
            "type": "error",
            "session_id": session_id,
            **error_info
        })

    async def _send_session_status(self, session_id: str) -> None:
        """セッション状態をクライアントに送信"""
        session = self.active_sessions.get(session_id)
        
        if not session:
            return
            
        status = {
            "type": "session_status",
            "session_id": session_id,
            "state": session.state.value,
            "duration": time.time() - session.start_time,
            "message_count": session.message_count,
            "error_count": session.error_count,
            "function_calls_active": session.function_calls_active
        }
        
        await self._send_to_client(session_id, status)

    def _get_reception_instructions(self) -> str:
        """受付AI用のインストラクション"""
        return """あなたは日本の企業の受付AIアシスタントです。以下のルールに従って対応してください:

1. 常に丁寧な敬語を使用し、親しみやすく応対する
2. 来客者の名前、会社名、来訪目的を確認する
3. 必要に応じてFunction Callsを使ってシステム機能を実行する
4. 音声での自然な会話を心がけ、聞き取りやすく話す
5. 来客者のタイプ（予約、営業、配達等）を判断して適切に案内する
6. システムエラーの場合は丁寧に謝罪し、代替手段を提案する

リアルタイム音声処理により、自然で流暢な会話体験を提供してください。"""

    def _get_function_call_tools(self) -> list:
        """Function Callsツール定義"""
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

    async def _cleanup_session(self, session_id: str) -> None:
        """セッションクリーンアップ"""
        if session_id not in self.active_sessions:
            return
            
        session = self.active_sessions[session_id]
        
        try:
            # Realtime WebSocket接続クローズ
            if session.realtime_websocket and not session.realtime_websocket.closed:
                await session.realtime_websocket.close()
                
            # LangGraphブリッジクリーンアップ
            await self.langgraph_bridge.cleanup_session(session_id)
            
            # メトリクス記録
            session_duration = time.time() - session.start_time
            await self.metrics_collector.record_session_end(
                session_id, session_duration, 0, False
            )
            
        except Exception as e:
            print(f"⚠️ Session cleanup error: {e}")
            
        finally:
            # セッション削除
            del self.active_sessions[session_id]
            session.state = WebSocketConnectionState.DISCONNECTED
            print(f"🧹 Realtime WebSocket session cleaned up: {session_id}")

    async def get_active_sessions(self) -> Dict[str, Dict[str, Any]]:
        """アクティブセッション一覧取得"""
        sessions = {}
        
        for session_id, session in self.active_sessions.items():
            sessions[session_id] = {
                "state": session.state.value,
                "duration": time.time() - session.start_time,
                "message_count": session.message_count,
                "error_count": session.error_count,
                "function_calls_active": session.function_calls_active
            }
        
        return sessions

    async def force_disconnect_session(self, session_id: str) -> bool:
        """セッション強制切断"""
        if session_id not in self.active_sessions:
            return False
            
        try:
            await self._cleanup_session(session_id)
            return True
        except Exception as e:
            print(f"❌ Force disconnect error: {e}")
            return False


# グローバルハンドラーインスタンス
realtime_websocket_handler = RealtimeWebSocketHandler()


def get_realtime_websocket_handler() -> RealtimeWebSocketHandler:
    """Realtime WebSocketハンドラー取得"""
    return realtime_websocket_handler