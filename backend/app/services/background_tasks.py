"""Background task manager for AI reception system"""

import asyncio
from datetime import datetime
from typing import Dict, Any, List
from ..models.visitor import ConversationLog
from .slack_service import SlackService


class BackgroundTaskManager:
    """Manages background tasks to improve response times"""
    
    def __init__(self):
        self.slack_service = SlackService()
        self._running_tasks = set()
    
    async def send_slack_notification_async(
        self,
        visitor_info: Dict[str, Any],
        conversation_logs: List[ConversationLog],
        calendar_result: Dict[str, Any] = None
    ) -> None:
        """Send Slack notification as a background task"""
        task = asyncio.create_task(
            self._send_slack_notification_impl(visitor_info, conversation_logs, calendar_result)
        )
        
        # Track task to prevent garbage collection
        self._running_tasks.add(task)
        task.add_done_callback(self._running_tasks.discard)
    
    async def _send_slack_notification_impl(
        self,
        visitor_info: Dict[str, Any],
        conversation_logs: List[ConversationLog],
        calendar_result: Dict[str, Any] = None
    ) -> None:
        """Implementation of Slack notification sending"""
        try:
            print(f"📤 Sending Slack notification in background for: {visitor_info.get('company', 'Unknown')}")
            await self.slack_service.send_visitor_notification(
                visitor_info,
                conversation_logs,
                calendar_result
            )
            print(f"✅ Slack notification sent successfully for: {visitor_info.get('company', 'Unknown')}")
        except Exception as e:
            print(f"❌ Background Slack notification failed: {e}")
    
    def schedule_task(self, coro):
        """Schedule a generic background task"""
        task = asyncio.create_task(coro)
        self._running_tasks.add(task)
        task.add_done_callback(self._running_tasks.discard)
        return task
    
    async def cleanup(self):
        """Clean up all running background tasks"""
        if self._running_tasks:
            print(f"🧹 Cleaning up {len(self._running_tasks)} background tasks")
            await asyncio.gather(*self._running_tasks, return_exceptions=True)
            self._running_tasks.clear()


# Global instance
background_task_manager = BackgroundTaskManager()