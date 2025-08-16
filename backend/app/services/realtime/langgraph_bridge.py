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
        Function Callを実行してLangGraphと統合（強化版）
        
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
        
        # リトライ設定
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                execution.status = FunctionCallStatus.EXECUTING
                start_time = asyncio.get_event_loop().time()
                
                print(f"🔧 Executing function call: {function_name} for session {session_id} (attempt {attempt + 1})")
                
                # パラメーター検証
                validated_params = await self._validate_function_parameters(function_name, parameters)
                
                # Function Call実行
                if function_name in self.function_mappings:
                    result = await asyncio.wait_for(
                        self.function_mappings[function_name](session_id, validated_params),
                        timeout=30.0  # 30秒タイムアウト
                    )
                    execution.result = result
                    execution.status = FunctionCallStatus.COMPLETED
                else:
                    raise ValueError(f"Unknown function: {function_name}")
                
                execution.execution_time = asyncio.get_event_loop().time() - start_time
                
                print(f"✅ Function call completed: {function_name} ({execution.execution_time:.2f}s)")
                
                # 成功時は処理後のタスクを実行
                await self._post_function_execution(session_id, function_name, result)
                
                return {
                    "success": True,
                    "call_id": execution.call_id,
                    "function_name": function_name,
                    "result": execution.result,
                    "execution_time": execution.execution_time,
                    "attempt": attempt + 1
                }
                
            except asyncio.TimeoutError as e:
                error_msg = f"Function call timeout: {function_name}"
                print(f"⏰ {error_msg}")
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                    
                execution.status = FunctionCallStatus.FAILED
                execution.error = error_msg
                
                return {
                    "success": False,
                    "call_id": execution.call_id,
                    "function_name": function_name,
                    "error": error_msg,
                    "timeout": True
                }
                
            except Exception as e:
                error_msg = str(e)
                print(f"❌ Function call error: {function_name} - {error_msg}")
                
                if attempt < max_retries - 1 and self._is_retryable_error(e):
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                    
                execution.status = FunctionCallStatus.FAILED
                execution.error = error_msg
                
                return {
                    "success": False,
                    "call_id": execution.call_id,
                    "function_name": function_name,
                    "error": error_msg,
                    "attempt": attempt + 1
                }
        
        # すべてのリトライ失敗
        return {
            "success": False,
            "call_id": execution.call_id,
            "function_name": function_name,
            "error": f"Failed after {max_retries} attempts",
            "max_retries_exceeded": True
        }

    async def _validate_function_parameters(self, function_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Function Callパラメーターの検証と補完"""
        validated = parameters.copy()
        
        try:
            if function_name == "collect_visitor_info":
                # 必須フィールドの確認
                if not validated.get("visitor_name"):
                    raise ValueError("visitor_name is required")
                    
                # データクリーニング
                validated["visitor_name"] = validated["visitor_name"].strip()
                if validated.get("company_name"):
                    validated["company_name"] = validated["company_name"].strip()
                if validated.get("purpose"):
                    validated["purpose"] = validated["purpose"].strip()
                    
            elif function_name == "check_appointment":
                # 必須フィールドの確認
                if not validated.get("visitor_name"):
                    raise ValueError("visitor_name is required")
                    
                # 日付フォーマット確認・補完
                if not validated.get("date"):
                    from datetime import datetime
                    validated["date"] = datetime.now().strftime("%Y-%m-%d")
                    
            elif function_name == "send_notification":
                # 必須フィールドの確認
                if not validated.get("visitor_info"):
                    raise ValueError("visitor_info is required")
                if not validated.get("message"):
                    raise ValueError("message is required")
                    
            elif function_name == "guide_visitor":
                # visitor_typeの検証
                valid_types = ["appointment", "sales", "delivery", "other"]
                if validated.get("visitor_type") not in valid_types:
                    validated["visitor_type"] = "other"
                    
            return validated
            
        except Exception as e:
            print(f"❌ Parameter validation error: {e}")
            raise ValueError(f"Invalid parameters for {function_name}: {e}")

    def _is_retryable_error(self, error: Exception) -> bool:
        """エラーがリトライ可能かチェック"""
        retryable_errors = [
            "ConnectionError", "TimeoutError", "HTTPException", 
            "TemporaryFailure", "ServiceUnavailable"
        ]
        
        error_name = error.__class__.__name__
        error_msg = str(error).lower()
        
        return (
            error_name in retryable_errors or
            "timeout" in error_msg or
            "connection" in error_msg or
            "temporarily unavailable" in error_msg
        )

    async def _post_function_execution(self, session_id: str, function_name: str, result: Dict[str, Any]) -> None:
        """Function Call実行後の処理"""
        try:
            # セッション状態の更新
            await self._update_session_context(session_id, function_name, result)
            
            # メトリクス収集
            await self._collect_function_metrics(session_id, function_name, result)
            
            # 後続処理の判定
            if function_name == "collect_visitor_info" and result.get("visitor_info"):
                # 来客者情報収集後に予約確認を提案
                await self._suggest_next_action(session_id, "check_appointment")
                
            elif function_name == "check_appointment" and result.get("appointment_found"):
                # 予約確認後にスタッフ通知を提案
                await self._suggest_next_action(session_id, "send_notification")
                
        except Exception as e:
            print(f"⚠️ Post-execution processing error: {e}")

    async def _update_session_context(self, session_id: str, function_name: str, result: Dict[str, Any]) -> None:
        """セッションコンテキストの更新"""
        # LangGraphのセッション状態に結果を反映
        context_update = {
            "last_function": function_name,
            "last_result": result,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        # LangGraphマネージャーに状態更新を送信
        await self.graph_manager.update_session_context(session_id, context_update)

    async def _collect_function_metrics(self, session_id: str, function_name: str, result: Dict[str, Any]) -> None:
        """Function Call実行メトリクスの収集"""
        metrics = {
            "function_name": function_name,
            "session_id": session_id,
            "success": result.get("success", True),
            "execution_time": result.get("execution_time", 0),
            "timestamp": asyncio.get_event_loop().time()
        }
        
        # メトリクス記録（非同期で実行）
        asyncio.create_task(self._record_metrics_async(metrics))

    async def _record_metrics_async(self, metrics: Dict[str, Any]) -> None:
        """メトリクス記録（非同期）"""
        try:
            # 実際のメトリクス収集システムへの送信
            # 現在は簡単なログ出力
            print(f"📊 Function Metrics: {metrics}")
        except Exception as e:
            print(f"⚠️ Metrics recording error: {e}")

    async def _suggest_next_action(self, session_id: str, suggested_action: str) -> None:
        """次のアクションの提案"""
        suggestion = {
            "type": "action_suggestion",
            "suggested_action": suggested_action,
            "session_id": session_id,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        print(f"💡 Action suggestion for {session_id}: {suggested_action}")

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
        """RealtimeセッションとLangGraphセッションの状態同期（強化版）"""
        try:
            sync_start_time = asyncio.get_event_loop().time()
            
            # LangGraphの現在状態を取得
            langgraph_state = await self.graph_manager.get_conversation_history(session_id)
            
            if not langgraph_state["success"]:
                # LangGraphセッションが存在しない場合は作成
                print(f"🔄 Creating new LangGraph session: {session_id}")
                init_result = await self.graph_manager.start_conversation(session_id)
                if init_result["success"]:
                    langgraph_state = await self.graph_manager.get_conversation_history(session_id)
                else:
                    raise Exception(f"Failed to create LangGraph session: {init_result.get('error')}")
            
            # Function Call実行履歴を取得
            function_history = await self.get_function_execution_history(session_id)
            
            # 状態統合と一貫性チェック
            synchronized_state = {
                "session_id": session_id,
                "sync_timestamp": asyncio.get_event_loop().time(),
                "langgraph": {
                    "current_step": langgraph_state.get("current_step"),
                    "visitor_info": langgraph_state.get("visitor_info"),
                    "calendar_result": langgraph_state.get("calendar_result"),
                    "message_count": len(langgraph_state.get("messages", [])),
                    "last_message": langgraph_state.get("messages", [])[-1] if langgraph_state.get("messages") else None
                },
                "realtime": {
                    "features": realtime_state.get("features", []),
                    "processing_mode": realtime_state.get("processing_mode", "realtime"),
                    "function_calls_count": len(function_history),
                    "last_function": function_history[-1] if function_history else None
                },
                "consistency_check": await self._check_state_consistency(langgraph_state, realtime_state, function_history),
                "sync_duration": asyncio.get_event_loop().time() - sync_start_time
            }
            
            # 状態の不整合があれば修復
            if not synchronized_state["consistency_check"]["consistent"]:
                repair_result = await self._repair_state_inconsistency(session_id, synchronized_state)
                synchronized_state["repair_performed"] = repair_result
            
            # 同期完了ログ
            print(f"🔄 Session state synchronized: {session_id} (duration: {synchronized_state['sync_duration']:.3f}s)")
            
            return {
                "success": True,
                "synchronized_state": synchronized_state
            }
            
        except Exception as e:
            print(f"❌ State sync error: {e}")
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id
            }

    async def _check_state_consistency(
        self, 
        langgraph_state: Dict[str, Any], 
        realtime_state: Dict[str, Any], 
        function_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """セッション状態の一貫性チェック"""
        consistency_issues = []
        
        try:
            # 来客者情報の一貫性チェック
            lg_visitor = langgraph_state.get("visitor_info")
            rt_visitor = realtime_state.get("visitor_info")
            
            if lg_visitor and rt_visitor:
                if lg_visitor.get("name") != rt_visitor.get("name"):
                    consistency_issues.append("visitor_name_mismatch")
                if lg_visitor.get("company") != rt_visitor.get("company"):
                    consistency_issues.append("visitor_company_mismatch")
            
            # Function Call履歴の整合性チェック
            expected_functions = self._analyze_required_functions(langgraph_state)
            executed_functions = [f["function_name"] for f in function_history if f["status"] == "completed"]
            
            missing_functions = set(expected_functions) - set(executed_functions)
            if missing_functions:
                consistency_issues.append(f"missing_functions: {list(missing_functions)}")
            
            # セッション進行状況の整合性
            lg_step = langgraph_state.get("current_step")
            if lg_step == "collect_visitor_info" and any(f["function_name"] == "collect_visitor_info" for f in function_history):
                if not any(f["status"] == "completed" for f in function_history if f["function_name"] == "collect_visitor_info"):
                    consistency_issues.append("incomplete_visitor_collection")
            
            return {
                "consistent": len(consistency_issues) == 0,
                "issues": consistency_issues,
                "score": max(0, 1 - len(consistency_issues) / 10)  # 一貫性スコア
            }
            
        except Exception as e:
            print(f"⚠️ Consistency check error: {e}")
            return {
                "consistent": False,
                "issues": [f"consistency_check_failed: {e}"],
                "score": 0
            }

    def _analyze_required_functions(self, langgraph_state: Dict[str, Any]) -> List[str]:
        """LangGraphの状態から必要なFunction Callsを分析"""
        required_functions = []
        
        current_step = langgraph_state.get("current_step")
        visitor_info = langgraph_state.get("visitor_info")
        
        # ステップベースの分析
        if current_step == "collect_visitor_info":
            required_functions.append("collect_visitor_info")
        elif current_step == "check_appointment":
            required_functions.extend(["collect_visitor_info", "check_appointment"])
        elif current_step == "notify_staff":
            required_functions.extend(["collect_visitor_info", "check_appointment", "send_notification"])
        
        # 来客者情報ベースの分析
        if visitor_info:
            if not visitor_info.get("appointment_checked"):
                required_functions.append("check_appointment")
            if visitor_info.get("requires_notification"):
                required_functions.append("send_notification")
        
        return list(set(required_functions))  # 重複除去

    async def _repair_state_inconsistency(self, session_id: str, synchronized_state: Dict[str, Any]) -> Dict[str, Any]:
        """状態不整合の修復"""
        repair_actions = []
        
        try:
            issues = synchronized_state["consistency_check"]["issues"]
            
            for issue in issues:
                if "visitor_name_mismatch" in issue:
                    # 来客者名の不整合を修復
                    repair_result = await self._repair_visitor_info_mismatch(session_id)
                    repair_actions.append({"action": "repair_visitor_info", "result": repair_result})
                
                elif "missing_functions" in issue:
                    # 未実行Function Callsの補完
                    missing_functions = issue.split(": ")[1] if ": " in issue else []
                    if isinstance(missing_functions, str):
                        import ast
                        missing_functions = ast.literal_eval(missing_functions)
                    
                    for func_name in missing_functions:
                        repair_result = await self._execute_missing_function(session_id, func_name)
                        repair_actions.append({"action": f"execute_{func_name}", "result": repair_result})
                
                elif "incomplete_visitor_collection" in issue:
                    # 不完全な来客者情報収集を再実行
                    repair_result = await self._retry_visitor_collection(session_id)
                    repair_actions.append({"action": "retry_visitor_collection", "result": repair_result})
            
            print(f"🔧 State repair completed for {session_id}: {len(repair_actions)} actions performed")
            
            return {
                "success": True,
                "actions_performed": repair_actions,
                "repairs_count": len(repair_actions)
            }
            
        except Exception as e:
            print(f"❌ State repair error: {e}")
            return {
                "success": False,
                "error": str(e),
                "actions_performed": repair_actions
            }

    async def _repair_visitor_info_mismatch(self, session_id: str) -> Dict[str, Any]:
        """来客者情報不整合の修復"""
        try:
            # LangGraphから最新の来客者情報を取得
            lg_state = await self.graph_manager.get_conversation_history(session_id)
            visitor_info = lg_state.get("visitor_info")
            
            if visitor_info:
                # Function Call履歴を更新
                update_params = {
                    "visitor_name": visitor_info.get("name"),
                    "company_name": visitor_info.get("company"),
                    "purpose": visitor_info.get("purpose")
                }
                
                result = await self._execute_collect_visitor_info(session_id, update_params)
                return {"success": True, "updated_info": update_params, "result": result}
            else:
                return {"success": False, "error": "No visitor info to repair with"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _execute_missing_function(self, session_id: str, function_name: str) -> Dict[str, Any]:
        """未実行Function Callの補完実行"""
        try:
            # 既存のセッション情報から適切なパラメーターを推定
            lg_state = await self.graph_manager.get_conversation_history(session_id)
            visitor_info = lg_state.get("visitor_info", {})
            
            if function_name == "check_appointment":
                params = {
                    "visitor_name": visitor_info.get("name", ""),
                    "date": visitor_info.get("date") or time.strftime("%Y-%m-%d")
                }
            elif function_name == "send_notification":
                params = {
                    "visitor_info": visitor_info,
                    "message": f"{visitor_info.get('name', 'お客様')}がいらっしゃいました"
                }
            elif function_name == "guide_visitor":
                params = {
                    "visitor_type": visitor_info.get("type", "other"),
                    "location": visitor_info.get("location", "")
                }
            else:
                return {"success": False, "error": f"Unknown function: {function_name}"}
            
            result = await self.execute_function_call(session_id, function_name, params)
            return {"success": True, "function_name": function_name, "result": result}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _retry_visitor_collection(self, session_id: str) -> Dict[str, Any]:
        """不完全な来客者情報収集の再試行"""
        try:
            # 最新の会話履歴から来客者情報を抽出
            lg_state = await self.graph_manager.get_conversation_history(session_id)
            messages = lg_state.get("messages", [])
            
            # 最新のメッセージから来客者情報を抽出（簡易版）
            visitor_name = ""
            company_name = ""
            purpose = ""
            
            for message in reversed(messages):
                content = message.get("content", "")
                if "と申します" in content or "です" in content:
                    # 名前抽出の簡易ロジック
                    words = content.split()
                    for word in words:
                        if word.endswith("と申します") or word.endswith("です"):
                            visitor_name = word.replace("と申します", "").replace("です", "")
                            break
            
            if visitor_name:
                params = {
                    "visitor_name": visitor_name,
                    "company_name": company_name,
                    "purpose": purpose
                }
                
                result = await self._execute_collect_visitor_info(session_id, params)
                return {"success": True, "extracted_info": params, "result": result}
            else:
                return {"success": False, "error": "Could not extract visitor information"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}

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