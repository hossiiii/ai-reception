import asyncio
import base64
import json

from fastapi import WebSocket, WebSocketDisconnect

from ..agents.reception_graph import ReceptionGraphManager
from ..services.audio_service import AudioService
from ..services.voice_activity_detector import VADConfig, VoiceActivityDetector
from ..services.realtime.hybrid_voice_manager import HybridVoiceManager
from ..services.realtime.realtime_websocket_handler import get_realtime_websocket_handler
from ..config.feature_flags import is_realtime_enabled


class VoiceWebSocketManager:
    """Manages WebSocket connections for voice chat with hybrid Realtime/Legacy support"""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.audio_service = AudioService()
        self.graph_manager = ReceptionGraphManager()
        
        # Hybrid Voice Manager for Realtime API integration
        self.hybrid_manager = HybridVoiceManager()
        
        print("✅ VoiceWebSocketManager initialized with hybrid support")

    async def connect(self, session_id: str, websocket: WebSocket):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        print(f"🔌 WebSocket connected: {session_id}")

    def disconnect(self, session_id: str):
        """Remove WebSocket connection"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            print(f"🔌 WebSocket disconnected: {session_id}")

    async def send_message(self, session_id: str, message: dict):
        """Send message to specific WebSocket connection"""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                print(f"❌ Failed to send message to {session_id}: {e}")
                self.disconnect(session_id)

    async def broadcast_to_session(self, session_id: str, message_type: str, data: dict):
        """Broadcast message to session"""
        message = {
            "type": message_type,
            "session_id": session_id,
            "timestamp": asyncio.get_event_loop().time(),
            **data
        }
        await self.send_message(session_id, message)


# Global WebSocket manager instance
voice_ws_manager = VoiceWebSocketManager()


def get_voice_ws_manager() -> VoiceWebSocketManager:
    """Dependency injection for WebSocket manager"""
    return voice_ws_manager


async def handle_voice_websocket(
    websocket: WebSocket,
    session_id: str
):
    """Handle voice WebSocket connection and audio streaming"""

    # Get the WebSocket manager instance directly
    manager = get_voice_ws_manager()

    # Initialize VAD for this session
    vad = VoiceActivityDetector(VADConfig(
        energy_threshold=0.01,
        silence_duration_ms=1500,
        min_speech_duration_ms=500
    ))

    # Audio buffer for collecting speech chunks
    audio_buffer = bytearray()
    is_collecting_speech = False
    awaiting_audio_blob = False
    expected_audio_size = 0

    try:
        # Connect WebSocket
        await manager.connect(session_id, websocket)

        # Determine processing mode (Realtime vs Legacy)
        use_realtime = is_realtime_enabled(session_id)
        
        if use_realtime:
            print(f"🎙️ Starting REALTIME voice conversation for session: {session_id}")
            # Initialize hybrid voice session
            hybrid_result = await manager.hybrid_manager.start_session(session_id)
            
            if hybrid_result["success"]:
                await manager.broadcast_to_session(session_id, "session_initialized", {
                    "processing_mode": hybrid_result["processing_mode"],
                    "features": hybrid_result["features"],
                    "limits": hybrid_result["limits"]
                })
                
                # Send initial greeting through hybrid manager
                greeting_result = await manager.hybrid_manager.process_audio_message(session_id, b"")
                if greeting_result.get("success"):
                    await manager.broadcast_to_session(session_id, "voice_response", {
                        "text": greeting_result.get("ai_response", "いらっしゃいませ。お名前とご用件をお聞かせください。"),
                        "audio": base64.b64encode(greeting_result.get("audio_response", b"")).decode(),
                        "processing_mode": greeting_result["processing_mode"]
                    })
            else:
                # Fallback to legacy mode
                use_realtime = False
                print(f"⚠️ Realtime initialization failed, falling back to legacy mode")
        
        if not use_realtime:
            print(f"🎙️ Starting LEGACY voice conversation for session: {session_id}")
            # Start conversation with greeting
            conversation_result = await manager.graph_manager.start_conversation(session_id)

            if conversation_result["success"]:
                # Generate audio greeting
                greeting_text = conversation_result["message"]
                greeting_audio = await manager.audio_service.generate_audio_output(greeting_text)

                await manager.broadcast_to_session(session_id, "voice_response", {
                    "text": greeting_text,
                    "audio": base64.b64encode(greeting_audio).decode() if greeting_audio else "",
                    "step": conversation_result["step"],
                    "visitor_info": conversation_result.get("visitor_info"),
                    "processing_mode": "legacy"
                })
            else:
                await manager.broadcast_to_session(session_id, "error", {
                    "message": "Failed to start conversation",
                    "error": conversation_result.get("error")
                })
                return

        # Main WebSocket loop
        while True:
            try:
                # Receive audio data
                data = await websocket.receive()

                if "bytes" in data:
                    # Handle binary audio data
                    audio_chunk = data["bytes"]

                    # Check if we're waiting for a complete audio blob
                    if awaiting_audio_blob and len(audio_chunk) > 0:
                        print(f"📦 Received complete audio blob: {len(audio_chunk)} bytes")
                        awaiting_audio_blob = False

                        # Process the complete audio through hybrid manager
                        await manager.broadcast_to_session(session_id, "processing", {
                            "message": "音声を処理中..."
                        })

                        if use_realtime:
                            # Use Hybrid Voice Manager for Realtime processing
                            hybrid_result = await manager.hybrid_manager.process_audio_message(session_id, audio_chunk)
                            
                            if hybrid_result["success"]:
                                await manager.broadcast_to_session(session_id, "voice_response", {
                                    "text": hybrid_result["ai_response"],
                                    "audio": base64.b64encode(hybrid_result["audio_response"]).decode() if hybrid_result["audio_response"] else "",
                                    "transcription": hybrid_result.get("transcription", ""),
                                    "processing_mode": hybrid_result["processing_mode"],
                                    "latency_ms": hybrid_result.get("latency_ms", 0),
                                    "cost": hybrid_result.get("cost", 0),
                                    "completed": hybrid_result.get("completed", False)
                                })
                            else:
                                # Handle hybrid processing error
                                await manager.broadcast_to_session(session_id, "error", {
                                    "message": "音声処理中にエラーが発生しました",
                                    "error": hybrid_result.get("error", "Unknown error")
                                })
                        else:
                            # Legacy processing
                            transcribed_text = await manager.audio_service.process_audio_input(audio_chunk)

                            if transcribed_text and transcribed_text.strip():
                                print(f"📝 Transcribed: {transcribed_text}")

                                # Send transcription to client
                                await manager.broadcast_to_session(session_id, "transcription", {
                                    "text": transcribed_text
                                })

                                # Process message through Step1 LangGraph system
                                response = await manager.graph_manager.send_message(session_id, transcribed_text)

                                if response["success"]:
                                    # Generate audio response
                                    response_text = response["message"]
                                    response_audio = await manager.audio_service.generate_audio_output(response_text)

                                    # Send voice response
                                    await manager.broadcast_to_session(session_id, "voice_response", {
                                        "text": response_text,
                                        "audio": base64.b64encode(response_audio).decode() if response_audio else "",
                                        "step": response["step"],
                                        "visitor_info": response.get("visitor_info"),
                                        "calendar_result": response.get("calendar_result"),
                                        "completed": response.get("completed", False),
                                        "processing_mode": "legacy"
                                    })

                        # Send ready status
                        await manager.broadcast_to_session(session_id, "ready", {
                            "message": "Ready for next input"
                        })
                        continue

                    if len(audio_chunk) > 0:
                        # Run VAD on audio chunk (for real-time feedback only)
                        vad_result = vad.detect_voice_activity(audio_chunk)

                        # Send VAD status to client
                        await manager.broadcast_to_session(session_id, "vad_status", {
                            "is_speech": vad_result.is_speech,
                            "energy_level": vad_result.energy_level,
                            "confidence": vad_result.confidence,
                            "duration_ms": vad_result.duration_ms
                        })

                        # Collect audio during speech (kept for backward compatibility)
                        if vad_result.is_speech:
                            audio_buffer.extend(audio_chunk)
                            is_collecting_speech = True

                        # Process speech when it ends
                        if vad_result.speech_ended and is_collecting_speech and len(audio_buffer) > 0:
                            print(f"🗣️ Processing speech ({len(audio_buffer)} bytes)")

                            # Send processing status
                            await manager.broadcast_to_session(session_id, "processing", {
                                "message": "音声を処理中..."
                            })

                            # Convert audio to text
                            transcribed_text = await manager.audio_service.process_audio_input(bytes(audio_buffer))

                            if transcribed_text and transcribed_text.strip():
                                print(f"📝 Transcribed: {transcribed_text}")

                                # Send transcription to client
                                await manager.broadcast_to_session(session_id, "transcription", {
                                    "text": transcribed_text
                                })

                                # Process message through Step1 LangGraph system
                                response = await manager.graph_manager.send_message(session_id, transcribed_text)

                                if response["success"]:
                                    # Generate audio response
                                    response_text = response["message"]
                                    response_audio = await manager.audio_service.generate_audio_output(response_text)

                                    # Send voice response
                                    await manager.broadcast_to_session(session_id, "voice_response", {
                                        "text": response_text,
                                        "audio": base64.b64encode(response_audio).decode() if response_audio else "",
                                        "step": response["step"],
                                        "visitor_info": response.get("visitor_info"),
                                        "calendar_result": response.get("calendar_result"),
                                        "completed": response.get("completed", False)
                                    })

                                    # Auto-end if conversation is completed
                                    if response.get("completed"):
                                        await manager.broadcast_to_session(session_id, "conversation_completed", {
                                            "message": "対応が完了しました。ありがとうございました。"
                                        })
                                        break

                                else:
                                    # Send error response
                                    error_text = response.get("error", "処理中にエラーが発生しました。もう一度お試しください。")
                                    error_audio = await manager.audio_service.generate_audio_output(error_text)

                                    await manager.broadcast_to_session(session_id, "voice_response", {
                                        "text": error_text,
                                        "audio": base64.b64encode(error_audio).decode() if error_audio else "",
                                        "step": "error",
                                        "error": response.get("error")
                                    })

                            # Reset buffer and collection state
                            audio_buffer.clear()
                            is_collecting_speech = False
                            vad.reset_state()

                            # Send ready status
                            await manager.broadcast_to_session(session_id, "ready", {
                                "message": "Ready for next input"
                            })

                elif "text" in data:
                    # Handle text commands/control messages
                    try:
                        message = json.loads(data["text"])
                        command = message.get("command")

                        if command == "ping":
                            await manager.broadcast_to_session(session_id, "pong", {
                                "timestamp": asyncio.get_event_loop().time()
                            })
                        elif command == "reset_audio":
                            # Reset audio processing state
                            audio_buffer.clear()
                            is_collecting_speech = False
                            vad.reset_state()
                            await manager.broadcast_to_session(session_id, "audio_reset", {
                                "message": "Audio state reset"
                            })
                        elif command == "get_status":
                            # Send current status
                            await manager.broadcast_to_session(session_id, "status", {
                                "vad_state": vad.get_current_state(),
                                "buffer_size": len(audio_buffer),
                                "collecting_speech": is_collecting_speech
                            })
                        elif command == "end_speech_with_audio":
                            # Expect a complete audio blob to follow
                            awaiting_audio_blob = True
                            expected_audio_size = message.get("audio_size", 0)
                            mime_type = message.get("mime_type", "audio/webm")
                            print(f"📥 Expecting audio blob: {expected_audio_size} bytes, type: {mime_type}")
                        elif command == "text_input":
                            # Handle direct text input (for name/company clarification)
                            text_input = message.get("text", "")
                            if text_input:
                                print(f"📝 Direct text input received: {text_input}")

                                # Send processing status
                                await manager.broadcast_to_session(session_id, "processing", {
                                    "message": "テキストを処理中..."
                                })

                                # Process message through Step1 LangGraph system
                                response = await manager.graph_manager.send_message(session_id, text_input)

                                if response["success"]:
                                    # Generate audio response
                                    response_text = response["message"]
                                    response_audio = await manager.audio_service.generate_audio_output(response_text)

                                    # Send voice response
                                    await manager.broadcast_to_session(session_id, "voice_response", {
                                        "text": response_text,
                                        "audio": base64.b64encode(response_audio).decode() if response_audio else "",
                                        "step": response["step"],
                                        "visitor_info": response.get("visitor_info"),
                                        "calendar_result": response.get("calendar_result"),
                                        "completed": response.get("completed", False)
                                    })

                                    # Auto-end if conversation is completed
                                    if response.get("completed"):
                                        await manager.broadcast_to_session(session_id, "conversation_completed", {
                                            "message": "対応が完了しました。ありがとうございました。"
                                        })
                                        break
                                else:
                                    # Send error response
                                    error_text = response.get("error", "処理中にエラーが発生しました。もう一度お試しください。")
                                    error_audio = await manager.audio_service.generate_audio_output(error_text)

                                    await manager.broadcast_to_session(session_id, "voice_response", {
                                        "text": error_text,
                                        "audio": base64.b64encode(error_audio).decode() if error_audio else "",
                                        "step": "error",
                                        "error": response.get("error")
                                    })

                                # Send ready status
                                await manager.broadcast_to_session(session_id, "ready", {
                                    "message": "Ready for next input"
                                })
                        elif command == "end_speech":
                            # Force end speech and process buffer
                            if is_collecting_speech and len(audio_buffer) > 0:
                                print(f"🔚 Force ending speech ({len(audio_buffer)} bytes)")

                                # Send processing status
                                await manager.broadcast_to_session(session_id, "processing", {
                                    "message": "音声を処理中..."
                                })

                                # Process the collected audio
                                transcribed_text = await manager.audio_service.process_audio_input(bytes(audio_buffer))

                                if transcribed_text and transcribed_text.strip():
                                    print(f"📝 Transcribed: {transcribed_text}")

                                    # Send transcription to client
                                    await manager.broadcast_to_session(session_id, "transcription", {
                                        "text": transcribed_text
                                    })

                                    # Process message through Step1 LangGraph system
                                    response = await manager.graph_manager.send_message(session_id, transcribed_text)

                                    if response["success"]:
                                        # Generate audio response
                                        response_text = response["message"]
                                        response_audio = await manager.audio_service.generate_audio_output(response_text)

                                        # Send voice response
                                        await manager.broadcast_to_session(session_id, "voice_response", {
                                            "text": response_text,
                                            "audio": base64.b64encode(response_audio).decode() if response_audio else "",
                                            "step": response["step"],
                                            "visitor_info": response.get("visitor_info"),
                                            "calendar_result": response.get("calendar_result"),
                                            "completed": response.get("completed", False)
                                        })

                                # Reset buffer and state
                                audio_buffer.clear()
                                is_collecting_speech = False
                                vad.reset_state()

                                # Send ready status
                                await manager.broadcast_to_session(session_id, "ready", {
                                    "message": "Ready for next input"
                                })
                        else:
                            print(f"⚠️ Unknown command: {command}")

                    except json.JSONDecodeError:
                        print(f"⚠️ Invalid JSON message: {data['text']}")

            except TimeoutError:
                # Handle timeout
                await manager.broadcast_to_session(session_id, "timeout", {
                    "message": "Connection timeout"
                })
                break

    except WebSocketDisconnect:
        print(f"🔌 WebSocket disconnected normally: {session_id}")

    except Exception as e:
        print(f"❌ WebSocket error for session {session_id}: {e}")

    finally:
        # Cleanup
        manager.disconnect(session_id)

        # Optional: Send conversation log to Slack if conversation was active
        try:
            conversation_history = await manager.graph_manager.get_conversation_history(session_id)
            if conversation_history["success"] and conversation_history["messages"]:
                print(f"📋 Conversation ended with {len(conversation_history['messages'])} messages")
                # Note: Slack notification is already handled by the LangGraph system in Step1
        except Exception as e:
            print(f"⚠️ Error during cleanup: {e}")


# Factory function to create WebSocket endpoints
def create_voice_websocket_endpoint():
    """Create voice WebSocket endpoint function"""
    async def voice_websocket_endpoint(websocket: WebSocket, session_id: str):
        await handle_voice_websocket(websocket, session_id)

    return voice_websocket_endpoint


def create_realtime_websocket_endpoint():
    """Create dedicated Realtime WebSocket endpoint function"""
    async def realtime_websocket_endpoint(websocket: WebSocket, session_id: str):
        """Dedicated Realtime API WebSocket endpoint"""
        realtime_handler = get_realtime_websocket_handler()
        await realtime_handler.handle_client_connection(websocket, session_id)

    return realtime_websocket_endpoint


async def handle_hybrid_mode_selection(websocket: WebSocket, session_id: str, mode_preference: str = "auto"):
    """
    ハイブリッドモード選択エンドポイント
    
    Args:
        websocket: WebSocket接続
        session_id: セッションID
        mode_preference: モード設定 ("auto", "realtime", "legacy")
    """
    
    try:
        await websocket.accept()
        
        # モード選択ロジック
        if mode_preference == "realtime":
            # 強制Realtimeモード
            print(f"🎙️ Forced Realtime mode requested for session: {session_id}")
            realtime_handler = get_realtime_websocket_handler()
            await realtime_handler.handle_client_connection(websocket, session_id)
            
        elif mode_preference == "legacy":
            # 強制Legacyモード
            print(f"🎙️ Forced Legacy mode requested for session: {session_id}")
            await handle_voice_websocket(websocket, session_id)
            
        else:
            # 自動選択（既存のハイブリッドロジック）
            print(f"🎙️ Auto mode selection for session: {session_id}")
            await handle_voice_websocket(websocket, session_id)
            
    except Exception as e:
        print(f"❌ Hybrid mode selection error: {e}")
        try:
            await websocket.close(code=1011, reason=f"Mode selection failed: {e}")
        except:
            pass


def create_hybrid_mode_websocket_endpoint():
    """Create hybrid mode selection WebSocket endpoint function"""
    async def hybrid_mode_websocket_endpoint(websocket: WebSocket, session_id: str, mode: str = "auto"):
        await handle_hybrid_mode_selection(websocket, session_id, mode)

    return hybrid_mode_websocket_endpoint
