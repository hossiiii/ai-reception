"""Background task manager for AI reception system"""

import asyncio
import logging
from datetime import datetime
from typing import Any

from ..models.visitor import ConversationLog
from .slack_service import SlackService


class BackgroundTaskManager:
    """Manages background tasks to improve response times"""

    def __init__(self):
        self.slack_service = SlackService()
        self._running_tasks = set()
        self.logger = logging.getLogger(__name__)

    async def send_slack_notification_async(
        self,
        visitor_info: dict[str, Any],
        conversation_logs: list[ConversationLog],
        calendar_result: dict[str, Any] = None,
        thread_ts: str = None
    ) -> None:
        """Send Slack notification as a background task"""
        task = asyncio.create_task(
            self._send_slack_notification_impl(visitor_info, conversation_logs, calendar_result, thread_ts)
        )

        # Track task to prevent garbage collection
        self._running_tasks.add(task)
        task.add_done_callback(self._running_tasks.discard)

    async def _send_slack_notification_impl(
        self,
        visitor_info: dict[str, Any],
        conversation_logs: list[ConversationLog],
        calendar_result: dict[str, Any] = None,
        thread_ts: str = None
    ) -> None:
        """Implementation of Slack notification sending with enhanced error handling"""
        max_retries = 3
        retry_delay = 1.0

        for attempt in range(max_retries):
            try:
                self.logger.info(f"📤 Sending Slack notification (attempt {attempt + 1}) for: {visitor_info.get('company', 'Unknown')}")

                success = await self.slack_service.send_visitor_notification(
                    visitor_info,
                    conversation_logs,
                    calendar_result,
                    thread_ts
                )

                if success:
                    self.logger.info(f"✅ Slack notification sent successfully for: {visitor_info.get('company', 'Unknown')}")
                    return
                else:
                    self.logger.warning(f"⚠️ Slack notification failed (attempt {attempt + 1}) for: {visitor_info.get('company', 'Unknown')}")

            except Exception as e:
                self.logger.error(f"❌ Background Slack notification error (attempt {attempt + 1}): {e}")

            # Retry logic
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff

        # Final failure notification
        self.logger.error(f"❌ All Slack notification attempts failed for: {visitor_info.get('company', 'Unknown')}")

        # Send error notification if possible
        try:
            await self.slack_service.send_error_notification(
                f"来客通知の送信に失敗しました: {visitor_info.get('company', 'Unknown')}",
                "background_task",
                visitor_info
            )
        except Exception as error_notify_exception:
            self.logger.error(f"❌ Error notification also failed: {error_notify_exception}")

    async def send_progress_notification_async(
        self,
        session_id: str,
        stage: str,
        visitor_info: dict[str, Any] = None,
        additional_info: str = None,
        thread_ts: str = None
    ) -> None:
        """Send progress notification as a background task"""
        task = asyncio.create_task(
            self._send_progress_notification_impl(session_id, stage, visitor_info, additional_info, thread_ts)
        )

        # Track task to prevent garbage collection
        self._running_tasks.add(task)
        task.add_done_callback(self._running_tasks.discard)

    async def _send_progress_notification_impl(
        self,
        session_id: str,
        stage: str,
        visitor_info: dict[str, Any] = None,
        additional_info: str = None,
        thread_ts: str = None
    ) -> None:
        """Implementation of progress notification sending"""
        try:
            # Create progress message
            stage_messages = {
                "greeting": "👋 来客者への挨拶を開始",
                "collecting_info": "📝 来客者情報を収集中",
                "confirming_info": "✅ 情報の確認を実施中",
                "checking_calendar": "📅 カレンダーを確認中",
                "providing_guidance": "🗣️ 来客者への案内を実施中",
                "waiting": "⏳ 来客者の応答を待機中",
                "completing": "🏁 対応を完了"
            }

            message = stage_messages.get(stage, f"🔄 {stage}")

            if visitor_info:
                name = visitor_info.get("name", "")
                company = visitor_info.get("company", "")
                if name or company:
                    message += f"\n来客者: {name}様 ({company})"

            if additional_info:
                message += f"\n詳細: {additional_info}"

            # Add session and timestamp info
            message += f"\nセッション: {session_id}"
            message += f"\n時刻: {datetime.now().strftime('%H:%M:%S')}"

            # Send simple message to thread or channel
            await self.slack_service.send_simple_message(message, thread_ts)

            self.logger.debug(f"📤 Progress notification sent: {stage} for session {session_id}")

        except Exception as e:
            self.logger.error(f"❌ Progress notification failed for session {session_id}: {e}")

    def schedule_task(self, coro):
        """Schedule a generic background task"""
        task = asyncio.create_task(coro)
        self._running_tasks.add(task)
        task.add_done_callback(self._running_tasks.discard)
        return task

    async def cleanup(self):
        """Clean up all running background tasks"""
        if self._running_tasks:
            self.logger.info(f"🧹 Cleaning up {len(self._running_tasks)} background tasks")
            await asyncio.gather(*self._running_tasks, return_exceptions=True)
            self._running_tasks.clear()
            self.logger.info("🧹 Background task cleanup completed")


# Global instance
background_task_manager = BackgroundTaskManager()
