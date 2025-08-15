import asyncio
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from ..config import settings
from ..models.visitor import ConversationLog, VisitorInfo


class SlackService:
    """Slack notification service using Web API only"""

    def __init__(self):
        self.bot_token = settings.slack_bot_token
        self.channel = settings.slack_channel
        self.timeout = 10.0

    def _get_jst_timestamp(self) -> str:
        """Get current timestamp in JST (Japan Standard Time)"""
        jst = ZoneInfo("Asia/Tokyo")
        return datetime.now(jst).strftime('%Y-%m-%d %H:%M:%S')

    async def send_visitor_notification(
        self,
        visitor_info: VisitorInfo,
        conversation_logs: list[ConversationLog],
        calendar_result: dict[str, Any] | None = None,
        thread_ts: str | None = None
    ) -> bool:
        """Send visitor notification to Slack with rich formatting"""
        try:
            # Create rich message block
            blocks = self._create_visitor_message_blocks(
                visitor_info,
                conversation_logs,
                calendar_result
            )

            # Send to Slack
            message_payload = {
                "channel": self.channel,
                "blocks": blocks,
                "text": f"来客対応: {visitor_info.get('name', 'N/A')}様 ({visitor_info.get('company', 'N/A')})"
            }

            if thread_ts:
                message_payload["thread_ts"] = thread_ts

            response = await self._send_web_api_message(message_payload)
            return bool(response and response.get("ok", False))

        except Exception as e:
            print(f"Slack notification error: {e}")
            return False

    async def send_error_notification(
        self,
        error_message: str,
        session_id: str,
        visitor_info: VisitorInfo | None = None
    ) -> bool:
        """Send error notification to Slack"""
        try:
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🚨 受付システムエラー",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*セッションID:*\n{session_id}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*発生時刻:*\n{self._get_jst_timestamp()}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*エラー内容:*\n```{error_message}```"
                    }
                }
            ]

            if visitor_info:
                blocks.append({
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*来客者:*\n{visitor_info.get('name', 'N/A')}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*会社名:*\n{visitor_info.get('company', 'N/A')}"
                        }
                    ]
                })

            message_payload = {
                "channel": self.channel,
                "blocks": blocks,
                "text": f"受付システムエラー: {error_message}"
            }

            response = await self._send_web_api_message(message_payload)
            return bool(response and response.get("ok", False))

        except Exception as e:
            print(f"Slack error notification failed: {e}")
            return False

    async def send_initial_thread_message(
        self,
        title: str,
        details: str
    ) -> str | None:
        """Send initial thread message and return thread_ts"""
        try:
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": title,
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": details
                    }
                }
            ]

            message_payload = {
                "channel": self.channel,
                "blocks": blocks,
                "text": title
            }

            # Send using Web API
            response = await self._send_web_api_message(message_payload)
            if response and response.get("ok"):
                # Web API returns proper ts that can be used as thread_ts
                return response.get("ts")

            # Failure
            return None

        except Exception as e:
            print(f"Slack initial thread message error: {e}")
            return None

    async def send_thread_message(
        self,
        message: str,
        thread_ts: str
    ) -> bool:
        """Send message to existing thread"""
        try:
            # Only send threaded messages if we have a valid thread_ts
            if not thread_ts:
                print("Warning: No thread_ts provided - sending as standalone message")
                return await self.send_simple_message(message)

            message_payload = {
                "channel": self.channel,
                "text": message,
                "thread_ts": thread_ts
            }

            # Use Web API for threading
            response = await self._send_web_api_message(message_payload)
            return bool(response and response.get("ok", False))

        except Exception as e:
            print(f"Slack thread message error: {e}")
            # Fall back to standalone message
            return await self.send_simple_message(message)

    async def send_simple_message(
        self,
        message: str,
        thread_ts: str | None = None
    ) -> bool:
        """Send simple text message, optionally to thread"""
        try:
            message_payload = {
                "channel": self.channel,
                "text": message
            }

            if thread_ts:
                message_payload["thread_ts"] = thread_ts

            response = await self._send_web_api_message(message_payload)
            return bool(response and response.get("ok", False))

        except Exception as e:
            print(f"Slack simple message error: {e}")
            return False

    async def send_video_call_notification(
        self,
        visitor_info: VisitorInfo,
        room_url: str,
        room_name: str
    ) -> bool:
        """Send video call notification to Slack"""
        try:
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "📹 ビデオ通話受付",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*来客者名:*\n{visitor_info.get('name', 'N/A')}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*会社名:*\n{visitor_info.get('company', 'N/A')}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*ルーム名:*\n{room_name}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*開始時刻:*\n{self._get_jst_timestamp()}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*🔗 ビデオ通話に参加:*\n<{room_url}|ここをクリックして参加>"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "⚠️ 最大2名まで参加可能です。来訪者と1対1で対応してください。"
                        }
                    ]
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "ビデオ通話に参加",
                                "emoji": True
                            },
                            "style": "primary",
                            "url": room_url
                        }
                    ]
                }
            ]

            message_payload = {
                "channel": self.channel,
                "blocks": blocks,
                "text": f"ビデオ通話受付: {visitor_info.get('name', 'N/A')}様からのビデオ通話要請"
            }

            response = await self._send_web_api_message(message_payload)
            return bool(response and response.get("ok", False))

        except Exception as e:
            print(f"Video call Slack notification error: {e}")
            return False

    def _create_visitor_message_blocks(
        self,
        visitor_info: VisitorInfo,
        conversation_logs: list[ConversationLog],
        calendar_result: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Create rich message blocks for visitor notification"""

        # Determine visitor type icon and color
        type_info = self._get_visitor_type_info(visitor_info.get('visitor_type'))

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{type_info['icon']} 来客対応ログ",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*来客者名:*\n{visitor_info.get('name', 'N/A')}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*会社名:*\n{visitor_info.get('company', 'N/A')}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*来客タイプ:*\n{type_info['name']}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*対応時刻:*\n{self._get_jst_timestamp()}"
                    }
                ]
            }
        ]

        # Add calendar information if available
        if calendar_result:
            if calendar_result.get('found'):
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*予約状況:* ✅ 予約確認済み\n*会議室:* {calendar_result.get('roomName', 'N/A')}"
                    }
                })
            else:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*予約状況:* ❌ 予約なし"
                    }
                })

        # Add conversation summary if available
        if conversation_logs:
            # Filter out duplicate messages
            filtered_logs = []
            seen_messages = set()

            for log in conversation_logs:
                message_content = log['message'][:200].strip()
                if message_content not in seen_messages:
                    filtered_logs.append(log)
                    seen_messages.add(message_content)

            # Show filtered conversation history
            conversation_text = "\n".join([
                f"{'👤' if log['speaker'] == 'visitor' else '🤖'} {log['message'][:200]}"
                for log in filtered_logs
            ])

            # Split into multiple blocks if conversation is too long
            if len(conversation_text) > 2000:  # Slack block text limit
                # Show first part and last part if too long
                first_part = conversation_text[:900]
                last_part = conversation_text[-900:]
                conversation_text = f"{first_part}\n...\n{last_part}"

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*会話履歴 ({len(filtered_logs)}メッセージ):*\n```{conversation_text}```"
                }
            })

        # Add action buttons for follow-up
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "対応完了",
                        "emoji": True
                    },
                    "style": "primary",
                    "value": f"complete_{visitor_info.get('name', 'N/A')}"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "追加対応が必要",
                        "emoji": True
                    },
                    "style": "danger",
                    "value": f"followup_{visitor_info.get('name', 'N/A')}"
                }
            ]
        })

        return blocks

    def _get_visitor_type_info(self, visitor_type: str | None) -> dict[str, str]:
        """Get visitor type display information"""
        type_mapping = {
            "appointment": {"name": "予約来客", "icon": "📅"},
            "sales": {"name": "営業訪問", "icon": "💼"},
            "delivery": {"name": "配達業者", "icon": "📦"},
            None: {"name": "不明", "icon": "❓"}
        }

        return type_mapping.get(visitor_type, type_mapping[None])

    async def _send_web_api_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """Send message using Slack Web API with retry logic"""
        if not self.bot_token:
            print("Slack bot token not configured")
            return None

        max_retries = 3
        retry_delay = 1.0

        for attempt in range(max_retries):
            try:
                # Ensure channel is set
                if "channel" not in message:
                    message["channel"] = self.channel

                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        "https://slack.com/api/chat.postMessage",
                        json=message,
                        headers={
                            "Authorization": f"Bearer {self.bot_token}",
                            "Content-Type": "application/json"
                        }
                    )

                    if response.status_code == 200:
                        response_data = response.json()
                        if response_data.get("ok"):
                            return response_data
                        else:
                            error = response_data.get("error", "Unknown error")
                            print(f"Slack Web API error: {error}")

                            # Handle specific errors
                            if error == "invalid_auth":
                                print("❌ Invalid bot token. Please check your SLACK_BOT_TOKEN configuration.")
                                return None
                            elif error == "channel_not_found":
                                print(f"❌ Channel '{self.channel}' not found. Please check your SLACK_CHANNEL configuration.")
                                return None
                            elif error == "not_in_channel":
                                print(f"❌ Bot is not in channel '{self.channel}'. Please invite the bot to the channel.")
                                return None
                            elif error == "invalid_thread_ts":
                                print("❌ Invalid thread timestamp. The thread may have been deleted.")
                                return None
                    else:
                        print(f"Slack Web API failed with status {response.status_code}: {response.text}")

            except Exception as e:
                print(f"Slack Web API attempt {attempt + 1} failed: {e}")

                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff

        return None
