import asyncio
import json
from typing import Dict, Any, Optional
from datetime import datetime
import httpx
from ..config import settings
from ..models.visitor import VisitorInfo, ConversationLog


class SlackService:
    """Slack notification service with webhook integration"""
    
    def __init__(self):
        self.webhook_url = settings.slack_webhook_url
        self.timeout = 10.0
    
    async def send_visitor_notification(
        self, 
        visitor_info: VisitorInfo, 
        conversation_logs: list[ConversationLog],
        calendar_result: Optional[Dict[str, Any]] = None
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
            return await self._send_webhook_message({
                "blocks": blocks,
                "text": f"来客対応: {visitor_info.get('name', 'N/A')}様 ({visitor_info.get('company', 'N/A')})"
            })
            
        except Exception as e:
            print(f"Slack notification error: {e}")
            return False
    
    async def send_error_notification(
        self, 
        error_message: str, 
        session_id: str,
        visitor_info: Optional[VisitorInfo] = None
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
                            "text": f"*発生時刻:*\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
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
            
            return await self._send_webhook_message({
                "blocks": blocks,
                "text": f"受付システムエラー: {error_message}"
            })
            
        except Exception as e:
            print(f"Slack error notification failed: {e}")
            return False
    
    def _create_visitor_message_blocks(
        self, 
        visitor_info: VisitorInfo, 
        conversation_logs: list[ConversationLog],
        calendar_result: Optional[Dict[str, Any]] = None
    ) -> list[Dict[str, Any]]:
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
                        "text": f"*対応時刻:*\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
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
            conversation_text = "\n".join([
                f"{'👤' if log['speaker'] == 'visitor' else '🤖'} {log['message'][:100]}..."
                for log in conversation_logs[-3:]  # Last 3 messages
            ])
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*会話履歴:*\n```{conversation_text}```"
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
    
    def _get_visitor_type_info(self, visitor_type: Optional[str]) -> Dict[str, str]:
        """Get visitor type display information"""
        type_mapping = {
            "appointment": {"name": "予約来客", "icon": "📅"},
            "sales": {"name": "営業訪問", "icon": "💼"},
            "delivery": {"name": "配達業者", "icon": "📦"},
            None: {"name": "不明", "icon": "❓"}
        }
        
        return type_mapping.get(visitor_type, type_mapping[None])
    
    async def _send_webhook_message(self, message: Dict[str, Any]) -> bool:
        """Send message to Slack webhook with retry logic"""
        if not self.webhook_url:
            print("Slack webhook URL not configured")
            return False
        
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        self.webhook_url,
                        json=message,
                        headers={"Content-Type": "application/json"}
                    )
                    
                    if response.status_code == 200:
                        return True
                    else:
                        print(f"Slack webhook failed with status {response.status_code}: {response.text}")
                        
            except Exception as e:
                print(f"Slack webhook attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
        
        return False