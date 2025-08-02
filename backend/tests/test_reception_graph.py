import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage

from app.agents.reception_graph import ReceptionGraphManager, create_reception_graph
from app.agents.nodes import ReceptionNodes
from app.models.conversation import ConversationState
from app.models.visitor import VisitorInfo


class TestReceptionNodes:
    """Test cases for ReceptionNodes"""

    @pytest.fixture
    def reception_nodes(self):
        return ReceptionNodes()

    @pytest.mark.asyncio
    async def test_greeting_node(self, reception_nodes):
        """Test greeting node generates appropriate welcome message"""
        initial_state: ConversationState = {
            "messages": [],
            "visitor_info": None,
            "current_step": "greeting",
            "calendar_result": None,
            "error_count": 0,
            "session_id": "test-session"
        }

        result = await reception_nodes.greeting_node(initial_state)

        assert result["current_step"] == "name_collection"
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], AIMessage)
        assert "いらっしゃいませ" in result["messages"][0].content
        assert "お名前" in result["messages"][0].content
        assert result["error_count"] == 0

    @pytest.mark.asyncio
    async def test_collect_name_node_success(self, reception_nodes):
        """Test name collection with valid input"""
        state: ConversationState = {
            "messages": [HumanMessage(content="山田太郎、株式会社テストです")],
            "visitor_info": None,
            "current_step": "name_collection",
            "calendar_result": None,
            "error_count": 0,
            "session_id": "test-session"
        }

        result = await reception_nodes.collect_name_node(state)

        assert result["current_step"] == "confirmation"
        assert result["visitor_info"] is not None
        assert result["visitor_info"]["name"] == "山田太郎"
        assert result["visitor_info"]["company"] == "株式会社テスト"
        assert not result["visitor_info"]["confirmed"]
        assert "確認" in result["messages"][-1].content

    @pytest.mark.asyncio
    async def test_collect_name_node_incomplete_info(self, reception_nodes):
        """Test name collection with incomplete information"""
        state: ConversationState = {
            "messages": [HumanMessage(content="山田")],
            "visitor_info": None,
            "current_step": "name_collection",
            "calendar_result": None,
            "error_count": 0,
            "session_id": "test-session"
        }

        result = await reception_nodes.collect_name_node(state)

        assert result["current_step"] == "name_collection"
        assert result["error_count"] == 1
        assert "不足" in result["messages"][-1].content

    @pytest.mark.asyncio
    async def test_confirm_info_node_positive(self, reception_nodes):
        """Test information confirmation with positive response"""
        visitor_info: VisitorInfo = {
            "name": "山田太郎",
            "company": "株式会社テスト",
            "visitor_type": None,
            "confirmed": False,
            "correction_count": 0
        }

        state: ConversationState = {
            "messages": [HumanMessage(content="はい")],
            "visitor_info": visitor_info,
            "current_step": "confirmation",
            "calendar_result": None,
            "error_count": 0,
            "session_id": "test-session"
        }

        result = await reception_nodes.confirm_info_node(state)

        assert result["current_step"] == "type_detection"
        assert result["visitor_info"]["confirmed"] is True
        assert result["error_count"] == 0

    @pytest.mark.asyncio
    async def test_confirm_info_node_negative(self, reception_nodes):
        """Test information confirmation with negative response"""
        visitor_info: VisitorInfo = {
            "name": "山田太郎",
            "company": "株式会社テスト",
            "visitor_type": None,
            "confirmed": False,
            "correction_count": 0
        }

        state: ConversationState = {
            "messages": [HumanMessage(content="いいえ")],
            "visitor_info": visitor_info,
            "current_step": "confirmation",
            "calendar_result": None,
            "error_count": 0,
            "session_id": "test-session"
        }

        result = await reception_nodes.confirm_info_node(state)

        assert result["current_step"] == "name_collection"
        assert result["visitor_info"]["correction_count"] == 1

    @pytest.mark.asyncio
    async def test_detect_type_node_appointment(self, reception_nodes):
        """Test visitor type detection for appointment"""
        visitor_info: VisitorInfo = {
            "name": "山田太郎",
            "company": "株式会社テスト",
            "visitor_type": None,
            "confirmed": True,
            "correction_count": 0
        }

        state: ConversationState = {
            "messages": [],
            "visitor_info": visitor_info,
            "current_step": "type_detection",
            "calendar_result": None,
            "error_count": 0,
            "session_id": "test-session"
        }

        result = await reception_nodes.detect_type_node(state)

        assert result["current_step"] == "appointment_check"
        assert result["visitor_info"]["visitor_type"] == "appointment"

    @pytest.mark.asyncio
    async def test_detect_type_node_delivery(self, reception_nodes):
        """Test visitor type detection for delivery"""
        visitor_info: VisitorInfo = {
            "name": "配達員",
            "company": "ヤマト運輸",
            "visitor_type": None,
            "confirmed": True,
            "correction_count": 0
        }

        state: ConversationState = {
            "messages": [],
            "visitor_info": visitor_info,
            "current_step": "type_detection",
            "calendar_result": None,
            "error_count": 0,
            "session_id": "test-session"
        }

        result = await reception_nodes.detect_type_node(state)

        assert result["current_step"] == "guidance"
        assert result["visitor_info"]["visitor_type"] == "delivery"

    @pytest.mark.asyncio
    async def test_check_appointment_node_found(self, reception_nodes):
        """Test appointment checking with reservation found"""
        # Mock the calendar service
        mock_calendar = AsyncMock()
        visitor_info: VisitorInfo = {
            "name": "山田太郎",
            "company": "株式会社テスト",
            "visitor_type": "appointment",
            "confirmed": True,
            "correction_count": 0
        }

        mock_calendar_result = {
            "found": True,
            "events": [{"id": "1", "summary": "山田太郎様との会議"}],
            "identifier": "山田太郎",
            "message": "予約を確認いたしました",
            "error": None,
            "roomName": "会議室A"
        }

        mock_calendar.check_todays_reservations = AsyncMock(return_value=mock_calendar_result)
        reception_nodes.calendar_service = mock_calendar

        state: ConversationState = {
            "messages": [],
            "visitor_info": visitor_info,
            "current_step": "appointment_check",
            "calendar_result": None,
            "error_count": 0,
            "session_id": "test-session"
        }

        result = await reception_nodes.check_appointment_node(state)

        assert result["current_step"] == "guidance"
        assert result["calendar_result"]["found"] is True
        assert "会議室A" in result["calendar_result"]["roomName"]

    @pytest.mark.asyncio
    async def test_guide_visitor_node_appointment_found(self, reception_nodes):
        """Test guidance for appointment visitor with reservation"""
        visitor_info: VisitorInfo = {
            "name": "山田太郎",
            "company": "株式会社テスト",
            "visitor_type": "appointment",
            "confirmed": True,
            "correction_count": 0
        }

        calendar_result = {
            "found": True,
            "message": "予約を確認いたしました",
            "roomName": "会議室A"
        }

        state: ConversationState = {
            "messages": [],
            "visitor_info": visitor_info,
            "current_step": "guidance",
            "calendar_result": calendar_result,
            "error_count": 0,
            "session_id": "test-session"
        }

        result = await reception_nodes.guide_visitor_node(state)

        assert result["current_step"] == "complete"
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], AIMessage)
        guidance_content = result["messages"][0].content
        assert "会議室" in guidance_content or "呼び鈴" in guidance_content

    @pytest.mark.asyncio
    async def test_guide_visitor_node_sales(self, reception_nodes):
        """Test guidance for sales visitor"""
        visitor_info: VisitorInfo = {
            "name": "営業太郎",
            "company": "営業会社",
            "visitor_type": "sales",
            "confirmed": True,
            "correction_count": 0
        }

        state: ConversationState = {
            "messages": [],
            "visitor_info": visitor_info,
            "current_step": "guidance",
            "calendar_result": None,
            "error_count": 0,
            "session_id": "test-session"
        }

        result = await reception_nodes.guide_visitor_node(state)

        assert result["current_step"] == "complete"
        guidance_content = result["messages"][0].content
        assert "お断り" in guidance_content or "新規" in guidance_content

    @pytest.mark.asyncio
    async def test_send_slack_node(self, reception_nodes):
        """Test Slack notification sending"""
        # Mock the slack service
        mock_slack = AsyncMock()
        visitor_info: VisitorInfo = {
            "name": "山田太郎",
            "company": "株式会社テスト",
            "visitor_type": "appointment",
            "confirmed": True,
            "correction_count": 0
        }

        mock_slack.send_visitor_notification = AsyncMock(return_value=True)

        state: ConversationState = {
            "messages": [
                AIMessage(content="いらっしゃいませ"),
                HumanMessage(content="山田太郎です"),
                AIMessage(content="ありがとうございます")
            ],
            "visitor_info": visitor_info,
            "current_step": "complete",
            "calendar_result": {"found": True},
            "error_count": 0,
            "session_id": "test-session"
        }

        mock_slack.send_visitor_notification = AsyncMock()
        reception_nodes.slack_service = mock_slack
        
        result = await reception_nodes.send_slack_node(state)

        assert result["current_step"] == "complete"
        mock_slack.send_visitor_notification.assert_called_once()


class TestReceptionGraphManager:
    """Test cases for ReceptionGraphManager"""

    @pytest.fixture
    def graph_manager(self):
        return ReceptionGraphManager()

    @pytest.mark.asyncio
    async def test_start_conversation(self, graph_manager):
        """Test starting a new conversation"""
        with patch.object(graph_manager.graph, 'ainvoke') as mock_invoke:
            mock_invoke.return_value = {
                "messages": [AIMessage(content="いらっしゃいませ")],
                "current_step": "name_collection",
                "visitor_info": None
            }

            result = await graph_manager.start_conversation("test-session")

            assert result["success"] is True
            assert result["session_id"] == "test-session"
            assert "いらっしゃいませ" in result["message"]
            assert result["step"] == "name_collection"

    @pytest.mark.asyncio
    async def test_send_message_success(self, graph_manager):
        """Test sending a message successfully"""
        with patch.object(graph_manager.graph, 'aget_state') as mock_get_state, \
             patch.object(graph_manager.graph, 'ainvoke') as mock_invoke:
            
            # Mock current state
            mock_state = MagicMock()
            mock_state.values = {
                "messages": [AIMessage(content="いらっしゃいませ")],
                "current_step": "name_collection",
                "visitor_info": None
            }
            mock_get_state.return_value = mock_state

            # Mock invoke result
            mock_invoke.return_value = {
                "messages": [AIMessage(content="ありがとうございます")],
                "current_step": "confirmation",
                "visitor_info": {
                    "name": "山田太郎",
                    "company": "株式会社テスト"
                }
            }

            result = await graph_manager.send_message("test-session", "山田太郎、株式会社テストです")

            assert result["success"] is True
            assert result["session_id"] == "test-session"
            assert result["step"] == "confirmation"
            assert result["visitor_info"] is not None

    @pytest.mark.asyncio
    async def test_send_message_session_not_found(self, graph_manager):
        """Test sending message to non-existent session"""
        with patch.object(graph_manager.graph, 'aget_state') as mock_get_state:
            mock_get_state.return_value = None

            result = await graph_manager.send_message("invalid-session", "test message")

            assert result["success"] is False
            assert "Session not found" in result["error"]

    @pytest.mark.asyncio
    async def test_get_conversation_history(self, graph_manager):
        """Test getting conversation history"""
        with patch.object(graph_manager.graph, 'aget_state') as mock_get_state:
            mock_state = MagicMock()
            mock_state.values = {
                "messages": [
                    AIMessage(content="いらっしゃいませ"),
                    HumanMessage(content="山田太郎です")
                ],
                "current_step": "confirmation",
                "visitor_info": {
                    "name": "山田太郎",
                    "company": "株式会社テスト"
                }
            }
            mock_get_state.return_value = mock_state

            result = await graph_manager.get_conversation_history("test-session")

            assert result["success"] is True
            assert len(result["messages"]) == 2
            assert result["messages"][0]["speaker"] == "ai"
            assert result["messages"][1]["speaker"] == "visitor"


class TestVisitorInfoExtraction:
    """Test cases for visitor information extraction"""

    def test_extract_visitor_info_standard_format(self):
        """Test extraction with standard Japanese format"""
        nodes = ReceptionNodes()
        
        result = nodes._extract_visitor_info("山田太郎、株式会社テストです")
        assert result["name"] == "山田太郎"
        assert result["company"] == "株式会社テスト"

    def test_extract_visitor_info_english_format(self):
        """Test extraction with English company format"""
        nodes = ReceptionNodes()
        
        result = nodes._extract_visitor_info("John Smith, Test Corp")
        assert result["name"] == "John Smith"
        assert result["company"] == "Test Corp"

    def test_extract_visitor_info_partial(self):
        """Test extraction with partial information"""
        nodes = ReceptionNodes()
        
        result = nodes._extract_visitor_info("山田太郎")
        assert result["name"] == "山田太郎"
        assert result["company"] == ""

    def test_detect_visitor_type_delivery(self):
        """Test visitor type detection for delivery companies"""
        nodes = ReceptionNodes()
        
        visitor_info = {"name": "配達員", "company": "ヤマト運輸"}
        result = nodes._detect_visitor_type(visitor_info)
        assert result == "delivery"

    def test_detect_visitor_type_sales(self):
        """Test visitor type detection for sales companies"""
        nodes = ReceptionNodes()
        
        visitor_info = {"name": "営業", "company": "営業商事"}
        result = nodes._detect_visitor_type(visitor_info)
        assert result == "sales"

    def test_detect_visitor_type_appointment(self):
        """Test visitor type detection for regular appointments"""
        nodes = ReceptionNodes()
        
        visitor_info = {"name": "山田太郎", "company": "普通の会社"}
        result = nodes._detect_visitor_type(visitor_info)
        assert result == "appointment"