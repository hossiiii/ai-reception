"""Integration tests for the new specialized guidance nodes architecture"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.nodes import ReceptionNodes
from app.models.conversation import ConversationState
from app.models.visitor import VisitorInfo


@pytest.fixture
def reception_nodes():
    """Create ReceptionNodes instance for testing"""
    return ReceptionNodes()


class TestSpecializedNodesIntegration:
    """Test the new specialized guidance nodes architecture end-to-end"""

    @pytest.mark.asyncio
    async def test_delivery_flow_complete_integration(self, reception_nodes):
        """Test complete delivery flow using specialized nodes"""
        # Mock Slack service
        mock_slack = AsyncMock()
        mock_slack.send_visitor_notification = AsyncMock(return_value=None)
        reception_nodes.slack_service = mock_slack
        
        # Simulate delivery visitor input
        state: ConversationState = {
            "messages": [HumanMessage(content="ヤマト運輸です、お荷物をお届けに参りました")],
            "visitor_info": {},
            "current_step": "collect_all_info",
            "calendar_result": None,
            "error_count": 0,
            "session_id": "test-delivery-integration"
        }
        
        # Execute collection (should trigger delivery shortcut)
        result = await reception_nodes.collect_all_info_node(state)
        
        # Verify delivery was correctly identified and handled
        assert result["visitor_info"]["visitor_type"] == "delivery"
        assert result["visitor_info"]["confirmed"] == True
        assert result["current_step"] == "complete"
        
        # Verify delivery-specific message was generated
        assert len(result["messages"]) > 0
        last_message = result["messages"][-1]
        assert isinstance(last_message, AIMessage)
        message_content = last_message.content.lower()
        
        # Verify delivery-appropriate content
        assert any(word in message_content for word in ["配達", "荷物", "お疲れ様"])
        # Verify no calendar-related mentions
        assert "カレンダー" not in message_content
        assert "予約" not in message_content
        
        # Verify Slack notification was sent
        mock_slack.send_visitor_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_sales_flow_complete_integration(self, reception_nodes):
        """Test complete sales flow using specialized nodes"""
        # Mock Slack service
        mock_slack = AsyncMock()
        mock_slack.send_visitor_notification = AsyncMock(return_value=None)
        reception_nodes.slack_service = mock_slack
        
        # Simulate sales visitor going through normal flow
        visitor_info: VisitorInfo = {
            "name": "営業担当者",
            "company": "販売会社",
            "purpose": "新サービスのご提案",
            "visitor_type": None,
            "confirmed": True,
            "correction_count": 0
        }
        
        state: ConversationState = {
            "messages": [
                AIMessage(content="確認メッセージ"),
                HumanMessage(content="はい、正しいです")
            ],
            "visitor_info": visitor_info,
            "current_step": "confirmation_response",
            "calendar_result": None,
            "error_count": 0,
            "session_id": "test-sales-integration"
        }
        
        # Execute confirmation (should route to sales guidance)
        result = await reception_nodes.confirm_info_node(state)
        
        # Verify sales type was determined and handled appropriately
        assert result["visitor_info"]["visitor_type"] == "sales"
        assert result["current_step"] == "complete"
        
        # Verify sales-specific message
        assert len(result["messages"]) > 0
        last_message = result["messages"][-1]
        assert isinstance(last_message, AIMessage)
        message_content = last_message.content.lower()
        
        # Verify sales-appropriate content (polite rejection)
        assert any(word in message_content for word in ["申し訳", "お断り", "お取引"])
        # Verify no calendar-related mentions
        assert "カレンダー" not in message_content
        
        # Verify Slack notification was sent
        mock_slack.send_visitor_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_appointment_flow_with_calendar_check(self, reception_nodes):
        """Test complete appointment flow with calendar check"""
        # Mock services
        mock_slack = AsyncMock()
        mock_slack.send_visitor_notification = AsyncMock(return_value=None)
        reception_nodes.slack_service = mock_slack
        
        mock_calendar = AsyncMock()
        mock_calendar.check_todays_reservations = AsyncMock(return_value={
            "found": True,
            "message": "会議の予約がございます。",
            "roomName": "会議室A"
        })
        reception_nodes.calendar_service = mock_calendar
        
        # Simulate appointment visitor
        visitor_info: VisitorInfo = {
            "name": "田中太郎",
            "company": "株式会社テスト",
            "purpose": "打ち合わせ",
            "visitor_type": None,
            "confirmed": True,
            "correction_count": 0
        }
        
        state: ConversationState = {
            "messages": [
                AIMessage(content="確認メッセージ"),
                HumanMessage(content="はい、正しいです")
            ],
            "visitor_info": visitor_info,
            "current_step": "confirmation_response",
            "calendar_result": None,
            "error_count": 0,
            "session_id": "test-appointment-integration"
        }
        
        # Execute confirmation (should route through calendar to appointment guidance)
        result = await reception_nodes.confirm_info_node(state)
        
        # Verify appointment type was determined
        assert result["visitor_info"]["visitor_type"] == "appointment"
        assert result["current_step"] == "complete"
        
        # Verify calendar was checked
        mock_calendar.check_todays_reservations.assert_called_once()
        
        # Verify calendar result is present
        assert result["calendar_result"]["found"] == True
        assert result["calendar_result"]["roomName"] == "会議室A"
        
        # Verify appointment-specific message with calendar info
        assert len(result["messages"]) > 0
        last_message = result["messages"][-1]
        assert isinstance(last_message, AIMessage)
        message_content = last_message.content
        
        # Verify appointment-appropriate content
        assert "会議室A" in message_content
        assert any(word in message_content for word in ["予約", "会議", "お忙しい中"])
        
        # Verify Slack notification was sent
        mock_slack.send_visitor_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_appointment_flow_no_reservation_found(self, reception_nodes):
        """Test appointment flow when no reservation is found"""
        # Mock services
        mock_slack = AsyncMock()
        mock_slack.send_visitor_notification = AsyncMock(return_value=None)
        reception_nodes.slack_service = mock_slack
        
        mock_calendar = AsyncMock()
        mock_calendar.check_todays_reservations = AsyncMock(return_value={
            "found": False,
            "message": "予約が見つかりませんでした"
        })
        reception_nodes.calendar_service = mock_calendar
        
        # Simulate appointment visitor without reservation
        visitor_info: VisitorInfo = {
            "name": "佐藤花子",
            "company": "株式会社未予約",
            "purpose": "会議の件で",
            "visitor_type": None,
            "confirmed": True,
            "correction_count": 0
        }
        
        state: ConversationState = {
            "messages": [
                AIMessage(content="確認メッセージ"),
                HumanMessage(content="はい、正しいです")
            ],
            "visitor_info": visitor_info,
            "current_step": "confirmation_response",
            "calendar_result": None,
            "error_count": 0,
            "session_id": "test-no-reservation"
        }
        
        # Execute confirmation
        result = await reception_nodes.confirm_info_node(state)
        
        # Verify appointment type was determined
        assert result["visitor_info"]["visitor_type"] == "appointment"
        assert result["current_step"] == "complete"
        
        # Verify calendar was checked
        mock_calendar.check_todays_reservations.assert_called_once()
        
        # Verify no reservation found
        assert result["calendar_result"]["found"] == False
        
        # Verify appropriate no-reservation message
        assert len(result["messages"]) > 0
        last_message = result["messages"][-1]
        assert isinstance(last_message, AIMessage)
        message_content = last_message.content
        
        # Verify no-reservation-appropriate content
        assert any(word in message_content for word in ["申し訳", "予約", "確認できません"])
        assert "事前予約制" in message_content
        
        # Verify Slack notification was sent
        mock_slack.send_visitor_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_specialized_nodes_direct_calls(self, reception_nodes):
        """Test direct calls to specialized guidance nodes"""
        
        # Test delivery_guidance_node
        delivery_state: ConversationState = {
            "messages": [],
            "visitor_info": {"company": "佐川急便", "visitor_type": "delivery"},
            "current_step": "guidance",
            "session_id": "test-direct-delivery"
        }
        
        delivery_result = await reception_nodes.delivery_guidance_node(delivery_state)
        assert delivery_result["current_step"] == "complete"
        assert len(delivery_result["messages"]) == 1
        assert "佐川急便" in delivery_result["messages"][0].content
        assert "配達" in delivery_result["messages"][0].content
        
        # Test sales_guidance_node
        sales_state: ConversationState = {
            "messages": [],
            "visitor_info": {"company": "営業会社", "name": "営業担当", "visitor_type": "sales"},
            "current_step": "guidance",
            "session_id": "test-direct-sales"
        }
        
        sales_result = await reception_nodes.sales_guidance_node(sales_state)
        assert sales_result["current_step"] == "complete"
        assert len(sales_result["messages"]) == 1
        assert "お断り" in sales_result["messages"][0].content
        
        # Test appointment_guidance_node
        appointment_state: ConversationState = {
            "messages": [],
            "visitor_info": {"company": "テスト会社", "name": "田中", "visitor_type": "appointment"},
            "calendar_result": {"found": True, "roomName": "会議室B"},
            "current_step": "guidance",
            "session_id": "test-direct-appointment"
        }
        
        appointment_result = await reception_nodes.appointment_guidance_node(appointment_state)
        assert appointment_result["current_step"] == "complete"
        assert len(appointment_result["messages"]) == 1
        assert "会議室B" in appointment_result["messages"][0].content

    @pytest.mark.asyncio
    async def test_appointment_guidance_without_calendar_result(self, reception_nodes):
        """Test that appointment guidance requires calendar result"""
        state: ConversationState = {
            "messages": [],
            "visitor_info": {"visitor_type": "appointment"},
            "calendar_result": None,  # Missing calendar result
            "current_step": "guidance",
            "session_id": "test-missing-calendar"
        }
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="Calendar check required"):
            await reception_nodes.appointment_guidance_node(state)

    @pytest.mark.asyncio
    async def test_error_recovery_in_specialized_flows(self, reception_nodes):
        """Test error handling in specialized node flows"""
        # Mock Slack service to fail
        mock_slack = AsyncMock()
        mock_slack.send_visitor_notification = AsyncMock(side_effect=Exception("Slack error"))
        reception_nodes.slack_service = mock_slack
        
        state: ConversationState = {
            "messages": [HumanMessage(content="ヤマトです")],
            "visitor_info": {},
            "current_step": "collect_all_info",
            "calendar_result": None,
            "error_count": 0,
            "session_id": "test-error-recovery"
        }
        
        # Execute delivery shortcut - should handle Slack error gracefully
        result = await reception_nodes.collect_all_info_node(state)
        
        # Should still complete delivery processing despite Slack error
        assert result["visitor_info"]["visitor_type"] == "delivery"
        # Error handling should ensure flow doesn't break entirely
        assert result["current_step"] in ["complete", "error"]