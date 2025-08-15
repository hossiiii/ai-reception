"""Asynchronous Slack notification manager with thread support"""

import asyncio
import contextlib
import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from ..models.visitor import ConversationLog, VisitorInfo
from .slack_service import SlackService


class AsyncNotificationManager:
    """Manages asynchronous Slack notifications with thread support per session"""

    def __init__(self):
        self.slack_service = SlackService()
        self._session_threads: dict[str, str] = {}  # session_id -> thread_ts
        self._session_started: set[str] = set()  # Track which sessions have had start notification sent
        self._notification_queue = asyncio.Queue()
        self._queue_processor_task = None
        self._running_tasks = set()
        self.logger = logging.getLogger(__name__)

    async def start_processor(self):
        """Start the background notification processor"""
        if self._queue_processor_task is None or self._queue_processor_task.done():
            self._queue_processor_task = asyncio.create_task(self._process_notification_queue())
            self.logger.info("🚀 AsyncNotificationManager processor started")

    async def stop_processor(self):
        """Stop the background notification processor"""
        if self._queue_processor_task and not self._queue_processor_task.done():
            self._queue_processor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._queue_processor_task
            self.logger.info("🛑 AsyncNotificationManager processor stopped")

    async def send_session_start_notification(
        self,
        session_id: str,
        initial_message: str = "新しい来客セッションが開始されました"
    ) -> bool:
        """Send initial notification and create thread for session"""
        try:
            # Check if session start notification already sent
            if session_id in self._session_started:
                self.logger.info(f"🔄 Session start notification already sent for {session_id}, skipping duplicate")
                return True  # Return True since notification was already sent successfully

            jst = ZoneInfo("Asia/Tokyo")
            timestamp = datetime.now(jst).strftime('%Y-%m-%d %H:%M:%S')

            # Create initial thread message
            thread_ts = await self.slack_service.send_initial_thread_message(
                f"🔔 {initial_message}",
                f"セッションID: {session_id}\n開始時刻: {timestamp}"
            )

            if thread_ts:
                # Thread created successfully with Web API
                self._session_threads[session_id] = thread_ts
                self._session_started.add(session_id)  # Mark session as started
                self.logger.info(f"📍 Created thread for session {session_id}: {thread_ts}")
                return True
            else:
                # Failure to create thread
                self.logger.error(f"❌ Failed to create initial notification for session {session_id}")
                return False

        except Exception as e:
            self.logger.error(f"❌ Error creating thread for session {session_id}: {e}")
            return False

    async def send_progress_notification(
        self,
        session_id: str,
        stage: str,
        visitor_info: VisitorInfo | None = None,
        additional_info: str | None = None
    ) -> bool:
        """Send progress notification to session thread"""
        try:
            notification = {
                "type": "progress",
                "session_id": session_id,
                "stage": stage,
                "visitor_info": visitor_info,
                "additional_info": additional_info,
                "timestamp": datetime.now()
            }

            await self._notification_queue.put(notification)
            self.logger.debug(f"📬 Queued progress notification for session {session_id}: {stage}")
            return True

        except Exception as e:
            self.logger.error(f"❌ Error queuing progress notification for session {session_id}: {e}")
            return False

    async def send_visitor_info_notification(
        self,
        session_id: str,
        visitor_info: VisitorInfo,
        conversation_logs: list[ConversationLog] | None = None
    ) -> bool:
        """Send visitor information notification to session thread"""
        try:
            notification = {
                "type": "visitor_info",
                "session_id": session_id,
                "visitor_info": visitor_info,
                "conversation_logs": conversation_logs or [],
                "timestamp": datetime.now()
            }

            await self._notification_queue.put(notification)
            self.logger.debug(f"📬 Queued visitor info notification for session {session_id}")
            return True

        except Exception as e:
            self.logger.error(f"❌ Error queuing visitor info notification for session {session_id}: {e}")
            return False

    async def send_completion_notification(
        self,
        session_id: str,
        visitor_info: VisitorInfo,
        conversation_logs: list[ConversationLog],
        calendar_result: dict[str, Any] | None = None
    ) -> bool:
        """Send completion notification to session thread"""
        try:
            notification = {
                "type": "completion",
                "session_id": session_id,
                "visitor_info": visitor_info,
                "conversation_logs": conversation_logs,
                "calendar_result": calendar_result,
                "timestamp": datetime.now()
            }

            await self._notification_queue.put(notification)
            self.logger.debug(f"📬 Queued completion notification for session {session_id}")
            return True

        except Exception as e:
            self.logger.error(f"❌ Error queuing completion notification for session {session_id}: {e}")
            return False

    async def send_error_notification(
        self,
        session_id: str,
        error_message: str,
        visitor_info: VisitorInfo | None = None
    ) -> bool:
        """Send error notification to session thread"""
        try:
            notification = {
                "type": "error",
                "session_id": session_id,
                "error_message": error_message,
                "visitor_info": visitor_info,
                "timestamp": datetime.now()
            }

            await self._notification_queue.put(notification)
            self.logger.debug(f"📬 Queued error notification for session {session_id}")
            return True

        except Exception as e:
            self.logger.error(f"❌ Error queuing error notification for session {session_id}: {e}")
            return False

    async def _process_notification_queue(self):
        """Background processor for notification queue"""
        self.logger.info("🔄 Starting notification queue processor")

        while True:
            try:
                # Wait for notification with timeout to allow for graceful shutdown
                notification = await asyncio.wait_for(
                    self._notification_queue.get(),
                    timeout=1.0
                )

                # Process the notification
                await self._handle_notification(notification)

            except TimeoutError:
                # Timeout is expected for graceful shutdown checks
                continue
            except asyncio.CancelledError:
                self.logger.info("📤 Notification processor cancelled")
                break
            except Exception as e:
                self.logger.error(f"❌ Error in notification processor: {e}")
                # Continue processing other notifications

    async def _handle_notification(self, notification: dict[str, Any]):
        """Handle individual notification"""
        try:
            session_id = notification["session_id"]
            notification_type = notification["type"]

            # Get thread for session
            thread_ts = self._session_threads.get(session_id)
            if not thread_ts:
                self.logger.warning(f"⚠️ No thread found for session {session_id}, skipping notification")
                return

            # Thread should always be available with Web API

            # Process based on type
            if notification_type == "progress":
                await self._send_progress_message(thread_ts, notification)
            elif notification_type == "visitor_info":
                await self._send_visitor_info_message(thread_ts, notification)
            elif notification_type == "completion":
                await self._send_completion_message(thread_ts, notification)
            elif notification_type == "error":
                await self._send_error_message(thread_ts, notification)
            else:
                self.logger.warning(f"⚠️ Unknown notification type: {notification_type}")

        except Exception as e:
            self.logger.error(f"❌ Error handling notification: {e}")

    async def _send_progress_message(self, thread_ts: str, notification: dict[str, Any]):
        """Send progress update message to thread"""
        stage = notification["stage"]
        visitor_info = notification.get("visitor_info")
        additional_info = notification.get("additional_info", "")

        # Create progress message based on stage
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

        # Add timestamp
        jst = ZoneInfo("Asia/Tokyo")
        timestamp = notification["timestamp"].astimezone(jst).strftime('%H:%M:%S')
        message += f"\n時刻: {timestamp}"

        # Send message to thread
        await self.slack_service.send_thread_message(message, thread_ts)

    async def _send_visitor_info_message(self, thread_ts: str, notification: dict[str, Any]):
        """Send visitor information update to thread"""
        visitor_info = notification["visitor_info"]
        conversation_logs = notification.get("conversation_logs", [])

        message = "👤 来客者情報が確定しました\n\n"
        message += f"• 名前: {visitor_info.get('name', 'N/A')}\n"
        message += f"• 会社: {visitor_info.get('company', 'N/A')}\n"
        message += f"• 訪問目的: {visitor_info.get('purpose', 'N/A')}\n"
        message += f"• 訪問タイプ: {visitor_info.get('visitor_type', 'N/A')}\n"

        if conversation_logs:
            message += f"\n会話ログ: {len(conversation_logs)}件のやり取り"

        # Add timestamp
        jst = ZoneInfo("Asia/Tokyo")
        timestamp = notification["timestamp"].astimezone(jst).strftime('%H:%M:%S')
        message += f"\n更新時刻: {timestamp}"

        # Send message to thread
        await self.slack_service.send_thread_message(message, thread_ts)

    async def _send_completion_message(self, thread_ts: str, notification: dict[str, Any]):
        """Send completion notification to thread"""
        visitor_info = notification["visitor_info"]
        conversation_logs = notification["conversation_logs"]
        calendar_result = notification.get("calendar_result")

        # Use the existing comprehensive notification method
        success = await self.slack_service.send_visitor_notification(
            visitor_info,
            conversation_logs,
            calendar_result,
            thread_ts=thread_ts
        )

        if success:
            # Send final completion message
            completion_message = "✅ 来客対応が完了しました\n"
            jst = ZoneInfo("Asia/Tokyo")
            timestamp = notification["timestamp"].astimezone(jst).strftime('%H:%M:%S')
            completion_message += f"完了時刻: {timestamp}"

            # Send completion message to thread
            await self.slack_service.send_thread_message(completion_message, thread_ts)

    async def _send_error_message(self, thread_ts: str, notification: dict[str, Any]):
        """Send error notification to thread"""
        error_message = notification["error_message"]
        visitor_info = notification.get("visitor_info")

        message = f"🚨 エラーが発生しました\n\n{error_message}\n"

        if visitor_info:
            message += f"関連する来客者: {visitor_info.get('name', 'N/A')}様"

        # Add timestamp
        jst = ZoneInfo("Asia/Tokyo")
        timestamp = notification["timestamp"].astimezone(jst).strftime('%H:%M:%S')
        message += f"\n発生時刻: {timestamp}"

        # Send message to thread
        await self.slack_service.send_thread_message(message, thread_ts)

    def get_session_thread(self, session_id: str) -> str | None:
        """Get thread_ts for a session"""
        return self._session_threads.get(session_id)

    def is_session_started(self, session_id: str) -> bool:
        """Check if session start notification has been sent"""
        return session_id in self._session_started

    def clear_session_thread(self, session_id: str):
        """Clear thread reference for completed session"""
        if session_id in self._session_threads:
            del self._session_threads[session_id]
        if session_id in self._session_started:
            self._session_started.remove(session_id)
        self.logger.info(f"🧹 Cleared thread reference and start tracking for session {session_id}")

    async def cleanup(self):
        """Cleanup all running tasks and threads"""
        await self.stop_processor()

        if self._running_tasks:
            self.logger.info(f"🧹 Cleaning up {len(self._running_tasks)} background tasks")
            await asyncio.gather(*self._running_tasks, return_exceptions=True)
            self._running_tasks.clear()

        # Clear session threads and start tracking
        self._session_threads.clear()
        self._session_started.clear()
        self.logger.info("🧹 AsyncNotificationManager cleanup completed")


# Global instance
async_notification_manager = AsyncNotificationManager()
