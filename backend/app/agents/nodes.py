import re
from datetime import datetime
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from ..models.conversation import ConversationState
from ..models.visitor import ConversationLog, VisitorInfo, VisitorType
from ..services.calendar_service import CalendarService
from ..services.slack_service import SlackService
from ..services.text_service import TextService


class ReceptionNodes:
    """LangGraph nodes for reception conversation flow"""

    def __init__(self) -> None:
        self.text_service = TextService()
        self.calendar_service = CalendarService()
        self.slack_service = SlackService()

    async def greeting_node(self, state: ConversationState) -> ConversationState:
        """AI-powered initial greeting to visitor - collect all info at once"""

        # Generate context-aware greeting that asks for company, name, and purpose
        context = f"""
現在時刻: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}
セッション: 新規訪問者

自然で温かみのある日本語で、企業受付として適切な挨拶をしてください。
以下を含めてください：
1. 歓迎の挨拶
2. 会社名・お名前・訪問目的を一度に確認依頼

丁寧で親しみやすい対応を心がけてください。
訪問者が一度の入力で必要な情報を全て提供できるように案内してください。
"""

        try:
            greeting_message = await self.text_service.generate_output(
                "音声受付システムの初回挨拶。簡潔に会社名、お名前、ご用件を伺う。入力例は不要。",
                context
            )
        except Exception as e:
            print(f"AI greeting generation error: {e}")
            # Fallback to static greeting (optimized for voice)
            greeting_message = """いらっしゃいませ。音声受付システムです。

会社名、お名前、ご用件をお聞かせください。"""

        ai_message = AIMessage(content=greeting_message)

        return {
            **state,
            "messages": [ai_message],
            "current_step": "collect_all_info",
            "error_count": 0
        }

    async def collect_name_node(self, state: ConversationState) -> ConversationState:
        """Collect visitor name and company information (simpler version for testing)"""
        last_message = state["messages"][-1]

        if not isinstance(last_message, HumanMessage):
            return {
                **state,
                "current_step": "name_collection",
                "error_count": state.get("error_count", 0) + 1
            }

        # Extract visitor info using the existing method
        visitor_info = self._extract_visitor_info(last_message.content)
        
        # Check if we have both name and company
        if not visitor_info["name"] or not visitor_info["company"]:
            # Missing information - ask for more details
            ai_message = AIMessage(content="申し訳ございませんが、会社名とお名前の両方を教えていただけますでしょうか？例：山田太郎、株式会社テストです。")
            
            return {
                **state,
                "messages": [ai_message],
                "current_step": "name_collection",
                "error_count": state.get("error_count", 0) + 1
            }

        # Information is complete - proceed to confirmation
        confirmation_message = f"""以下の情報で間違いございませんでしょうか？

・会社名：{visitor_info['company']}
・お名前：{visitor_info['name']}

情報が正しい場合は「はい」、修正が必要な場合は「いいえ」とお答えください。"""

        ai_message = AIMessage(content=confirmation_message)

        return {
            **state,
            "messages": [HumanMessage(content=last_message.content), ai_message],
            "visitor_info": visitor_info,
            "current_step": "confirmation",
            "error_count": 0
        }

    async def collect_all_info_node(self, state: ConversationState) -> ConversationState:
        """Collect visitor company, name and purpose information using AI"""
        last_message = state["messages"][-1]

        if not isinstance(last_message, HumanMessage):
            return {
                **state,
                "current_step": "collect_all_info",
                "error_count": state.get("error_count", 0) + 1
            }

        # Get existing visitor info if any
        existing_visitor_info = state.get("visitor_info") or {}

        # Use AI to extract all visitor information (company, name, purpose)
        new_visitor_info = await self._ai_extract_all_visitor_info(last_message.content, state)

        # Merge with existing information - keep existing values if new ones are empty
        merged_visitor_info = {
            "company": new_visitor_info.get("company") or existing_visitor_info.get("company", ""),
            "name": new_visitor_info.get("name") or existing_visitor_info.get("name", ""),
            "purpose": new_visitor_info.get("purpose") or existing_visitor_info.get("purpose", ""),
            "confidence": new_visitor_info.get("confidence", "low")
        }

        # Check if all required information is present
        missing_info = []
        if not merged_visitor_info.get("company"):
            missing_info.append("会社名")
        if not merged_visitor_info.get("name"):
            missing_info.append("お名前")
        if not merged_visitor_info.get("purpose"):
            missing_info.append("訪問目的")

        if missing_info:
            # Generate AI response for incomplete information
            conversation_history = self._format_conversation_history(state.get("messages", []))

            # Show what information we already have
            collected_info = []
            if merged_visitor_info.get("company"):
                collected_info.append(f"会社名: {merged_visitor_info['company']}")
            if merged_visitor_info.get("name"):
                collected_info.append(f"お名前: {merged_visitor_info['name']}")
            if merged_visitor_info.get("purpose"):
                collected_info.append(f"訪問目的: {merged_visitor_info['purpose']}")

            context = f"""
会話履歴:
{conversation_history}

既に取得済みの情報:
{chr(10).join(collected_info) if collected_info else "（なし）"}

ユーザーからの最新入力: "{last_message.content}"
エラー回数: {state.get("error_count", 0)}回目
不足している情報: {', '.join(missing_info)}

この会話の文脈を理解した上で、既に取得済みの情報は保持しつつ、不足している情報のみを自然で丁寧な日本語で教えてもらうよう案内してください。

重要：
- 既に取得済みの情報は再度聞かない
- 不足している情報のみを具体的に指摘する
- 会話の流れを考慮した自然な案内にする
- エラー回数が多い場合は、より分かりやすい説明をする
- 会社名やお名前を聞く場合は、「音声認識が難しい場合は、テキストで入力することもできます」と案内する
"""

            try:
                ai_response = await self.text_service.generate_output(
                    "全情報の収集（不足情報あり）",
                    context
                )
                ai_message = AIMessage(content=ai_response)
            except Exception as e:
                print(f"AI response error in collect_all_info: {e}")
                # Fallback message
                collected_info_str = ""
                if merged_visitor_info.get("company"):
                    collected_info_str += f"会社名：{merged_visitor_info['company']} "
                if merged_visitor_info.get("name"):
                    collected_info_str += f"お名前：{merged_visitor_info['name']} "
                if merged_visitor_info.get("purpose"):
                    collected_info_str += f"訪問目的：{merged_visitor_info['purpose']} "

                if collected_info_str:
                    ai_message = AIMessage(content=f"""申し訳ございません。
                    
取得済み情報：{collected_info_str.strip()}
不足している情報：{', '.join(missing_info)}

{missing_info[0]}を教えていただけますでしょうか？""")
                else:
                    ai_message = AIMessage(content=f"""申し訳ございません。以下の情報が不足しています：{', '.join(missing_info)}

例: 株式会社テストの山田太郎です。本日10時から貴社の田中様とお約束をいただいております。

音声認識が難しい場合は、テキストで入力することもできます。""")

            return {
                **state,
                "messages": [ai_message],
                "visitor_info": merged_visitor_info,  # Save partial information
                "current_step": "collect_all_info",
                "error_count": state.get("error_count", 0) + 1
            }

        # All information collected - generate confirmation message
        user_message = state["messages"][-1]

        # Generate confirmation message
        context = f"""
収集した訪問者情報:
- 会社名: {merged_visitor_info.get('company', '不明')}
- お名前: {merged_visitor_info.get('name', '不明')}
- 訪問目的: {merged_visitor_info.get('purpose', '不明')}

この情報をユーザーに確認してもらうメッセージを生成してください。
以下を含めてください：
1. 収集した情報の提示
2. 情報が正しいかの確認依頼
3. 修正が必要な場合の案内

自然で丁寧な日本語で、分かりやすく確認を求めてください。
"""

        try:
            confirmation_message = await self.text_service.generate_output(
                "訪問者情報の確認依頼",
                context
            )
        except Exception as e:
            print(f"AI response error in collect_all_info confirmation: {e}")
            # Fallback confirmation message
            confirmation_message = f"""以下の情報で間違いございませんでしょうか？

・会社名：{merged_visitor_info.get('company', '不明')}
・お名前：{merged_visitor_info.get('name', '不明')}  
・訪問目的：{merged_visitor_info.get('purpose', '不明')}

情報が正しい場合は「はい」、修正が必要な場合は「いいえ」とお答えください。
修正の場合は、正しい情報を教えてください。"""

        ai_message = AIMessage(content=confirmation_message)

        return {
            **state,
            "messages": [user_message, ai_message],
            "visitor_info": merged_visitor_info,
            "current_step": "confirmation_response",
            "error_count": 0
        }

    async def confirm_info_node(self, state: ConversationState) -> ConversationState:
        """Confirm all visitor information with user"""
        visitor_info = state.get("visitor_info", {})

        # If this is the first time reaching confirmation, show the collected info
        # Check if the last message was from collection or if this is initial confirmation display
        last_message = state.get("messages", [])[-1] if state.get("messages") else None
        is_initial_confirmation = (
            state.get("current_step") == "confirmation" and
            (not last_message or not isinstance(last_message, HumanMessage) or
             "株式会社" in last_message.content or "です" in last_message.content)  # Likely the collection input
        )

        if is_initial_confirmation:
            # Generate confirmation message showing all collected information
            context = f"""
収集した訪問者情報:
- 会社名: {visitor_info.get('company', '不明')}
- お名前: {visitor_info.get('name', '不明')}
- 訪問目的: {visitor_info.get('purpose', '不明')}

この情報をユーザーに確認してもらうメッセージを生成してください。
以下を含めてください：
1. 収集した情報の提示
2. 情報が正しいかの確認依頼
3. 修正が必要な場合の案内

自然で丁寧な日本語で、分かりやすく確認を求めてください。
"""

            try:
                confirmation_message = await self.text_service.generate_output(
                    "訪問者情報の確認依頼",
                    context
                )
            except Exception as e:
                print(f"AI response error in info confirmation: {e}")
                # Fallback confirmation message
                confirmation_message = f"""以下の情報で間違いございませんでしょうか？

・会社名：{visitor_info.get('company', '不明')}
・お名前：{visitor_info.get('name', '不明')}  
・訪問目的：{visitor_info.get('purpose', '不明')}

情報が正しい場合は「はい」、修正が必要な場合は「いいえ」とお答えください。
修正の場合は、正しい情報を教えてください。"""

            ai_message = AIMessage(content=confirmation_message)

            return {
                **state,
                "messages": [ai_message],
                "current_step": "confirmation_response",
                "error_count": 0
            }

        # Handle user's confirmation response
        last_message = state["messages"][-1]
        if not isinstance(last_message, HumanMessage):
            return state

        # Use AI to understand confirmation intent
        confirmation_result = await self._ai_understand_confirmation_response(last_message.content, state)

        if confirmation_result["intent"] == "confirmed":
            # Information confirmed - proceed to visitor type processing
            visitor_info["confirmed"] = True

            # Check if purpose is already set to avoid redundant questions
            if visitor_info.get("purpose"):
                # Purpose already collected, proceed directly to processing
                try:
                    ai_response = await self.text_service.generate_output(
                        "情報確認完了の案内（処理開始）",
                        f"""訪問者情報が確認されました：
- 会社名: {visitor_info.get('company')}
- 名前: {visitor_info.get('name')}  
- 目的: {visitor_info.get('purpose')}

確認完了を伝え、カレンダー確認等の次の処理を進めることを自然な日本語で案内してください。"""
                    )
                except Exception as e:
                    print(f"AI response error in confirmation completion: {e}")
                    ai_response = "ありがとうございます。確認いたしました。処理を進めさせていただきます。"

                ai_message = AIMessage(content=ai_response)

                # Determine visitor type from purpose and proceed automatically
                purpose = visitor_info.get('purpose', '')
                purpose_lower = purpose.lower()

                if any(word in purpose_lower for word in ["予約", "会議", "打ち合わせ", "アポ", "appointment", "ミーティング"]):
                    visitor_type = "appointment"
                elif any(word in purpose_lower for word in ["営業", "商談", "提案", "sales", "セールス"]):
                    visitor_type = "sales"
                elif any(word in purpose_lower for word in ["配達", "荷物", "宅配", "delivery", "配送"]):
                    visitor_type = "delivery"
                else:
                    visitor_type = "appointment"  # Default to appointment

                visitor_info["visitor_type"] = visitor_type

                print(f"🎯 Auto-determined visitor type: {visitor_type} from purpose: {purpose}")

                # Execute the appropriate flow immediately
                if visitor_type == "appointment":
                    print("🔄 Auto-proceeding to calendar check for appointment")
                    updated_state = {
                        **state,
                        "messages": [ai_message],
                        "visitor_info": visitor_info,
                        "current_step": "appointment_check"
                    }

                    # Execute calendar check immediately
                    calendar_result = await self.check_appointment_node(updated_state)

                    # Then proceed to guidance and Slack notification
                    if calendar_result.get("current_step") == "guidance":
                        print("🔄 Auto-proceeding to guidance after calendar check")
                        guidance_result = await self.guide_visitor_node(calendar_result)

                        # Then send Slack notification
                        if guidance_result.get("current_step") == "complete":
                            print("✅ Auto-proceeding to Slack notification")
                            slack_result = await self.send_slack_node(guidance_result)
                            return slack_result
                        else:
                            return guidance_result
                    else:
                        return calendar_result
                else:
                    print(f"🔄 Auto-proceeding to guidance for {visitor_type}")
                    updated_state = {
                        **state,
                        "messages": [ai_message],
                        "visitor_info": visitor_info,
                        "current_step": "guidance"
                    }

                    # Execute guidance immediately for sales/delivery
                    guidance_result = await self.guide_visitor_node(updated_state)

                    # Then send Slack notification
                    if guidance_result.get("current_step") == "complete":
                        print("✅ Auto-proceeding to Slack notification")
                        slack_result = await self.send_slack_node(guidance_result)
                        return slack_result
                    else:
                        return guidance_result
            else:
                # Purpose not set, need to ask for it
                try:
                    ai_response = await self.text_service.generate_output(
                        "情報確認完了の案内（目的質問）",
                        "訪問者の会社名と名前は確認されましたが、訪問目的がまだ不明です。目的を確認するよう自然な日本語で案内してください。"
                    )
                except Exception as e:
                    print(f"AI response error in confirmation completion: {e}")
                    ai_response = "ありがとうございます。確認いたしました。訪問目的を教えていただけますでしょうか？"

                ai_message = AIMessage(content=ai_response)

                return {
                    **state,
                    "messages": [ai_message],
                    "visitor_info": visitor_info,
                    "current_step": "process_visitor_type",
                    "error_count": 0
                }

        elif confirmation_result["intent"] == "correction":
            # User wants to make corrections
            corrected_info = confirmation_result.get("corrected_info", {})

            # Update visitor info with corrections if provided
            if corrected_info:
                visitor_info.update(corrected_info)

                # Generate updated confirmation message with corrected info
                context = f"""
修正後の訪問者情報:
- 会社名: {visitor_info.get('company', '不明')}
- お名前: {visitor_info.get('name', '不明')}
- 訪問目的: {visitor_info.get('purpose', '不明')}

修正された情報を元に、再度確認をお願いするメッセージを生成してください。
以下を含めてください：
1. 修正反映の確認
2. 更新された情報の提示
3. 再確認の依頼

自然で丁寧な日本語で、分かりやすく再確認を求めてください。
"""

                try:
                    reconfirmation_message = await self.text_service.generate_output(
                        "修正後の再確認依頼",
                        context
                    )
                except Exception as e:
                    print(f"AI response error in reconfirmation: {e}")
                    # Fallback reconfirmation message
                    reconfirmation_message = f"""修正いたしました。以下の情報で間違いございませんでしょうか？

・会社名：{visitor_info.get('company', '不明')}
・お名前：{visitor_info.get('name', '不明')}  
・訪問目的：{visitor_info.get('purpose', '不明')}

情報が正しい場合は「はい」、さらに修正が必要な場合は修正内容をお教えください。"""

                ai_message = AIMessage(content=reconfirmation_message)

                return {
                    **state,
                    "messages": [ai_message],
                    "visitor_info": visitor_info,
                    "current_step": "confirmation_response",
                    "error_count": 0
                }
            else:
                # No specific corrections provided, ask for complete re-entry
                try:
                    correction_message = await self.text_service.generate_output(
                        "情報修正の案内",
                        "訪問者が情報修正を希望しています。全ての情報（会社名・名前・訪問目的）を再度入力してもらうよう、自然で丁寧な日本語で案内してください。"
                    )
                except Exception as e:
                    print(f"AI response error in correction request: {e}")
                    correction_message = """承知いたしました。お手数ですが、会社名・お名前・訪問目的を再度教えてください。

例: 株式会社テストの山田太郎です。本日10時から貴社の田中様とお約束をいただいております。"""

                ai_message = AIMessage(content=correction_message)

                return {
                    **state,
                    "messages": [ai_message],
                    "visitor_info": {},  # Clear visitor info for re-collection
                    "current_step": "collect_all_info",
                    "error_count": 0
                }

        else:
            # Unclear response - ask for clarification
            try:
                error_message = await self.text_service.generate_output(
                    "曖昧な確認回答への対応",
                    f"""ユーザーの入力: "{last_message.content}"
                    
ユーザーの回答が曖昧で、確認か修正かが分からない状況です。
「はい」「いいえ」または具体的な修正内容を教えてもらうよう、自然で丁寧な日本語で案内してください。"""
                )
            except Exception as e:
                print(f"AI response error in unclear confirmation: {e}")
                error_message = """申し訳ございません。「はい」または「いいえ」でお答えください。

情報が正しい場合は「はい」
修正が必要な場合は「いいえ」または修正内容を直接お教えください。"""

            ai_message = AIMessage(content=error_message)

            return {
                **state,
                "messages": [ai_message],
                "current_step": "confirmation_response",
                "error_count": state.get("error_count", 0) + 1
            }

    async def detect_type_node(self, state: ConversationState) -> ConversationState:
        """Ask visitor for their visit purpose using AI"""
        visitor_info = state.get("visitor_info") or {}
        name = visitor_info.get("name", "")
        company = visitor_info.get("company", "")
        conversation_history = self._format_conversation_history(state.get("messages", []))

        # Use AI to generate a natural question about visit purpose
        context = f"""
会話履歴:
{conversation_history}

訪問者情報:
- 会社名: {company}
- お名前: {name}

この会話の文脈を理解した上で、訪問者の来訪目的を自然に質問してください。

重要：
- 選択肢は提示せず、自然な会話形式で目的を聞く
- 「どのようなご用件でしょうか？」のような自然な質問にする
- 訪問者が自由に答えられる形にする
- 予約、営業、配達のいずれかを判定できるよう、オープンな質問をする
"""

        try:
            # Generate AI question for visitor type
            ai_response = await self.text_service.generate_output(
                "訪問目的の確認",
                context
            )

            ai_message = AIMessage(content=ai_response)

            return {
                **state,
                "messages": [ai_message],
                "visitor_info": visitor_info,
                "current_step": "visitor_type_response"  # Wait for user response
            }

        except Exception as e:
            print(f"AI type detection error: {e}")
            # Fallback question
            fallback_message = f"""ありがとうございます、{company}の{name}様。

本日はどのようなご用件でお越しでしょうか？"""

            ai_message = AIMessage(content=fallback_message)

            return {
                **state,
                "messages": [ai_message],
                "visitor_info": visitor_info,
                "current_step": "visitor_type_response"
            }

    async def process_visitor_type_node(self, state: ConversationState) -> ConversationState:
        """Process visitor's response about their visit purpose using AI"""
        last_message = state["messages"][-1]

        if not isinstance(last_message, HumanMessage):
            return {
                **state,
                "current_step": "visitor_type_response",
                "error_count": state.get("error_count", 0) + 1
            }

        visitor_info = state.get("visitor_info") or {}
        conversation_history = self._format_conversation_history(state.get("messages", []))

        # Use AI to understand visitor's response and determine type
        context = f"""
会話履歴:
{conversation_history}

訪問者情報:
- お名前: {visitor_info.get('name', '不明')}
- 会社名: {visitor_info.get('company', '不明')}

ユーザーの最新回答: "{last_message.content}"

この会話の文脈と訪問者の回答を理解して、訪問タイプを判定してください。

判定結果をJSON形式で返してください：
{{
    "visitor_type": "appointment|sales|delivery",
    "confidence": "high|medium|low",
    "response_message": "訪問者への返答メッセージ"
}}

判定基準：
- "appointment": 予約済み、会議、打ち合わせ、アポイントメント等
- "sales": 営業、商談、提案、新規開拓等  
- "delivery": 配達、荷物、宅配、郵便物等

response_messageは次のステップへの自然な案内を含めてください：
- appointmentの場合: カレンダー確認を行う旨
- sales/deliveryの場合: 適切な案内を行う旨
"""

        try:
            ai_response = await self.text_service.generate_output(
                "訪問目的の判定と回答",
                context
            )

            # Parse AI response
            import json
            import re

            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                visitor_type = result.get("visitor_type", "appointment")
                response_message = result.get("response_message", "承知いたしました。")
                confidence = result.get("confidence", "medium")

                # Update visitor info
                visitor_info["visitor_type"] = visitor_type

                ai_message = AIMessage(content=response_message)

                # Determine next step based on visitor type
                if visitor_type == "appointment":
                    # For appointments, immediately proceed to calendar check
                    updated_state = {
                        **state,
                        "messages": [ai_message],
                        "visitor_info": visitor_info,
                        "current_step": "appointment_check"
                    }

                    # Execute calendar check immediately
                    print("🔄 Executing calendar check immediately for appointment...")
                    calendar_result = await self.check_appointment_node(updated_state)
                    return calendar_result
                else:
                    return {
                        **state,
                        "messages": [ai_message],
                        "visitor_info": visitor_info,
                        "current_step": "guidance"
                    }

        except Exception as e:
            print(f"AI visitor type processing error: {e}")

        # Fallback processing
        user_response = last_message.content.lower()

        if any(word in user_response for word in ["1", "予約", "会議", "打ち合わせ", "アポ", "appointment"]):
            visitor_type = "appointment"
            message = "承知いたしました。カレンダーを確認いたします。少々お待ちください..."
        elif any(word in user_response for word in ["2", "営業", "商談", "提案", "sales"]):
            visitor_type = "sales"
            message = "営業でのご訪問ですね。承知いたしました。"
        elif any(word in user_response for word in ["3", "配達", "荷物", "宅配", "delivery"]):
            visitor_type = "delivery"
            message = "配達でお越しいただいたのですね。承知いたしました。"
        else:
            # Default to appointment for unclear responses
            visitor_type = "appointment"
            message = "承知いたしました。念のためカレンダーを確認いたします。"

        visitor_info["visitor_type"] = visitor_type
        ai_message = AIMessage(content=message)

        if visitor_type == "appointment":
            # For appointments, immediately proceed to calendar check
            updated_state = {
                **state,
                "messages": [ai_message],
                "visitor_info": visitor_info,
                "current_step": "appointment_check"
            }

            # Execute calendar check immediately
            print("🔄 Executing calendar check immediately for appointment (fallback)...")
            calendar_result = await self.check_appointment_node(updated_state)
            return calendar_result
        else:
            return {
                **state,
                "messages": [ai_message],
                "visitor_info": visitor_info,
                "current_step": "guidance"
            }

    async def check_appointment_node(self, state: ConversationState) -> ConversationState:
        """Check calendar for appointments"""
        visitor_info = state.get("visitor_info") or {}
        visitor_name = visitor_info.get("name", "")

        try:
            print(f"📅 Checking calendar for appointment: {visitor_name}")

            # Check today's reservations
            calendar_result = await self.calendar_service.check_todays_reservations(visitor_name)

            # Create AI message based on calendar result
            ai_message = AIMessage(content=calendar_result.get("message", "カレンダーをチェックしました。"))

            return {
                **state,
                "messages": [ai_message],
                "calendar_result": calendar_result,
                "current_step": "guidance"
            }

        except Exception as e:
            print(f"❌ Calendar check error: {e}")

            # Error handling - proceed to guidance with error info
            calendar_result = {
                "found": False,
                "error": True,
                "message": "システムエラーが発生しました。スタッフをお呼びします。"
            }

            error_message = AIMessage(content="申し訳ございません。システムの不具合が発生しました。スタッフをお呼びいたします。")

            return {
                **state,
                "messages": [error_message],
                "calendar_result": calendar_result,
                "current_step": "guidance"
            }

    async def guide_visitor_node(self, state: ConversationState) -> ConversationState:
        """Provide AI-generated guidance based on visitor type and calendar results"""
        visitor_info = state.get("visitor_info") or {}
        visitor_type = visitor_info.get("visitor_type", "unknown")
        calendar_result = state.get("calendar_result") or {}

        # Generate AI-powered guidance message
        guidance_message = await self._ai_generate_guidance_message(visitor_type, calendar_result, visitor_info)

        ai_message = AIMessage(content=guidance_message)

        return {
            **state,
            "messages": [ai_message],
            "current_step": "complete"
        }

    async def send_slack_node(self, state: ConversationState) -> ConversationState:
        """Send notification to Slack"""
        visitor_info = state["visitor_info"]
        messages = state["messages"]
        calendar_result = state.get("calendar_result")

        # Convert messages to conversation logs
        conversation_logs = []
        for msg in messages:
            if isinstance(msg, (HumanMessage, AIMessage)):
                speaker = "visitor" if isinstance(msg, HumanMessage) else "ai"
                log: ConversationLog = {
                    "timestamp": datetime.now(),
                    "speaker": speaker,
                    "message": msg.content
                }
                conversation_logs.append(log)

        try:
            # Send Slack notification
            await self.slack_service.send_visitor_notification(
                visitor_info,
                conversation_logs,
                calendar_result
            )
        except Exception as e:
            print(f"Slack notification error: {e}")

        return {
            **state,
            "current_step": "complete"
        }

    async def _ai_extract_visitor_info(self, input_text: str, state: ConversationState) -> VisitorInfo:
        """Extract visitor information using AI understanding with conversation context"""
        try:
            # Include conversation history for context
            conversation_history = self._format_conversation_history(state.get("messages", []))
            error_count = state.get("error_count", 0)

            context = f"""
会話履歴:
{conversation_history}

エラー回数: {error_count}回目

現在のユーザー入力: "{input_text}"

この会話の文脈を理解した上で、ユーザーの入力から以下の情報を抽出してください：
1. 会社・組織名
2. 訪問者の名前（姓名）

抽出結果をJSON形式で返してください：
{{
    "company": "抽出した会社名",
    "name": "抽出した名前（姓名を含む完全な名前）",
    "confidence": "high|medium|low（抽出の確信度）"
}}

重要：
- 会話の流れを考慮してください
- 会社名を先に、名前を後に記載する順番を推奨します
- 過去に情報の修正があった場合は、最新の情報を優先してください
- エラー回数が多い場合は、より柔軟に情報を抽出してください

入力例：
- "株式会社テスト、山田太郎です" → {{"company": "株式会社テスト", "name": "山田太郎", "confidence": "high"}}
- "アマゾンの田中と申します" → {{"company": "アマゾン", "name": "田中", "confidence": "medium"}}
- "佐藤です" → {{"company": "", "name": "佐藤", "confidence": "low"}}

情報が不足している場合は、確信度を"low"にし、空文字列を使用してください。
"""

            ai_response = await self.text_service.generate_output(
                "JSON形式で情報を抽出",
                context
            )

            # Try to parse JSON response
            import json
            import re

            # Extract JSON from AI response
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                extracted_data = json.loads(json_match.group())

                name = extracted_data.get("name", "").strip()
                company = extracted_data.get("company", "").strip()
                confidence = extracted_data.get("confidence", "low")

                # Only accept if confidence is medium or high
                if confidence == "low":
                    name = ""
                    company = ""

                return VisitorInfo(
                    name=name,
                    company=company,
                    visitor_type=None,
                    confirmed=False,
                    correction_count=0
                )

        except Exception as e:
            print(f"AI extraction error: {e}")

        # Fallback to regex extraction
        return self._extract_visitor_info(input_text)

    async def _ai_extract_all_visitor_info(self, input_text: str, state: ConversationState) -> dict[str, Any]:
        """Extract all visitor information (company, name, purpose) using AI"""
        try:
            conversation_history = self._format_conversation_history(state.get("messages", []))
            error_count = state.get("error_count", 0)
            existing_visitor_info = state.get("visitor_info") or {}

            context = f"""
会話履歴:
{conversation_history}

既存の訪問者情報:
- 会社名: {existing_visitor_info.get('company', '未取得')}
- 名前: {existing_visitor_info.get('name', '未取得')}
- 訪問目的: {existing_visitor_info.get('purpose', '未取得')}

エラー回数: {error_count}回目
現在のユーザー入力: "{input_text}"

この会話の全体的な文脈を理解した上で、現在のユーザー入力から新しい情報を抽出してください。
既存の情報も考慮し、新しい入力で補完または更新される情報を抽出してください。

抽出結果をJSON形式で返してください：
{{
    "company": "抽出した会社名（既存情報で十分な場合は既存値、空の場合は空文字列）",
    "name": "抽出した名前（既存情報で十分な場合は既存値、空の場合は空文字列）",
    "purpose": "抽出した訪問目的（現在の入力から抽出、空の場合は空文字列）",
    "confidence": "high|medium|low（全体的な抽出の確信度）"
}}

訪問目的の抽出例：
- "打ち合わせ" "打ち合わせできました" "打ち合わせで来ました" → "予約会議"
- "営業" "営業で伺いました" "営業訪問です" → "営業"  
- "配達" "荷物を持参しました" → "配達"
- "面談" "面接" → "面談"

重要：
- 既存の情報がある場合は、それを保持しつつ新しい情報を追加
- 訪問目的は「打ち合わせ」「営業」「配達」など、自然な表現から適切に抽出
- 会話の文脈全体を理解して判断する
"""

            ai_response = await self.text_service.generate_output(
                "全情報をJSON形式で抽出",
                context
            )

            # Parse JSON response
            import json
            import re

            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                extracted_data = json.loads(json_match.group())

                return {
                    "company": extracted_data.get("company", "").strip(),
                    "name": extracted_data.get("name", "").strip(),
                    "purpose": extracted_data.get("purpose", "").strip(),
                    "confidence": extracted_data.get("confidence", "low")
                }

        except Exception as e:
            print(f"AI all info extraction error: {e}")

        # Fallback extraction with purpose detection
        visitor_info = self._extract_visitor_info(input_text)

        # Simple purpose extraction for fallback
        purpose = ""
        input_lower = input_text.lower()
        if any(word in input_lower for word in ["打ち合わせ", "会議", "面談", "アポ"]):
            purpose = "予約会議"
        elif any(word in input_lower for word in ["営業", "商談", "提案"]):
            purpose = "営業"
        elif any(word in input_lower for word in ["配達", "荷物", "宅配"]):
            purpose = "配達"
        elif "面接" in input_lower:
            purpose = "面接"

        return {
            "company": visitor_info.get("company", ""),
            "name": visitor_info.get("name", ""),
            "purpose": purpose,
            "confidence": "low"
        }

    async def _ai_understand_confirmation_response(self, user_input: str, state: ConversationState) -> dict[str, Any]:
        """Use AI to understand user's confirmation response and extract corrections if any"""
        try:
            conversation_history = self._format_conversation_history(state.get("messages", []))
            visitor_info = state.get("visitor_info", {})

            context = f"""
会話履歴:
{conversation_history}

確認対象の情報:
- 会社名: {visitor_info.get('company', '不明')}
- 名前: {visitor_info.get('name', '不明')}
- 訪問目的: {visitor_info.get('purpose', '不明')}

現在のユーザー入力: "{user_input}"

ユーザーの発言を分析し、以下のJSON形式で返してください：
{{
    "intent": "confirmed|correction|unclear",
    "corrected_info": {{
        "company": "修正された会社名（修正がない場合は省略）",
        "name": "修正された名前（修正がない場合は省略）", 
        "purpose": "修正された訪問目的（修正がない場合は省略）"
    }}
}}

判定基準：
1. "confirmed" - 情報が正しいと確認
   - 「はい」「そうです」「正しいです」「間違いありません」「あってます」「合ってます」「その通り」など
   - 自然な日本語での肯定表現を幅広く認識する
   
2. "correction" - 修正が必要
   - 「いいえ」「違います」「間違っています」「違う」など否定表現
   - または具体的な修正内容が含まれている場合
   
3. "unclear" - 意図が不明確
   - 上記以外の曖昧な回答

修正内容が具体的に含まれている場合は、corrected_infoに抽出してください。

例：
- "はい、正しいです" → {{"intent": "confirmed"}}
- "あってます" → {{"intent": "confirmed"}}
- "合ってる" → {{"intent": "confirmed"}}
- "その通りです" → {{"intent": "confirmed"}}
- "いいえ、会社名は株式会社ABCです" → {{"intent": "correction", "corrected_info": {{"company": "株式会社ABC"}}}}
- "名前は田中次郎です" → {{"intent": "correction", "corrected_info": {{"name": "田中次郎"}}}}
"""

            ai_response = await self.text_service.generate_output(
                "確認応答の理解と修正抽出",
                context
            )

            # Parse JSON response
            import json
            import re

            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    "intent": result.get("intent", "unclear"),
                    "corrected_info": result.get("corrected_info", {})
                }

        except Exception as e:
            print(f"AI confirmation response understanding error: {e}")

        # Enhanced fallback keyword matching with more natural Japanese expressions
        user_lower = user_input.lower().strip()

        # Positive confirmations - expanded list
        positive_words = [
            "はい", "yes", "正しい", "間違いない", "そうです", "ok", "オーケー",
            "あってます", "あってる", "合ってます", "合ってる", "その通り", "正解",
            "間違いありません", "問題ありません", "大丈夫", "うん", "ええ", "そう",
            "確認しました", "確認できました", "よろしく", "お願いします"
        ]

        # Negative responses - expanded list
        negative_words = [
            "いいえ", "no", "違い", "間違い", "修正", "訂正", "変更",
            "違います", "間違ってます", "間違っています", "ちがう", "だめ",
            "ノー", "エヌジー", "ng", "不正確", "不正解"
        ]

        if any(word in user_lower for word in positive_words):
            return {"intent": "confirmed", "corrected_info": {}}
        elif any(word in user_lower for word in negative_words):
            return {"intent": "correction", "corrected_info": {}}
        else:
            return {"intent": "unclear", "corrected_info": {}}

    async def _ai_understand_confirmation(self, user_input: str, state: ConversationState) -> str:
        """Use AI to understand user's confirmation intent with conversation context"""
        try:
            # Include conversation history for context
            conversation_history = self._format_conversation_history(state.get("messages", []))
            visitor_info = state.get("visitor_info", {})

            context = f"""
会話履歴:
{conversation_history}

確認対象の情報:
- 名前: {visitor_info.get('name', '不明')}
- 会社: {visitor_info.get('company', '不明')}

現在のユーザー入力: "{user_input}"

この会話の文脈を理解した上で、ユーザーの最新の発言の意図を判断してください：

1. "confirmed" - 上記の情報が正しいと確認している
2. "denied" - 上記の情報が間違っているため修正したい  
3. "unclear" - 意図が不明確で再確認が必要

重要：
- 会話の流れを考慮して判断してください
- 何に対する「はい」「いいえ」なのかを文脈から理解してください
- 情報確認の文脈での発言であることを念頭に置いてください

判定結果を1単語で返してください: confirmed, denied, または unclear

判定例：
- "はい" → confirmed (情報が正しい)
- "そうです" → confirmed (情報が正しい)
- "正しいです" → confirmed (情報が正しい)
- "OK" → confirmed (情報が正しい)
- "いいえ" → denied (情報が間違っている)
- "違います" → denied (情報が間違っている)
- "間違っています" → denied (情報が間違っている)
- "修正します" → denied (情報が間違っている)
- "よくわからない" → unclear (意図不明)
- "もう一度" → unclear (意図不明)
"""

            ai_response = await self.text_service.generate_output(
                "確認意図の判定",
                context
            )

            # Extract the intent from AI response
            response_lower = ai_response.lower().strip()

            if "confirmed" in response_lower:
                return "confirmed"
            elif "denied" in response_lower:
                return "denied"
            else:
                return "unclear"

        except Exception as e:
            print(f"AI confirmation understanding error: {e}")

            # Fallback to simple keyword matching
            user_lower = user_input.lower().strip()

            if any(word in user_lower for word in ["はい", "yes", "正しい", "間違いない", "そうです", "ok"]):
                return "confirmed"
            elif any(word in user_lower for word in ["いいえ", "no", "違い", "間違い", "修正"]):
                return "denied"
            else:
                return "unclear"

    def _format_conversation_history(self, messages: list) -> str:
        """Format conversation history for AI context"""
        history = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                history.append(f"訪問者: {msg.content}")
            elif isinstance(msg, AIMessage):
                history.append(f"受付AI: {msg.content}")

        return "\n".join(history) if history else "（会話履歴なし）"

    async def _ai_generate_guidance_message(
        self,
        visitor_type: str,
        calendar_result: dict[str, Any],
        visitor_info: dict[str, Any]
    ) -> str:
        """Generate AI-powered guidance message based on visitor context"""

        try:
            # Create comprehensive context for AI
            context = f"""
訪問者情報:
- 名前: {visitor_info.get('name', 'unknown')}
- 会社: {visitor_info.get('company', 'unknown')}
- 訪問タイプ: {visitor_type}

カレンダー確認結果:
"""

            if calendar_result:
                context += f"""
- 予約発見: {'あり' if calendar_result.get('found') else 'なし'}
- 会議室: {calendar_result.get('roomName', 'N/A')}
- エラー: {'あり' if calendar_result.get('error') else 'なし'}
"""
                if calendar_result.get('events'):
                    context += f"- 予約詳細: {len(calendar_result['events'])}件の予約\n"
            else:
                context += "- カレンダー確認未実施\n"

            context += """

以下の状況に基づいて、適切な案内メッセージを生成してください:

1. 予約来訪者で予約確認済み → 会議室案内、感謝の言葉
2. 予約来訪者で予約未確認 → 丁寧な謝罪、事前予約制の説明、お引き取りのお願い
3. 営業訪問者 → 丁寧なお断り、名刺受け取りの案内
4. 配達業者 → 配達手順の案内（置き配、サイン等）
5. その他・不明 → スタッフ呼び出しの案内

自然で丁寧な日本語で、状況に最適な案内を生成してください。
相手の立場に立った、思いやりのある対応を心がけてください。
"""

            ai_response = await self.text_service.generate_output(
                "訪問者への最終案内",
                context
            )

            return ai_response

        except Exception as e:
            print(f"AI guidance generation error: {e}")

            # Fallback to template-based guidance
            visitor_type_literal = "appointment" if visitor_type == "appointment" else \
                                 "sales" if visitor_type == "sales" else \
                                 "delivery" if visitor_type == "delivery" else "appointment"

            # Convert dict to VisitorInfo for fallback
            visitor_info_obj = VisitorInfo(
                name=visitor_info.get("name", ""),
                company=visitor_info.get("company", ""),
                visitor_type=visitor_type_literal,
                confirmed=visitor_info.get("confirmed", False),
                correction_count=visitor_info.get("correction_count", 0)
            )

            return self._generate_guidance_message(visitor_type_literal, calendar_result, visitor_info_obj)

    def _extract_visitor_info(self, input_text: str) -> VisitorInfo:
        """Extract visitor information from input text"""
        # Simple regex patterns for Japanese names and companies
        patterns = [
            # English full name with company
            r'([A-Za-z]+\s+[A-Za-z]+),\s*([A-Za-z\s]+(?:Corp|Inc|Ltd|Company).*?)(?:です)?$',
            # Company format with "です" suffix
            r'([^\s,、]+)[,、\s]+(.*?株式会社.*?)(?:です)?$',
            r'([^\s,、]+)[,、\s]+(.*?会社.*?)(?:です)?$',
            r'([^\s,、]+)[,、\s]+(.*?Corp.*?)(?:です)?$',
            r'([^\s,、]+)[,、\s]+(.*?Ltd.*?)(?:です)?$',
            r'([^\s,、]+)[,、\s]+(.*?Inc.*?)(?:です)?$',
            # General name and company pattern
            r'([^\s,、]+)[,、\s]+([^\s,、]+?)(?:です)?$',
        ]

        name = ""
        company = ""

        for pattern in patterns:
            match = re.search(pattern, input_text)
            if match:
                name = match.group(1).strip()
                company = match.group(2).strip()
                # Remove trailing "です" from company name
                if company.endswith('です'):
                    company = company[:-2]
                break

        # Handle single name without company
        if not name and not company:
            # Try to extract just a name
            name_match = re.search(r'([^\s,、]+)', input_text)
            if name_match:
                name = name_match.group(1).strip()

        return VisitorInfo(
            name=name,
            company=company,
            visitor_type=None,
            confirmed=False,
            correction_count=0
        )

    def _detect_visitor_type(self, visitor_info: VisitorInfo) -> VisitorType:
        """Detect visitor type based on company name and context"""
        company = visitor_info["company"].lower()

        # Delivery companies
        delivery_keywords = ["宅急便", "宅配", "配送", "配達", "ヤマト", "佐川", "郵便", "ups", "dhl", "fedex", "アマゾン", "amazon"]
        if any(keyword in company for keyword in delivery_keywords):
            return "delivery"

        # Sales indicators (generic company names or sales-related terms)
        sales_keywords = ["営業", "販売", "セールス", "商品", "商談", "紹介", "サービス", "ソリューション"]
        if any(keyword in company for keyword in sales_keywords):
            return "sales"

        # Default to appointment for other cases
        return "appointment"

    def _generate_guidance_message(
        self,
        visitor_type: VisitorType,
        calendar_result: dict[str, Any],
        visitor_info: VisitorInfo
    ) -> str:
        """Generate appropriate guidance message based on visitor type and calendar results"""

        if visitor_type == "appointment":
            if calendar_result and calendar_result.get("found"):
                return f"""お疲れ様です。{calendar_result.get('message', '')}

本日はお忙しい中、お越しいただきありがとうございます。"""
            else:
                return calendar_result.get("message", "予約の確認ができませんでした。") + """

恐れ入りますが、事前予約制となっております。
お手数ですが、担当者にご連絡の上、改めて予約をお取りください。"""

        elif visitor_type == "sales":
            return f"""{visitor_info['name']}様、お疲れ様です。

申し訳ございませんが、弊社では新規のお取引については
現在お断りさせていただいております。

もしお名刺や資料をお預けいただける場合は、
こちらにお預けください。
必要に応じて後日、担当者よりご連絡差し上げます。"""

        elif visitor_type == "delivery":
            return f"""{visitor_info['name']}様、お疲れ様です。

配達の件でお越しいただき、ありがとうございます。

・置き配の場合: 玄関前にお荷物をお置きください
・サインが必要な場合: 奥の呼び鈴を押してお待ちください

配達完了後は、そのままお帰りいただけます。
ありがとうございました。"""

        else:
            return """承知いたしました。少々お待ちください。
担当者にご連絡いたします。"""
