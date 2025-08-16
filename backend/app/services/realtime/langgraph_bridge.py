"""
OpenAI Realtime APIとLangGraphを連携するブリッジ

このブリッジは以下の機能を提供:
1. Realtime APIのFunction CallsをLangGraphノードにマッピング
2. 既存のLangGraphワークフローとの統合
3. セッション状態の同期と管理
4. エラーハンドリングとフォールバック
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from ...agents.reception_graph import ReceptionGraphManager
from ...models.conversation import ConversationState
from ...models.visitor import VisitorInfo
from ...services.calendar_service import CalendarService
from ...services.slack_service import SlackService


class FunctionCallStatus(Enum):
    """Function Call実行状態"""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class FunctionCallExecution:
    """Function Call実行情報"""
    call_id: str
    function_name: str
    parameters: Dict[str, Any]
    status: FunctionCallStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: float = 0.0


class LangGraphBridge:
    """Realtime API ↔ LangGraph ブリッジ"""

    def __init__(self):
        # 既存サービスとの統合
        self.graph_manager = ReceptionGraphManager()
        self.calendar_service = CalendarService()
        self.slack_service = SlackService()
        
        # Function Call実行履歴
        self.execution_history: Dict[str, List[FunctionCallExecution]] = {}
        
        # Function Callsマッピング
        self.function_mappings = {
            "collect_visitor_info": self._execute_collect_visitor_info,
            "check_appointment": self._execute_check_appointment,
            "send_notification": self._execute_send_notification,
            "guide_visitor": self._execute_guide_visitor
        }
        
        print("✅ LangGraphBridge initialized")

    async def execute_function_call(
        self, 
        session_id: str, 
        function_name: str, 
        parameters: Dict[str, Any],
        call_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Function Callを実行してLangGraphと統合
        
        Args:
            session_id: セッションID
            function_name: 実行する関数名
            parameters: 関数パラメーター
            call_id: Function CallのID
            
        Returns:
            実行結果
        """
        # 実行履歴初期化
        if session_id not in self.execution_history:
            self.execution_history[session_id] = []
        
        # 実行情報作成
        execution = FunctionCallExecution(
            call_id=call_id or f"call_{len(self.execution_history[session_id])}",
            function_name=function_name,
            parameters=parameters,
            status=FunctionCallStatus.PENDING
        )
        
        self.execution_history[session_id].append(execution)
        
        try:
            execution.status = FunctionCallStatus.EXECUTING
            start_time = asyncio.get_event_loop().time()
            
            print(f"🔧 Executing function call: {function_name} for session {session_id}")
            
            # Function Call実行
            if function_name in self.function_mappings:
                result = await self.function_mappings[function_name](session_id, parameters)
                execution.result = result
                execution.status = FunctionCallStatus.COMPLETED
            else:
                raise ValueError(f"Unknown function: {function_name}")
            
            execution.execution_time = asyncio.get_event_loop().time() - start_time
            
            print(f"✅ Function call completed: {function_name} ({execution.execution_time:.2f}s)")
            
            return {
                "success": True,
                "call_id": execution.call_id,
                "function_name": function_name,
                "result": execution.result,
                "execution_time": execution.execution_time
            }
            
        except Exception as e:
            execution.status = FunctionCallStatus.FAILED
            execution.error = str(e)
            
            print(f"❌ Function call failed: {function_name} - {e}")
            
            return {
                "success": False,
                "call_id": execution.call_id,
                "function_name": function_name,
                "error": str(e)
            }

    async def _execute_collect_visitor_info(self, session_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """来客者情報収集Function Call"""
        try:
            # パラメーター抽出
            visitor_name = parameters.get("visitor_name", "")
            company_name = parameters.get("company_name", "")
            purpose = parameters.get("purpose", "")
            
            # VisitorInfo作成
            visitor_info = VisitorInfo(
                name=visitor_name,
                company=company_name,
                purpose=purpose,
                contact_info=parameters.get("contact_info"),
                note=parameters.get("note")
            )
            
            # LangGraphのセッション状態を更新
            current_state = await self.graph_manager.get_conversation_history(session_id)
            
            if current_state["success"]:
                # 既存の状態に来客者情報を追加
                from langchain_core.messages import AIMessage
                
                update_message = AIMessage(
                    content=f"来客者情報を確認いたします：\n名前: {visitor_name}\n会社: {company_name}\n目的: {purpose}"
                )
                
                # セッション状態の更新をLangGraphに委譲
                # これにより既存のワークフローとの整合性を保つ
                graph_result = await self.graph_manager.send_message(
                    session_id, 
                    f"visitor_info_update:{json.dumps(visitor_info.dict())}"
                )
                
                return {
                    "visitor_info": visitor_info.dict(),
                    "confirmation_message": "来客者情報を確認いたしました。",
                    "next_step": "confirmation" if all([visitor_name, company_name]) else "collect_missing_info",
                    "langgraph_result": graph_result
                }
            else:
                # セッションが見つからない場合は新規作成
                init_result = await self.graph_manager.start_conversation(session_id)
                
                return {
                    "visitor_info": visitor_info.dict(),
                    "confirmation_message": "新しいセッションで来客者情報を記録いたしました。",
                    "next_step": "collect_missing_info",
                    "session_created": True,
                    "langgraph_result": init_result
                }
                
        except Exception as e:
            return {
                "error": f"来客者情報の処理中にエラーが発生しました: {str(e)}",
                "visitor_info": None,
                "next_step": "retry"
            }

    async def _execute_check_appointment(self, session_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """予約確認Function Call"""
        try:
            visitor_name = parameters.get("visitor_name", "")
            date = parameters.get("date", "")
            
            print(f"📅 Checking appointment for {visitor_name} on {date}")
            
            # CalendarServiceを使用して予約確認
            # （既存のLangGraphノードと同じロジック）
            calendar_result = await self.calendar_service.check_appointment(
                visitor_name=visitor_name,
                date=date
            )
            
            if calendar_result.get("found"):
                appointment = calendar_result["appointment"]
                return {
                    "appointment_found": True,
                    "appointment": appointment,
                    "message": f"{visitor_name}様の{date}のご予約を確認いたしました。",
                    "next_step": "guide_to_meeting",
                    "calendar_result": calendar_result
                }
            else:
                return {
                    "appointment_found": False,
                    "message": f"{visitor_name}様の{date}のご予約が見つかりませんでした。",
                    "next_step": "handle_no_appointment",
                    "calendar_result": calendar_result
                }
                
        except Exception as e:
            return {
                "error": f"予約確認中にエラーが発生しました: {str(e)}",
                "appointment_found": False,
                "next_step": "retry"
            }

    async def _execute_send_notification(self, session_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """スタッフ通知Function Call"""
        try:
            visitor_info = parameters.get("visitor_info", {})
            message = parameters.get("message", "")
            
            print(f"📢 Sending notification for session {session_id}")
            
            # SlackServiceを使用して通知送信
            # （既存のLangGraphノードと同じロジック）
            notification_result = await self.slack_service.send_visitor_notification(
                visitor_info=visitor_info,
                custom_message=message,
                session_id=session_id
            )
            
            if notification_result.get("success"):
                return {
                    "notification_sent": True,
                    "message": "担当者への通知を送信いたしました。",
                    "slack_result": notification_result,
                    "next_step": "wait_for_staff"
                }
            else:
                return {
                    "notification_sent": False,
                    "error": "通知送信に失敗しました。",
                    "slack_result": notification_result,
                    "next_step": "retry_notification"
                }
                
        except Exception as e:
            return {
                "error": f"通知送信中にエラーが発生しました: {str(e)}",
                "notification_sent": False,
                "next_step": "retry"
            }

    async def _execute_guide_visitor(self, session_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """来客者案内Function Call"""
        try:
            visitor_type = parameters.get("visitor_type", "other")
            location = parameters.get("location", "")
            
            print(f"🗺️ Guiding visitor (type: {visitor_type}) for session {session_id}")
            
            # 来客者タイプに基づく案内メッセージ生成
            guide_messages = {
                "appointment": {
                    "message": "ご予約のお客様ですね。担当者にご連絡いたしますので、少々お待ちください。",
                    "location": "受付エリアでお待ちください",
                    "next_step": "notify_staff"
                },
                "sales": {
                    "message": "営業のお客様ですね。受付にて詳細を確認させていただきます。",
                    "location": "受付カウンターまでお越しください",
                    "next_step": "handle_sales_visit"
                },
                "delivery": {
                    "message": "配達のお客様ですね。配達物の確認をいたします。",
                    "location": "荷物受付エリア",
                    "next_step": "handle_delivery"
                },
                "other": {
                    "message": "お越しいただきありがとうございます。詳細を確認いたします。",
                    "location": "受付エリア",
                    "next_step": "general_inquiry"
                }
            }
            
            guide_info = guide_messages.get(visitor_type, guide_messages["other"])
            
            # 指定された場所がある場合は上書き
            if location:
                guide_info["location"] = location
            
            # LangGraphの案内ノードと連携
            graph_result = await self.graph_manager.send_message(
                session_id,
                f"guide_visitor:{visitor_type}:{location}"
            )
            
            return {
                "guidance_provided": True,
                "visitor_type": visitor_type,
                "location": guide_info["location"],
                "message": guide_info["message"],
                "next_step": guide_info["next_step"],
                "langgraph_result": graph_result
            }
            
        except Exception as e:
            return {
                "error": f"案内処理中にエラーが発生しました: {str(e)}",
                "guidance_provided": False,
                "next_step": "retry"
            }

    async def sync_session_state(self, session_id: str, realtime_state: Dict[str, Any]) -> Dict[str, Any]:
        """RealtimeセッションとLangGraphセッションの状態同期"""
        try:
            # LangGraphの現在状態を取得
            langgraph_state = await self.graph_manager.get_conversation_history(session_id)
            
            if not langgraph_state["success"]:
                # LangGraphセッションが存在しない場合は作成
                init_result = await self.graph_manager.start_conversation(session_id)
                if init_result["success"]:
                    langgraph_state = await self.graph_manager.get_conversation_history(session_id)
            
            # 状態統合
            synchronized_state = {
                "session_id": session_id,
                "langgraph_step": langgraph_state.get("current_step"),
                "visitor_info": langgraph_state.get("visitor_info"),
                "calendar_result": langgraph_state.get("calendar_result"),
                "message_count": len(langgraph_state.get("messages", [])),
                "realtime_features": realtime_state.get("features", []),
                "last_sync": asyncio.get_event_loop().time()
            }
            
            return {
                "success": True,
                "synchronized_state": synchronized_state
            }
            
        except Exception as e:
            print(f"❌ State sync error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_function_execution_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Function Call実行履歴取得"""
        if session_id not in self.execution_history:
            return []
        
        history = []
        for execution in self.execution_history[session_id]:
            history.append({
                "call_id": execution.call_id,
                "function_name": execution.function_name,
                "parameters": execution.parameters,
                "status": execution.status.value,
                "result": execution.result,
                "error": execution.error,
                "execution_time": execution.execution_time
            })
        
        return history

    async def cleanup_session(self, session_id: str):
        """セッションクリーンアップ"""
        if session_id in self.execution_history:
            del self.execution_history[session_id]
            print(f"🧹 Function call history cleaned up for session: {session_id}")