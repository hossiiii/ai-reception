from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from ..models.conversation import ConversationState
from .nodes import ReceptionNodes


def create_reception_graph():
    """Create the main reception conversation flow graph"""
    
    # Initialize nodes
    nodes = ReceptionNodes()
    
    # Create StateGraph with ConversationState
    workflow = StateGraph(ConversationState)
    
    # Add nodes to the graph
    workflow.add_node("greeting", nodes.greeting_node)
    workflow.add_node("collect_all_info", nodes.collect_all_info_node)
    workflow.add_node("confirm_info", nodes.confirm_info_node)
    workflow.add_node("detect_type", nodes.detect_type_node)
    workflow.add_node("process_visitor_type", nodes.process_visitor_type_node)
    workflow.add_node("check_appointment", nodes.check_appointment_node)
    workflow.add_node("guide_visitor", nodes.guide_visitor_node)
    workflow.add_node("send_slack", nodes.send_slack_node)
    
    # Define the conversation flow
    workflow.set_entry_point("greeting")
    
    # From greeting, go to collect all info
    workflow.add_edge("greeting", "collect_all_info")
    
    # From collect all info, determine next step based on success
    def should_confirm_or_retry(state: ConversationState) -> str:
        """Determine if we should go to confirmation or retry collection"""
        current_step = state.get("current_step", "collect_all_info")
        error_count = state.get("error_count", 0)
        
        # Prevent infinite loops with max retries
        if error_count > 3:
            return "confirm_info"  # Force proceed to avoid infinite retry
        
        if current_step == "confirmation":
            return "confirm_info"
        else:
            return "collect_all_info"
    
    workflow.add_conditional_edges(
        "collect_all_info",
        should_confirm_or_retry,
        {
            "confirm_info": "confirm_info",
            "collect_all_info": "collect_all_info"
        }
    )
    
    # From confirmation, determine next step based on user response
    def route_after_confirmation(state: ConversationState) -> str:
        """Route based on confirmation result"""
        current_step = state.get("current_step", "process_visitor_type")
        
        if current_step == "collect_all_info":
            return "collect_all_info"  # Go back to collection if correction needed
        elif current_step == "confirmation":
            return "confirm_info"  # Stay in confirmation loop
        else:
            return "process_visitor_type"  # Proceed to visitor type processing
    
    workflow.add_conditional_edges(
        "confirm_info",
        route_after_confirmation,
        {
            "collect_all_info": "collect_all_info",
            "confirm_info": "confirm_info", 
            "process_visitor_type": "process_visitor_type"
        }
    )
    
    # From visitor type processing, determine next step
    def route_after_visitor_type(state: ConversationState) -> str:
        """Route based on determined visitor type"""
        current_step = state.get("current_step", "guidance")
        
        if current_step == "appointment_check":
            return "check_appointment"
        else:
            return "guide_visitor"
    
    workflow.add_conditional_edges(
        "process_visitor_type",
        route_after_visitor_type,
        {
            "check_appointment": "check_appointment",
            "guide_visitor": "guide_visitor"
        }
    )
    
    # From appointment check, always go to guidance
    workflow.add_edge("check_appointment", "guide_visitor")
    
    # From guidance, send Slack notification
    workflow.add_edge("guide_visitor", "send_slack")
    
    # From Slack notification, end the conversation
    workflow.add_edge("send_slack", END)
    
    # Set up memory checkpointer for conversation persistence
    memory = MemorySaver()
    
    # Compile the graph
    app = workflow.compile(checkpointer=memory)
    
    return app


class ReceptionGraphManager:
    """Manager class for the reception graph with session handling"""
    
    def __init__(self) -> None:
        self.graph = create_reception_graph()
    
    async def start_conversation(self, session_id: str) -> Dict[str, Any]:
        """Start a new conversation session - only run greeting node"""
        config = {
            "configurable": {"thread_id": session_id},
            "recursion_limit": 50
        }
        
        # Initialize conversation state
        initial_state = ConversationState(
            messages=[],
            visitor_info=None,
            current_step="greeting",
            calendar_result=None,
            error_count=0,
            session_id=session_id
        )
        
        try:
            # Only run the greeting node, don't execute the full graph
            from .nodes import ReceptionNodes
            nodes_instance = ReceptionNodes()
            
            print(f"Starting conversation for session {session_id}")
            print("Calling greeting_node only")
            
            # Run only the greeting node
            result = await nodes_instance.greeting_node(initial_state)
            
            # Save the initial state to graph memory with node specification
            await self.graph.aupdate_state(config, result, as_node="greeting")
            
            return {
                "success": True,
                "session_id": session_id,
                "message": result["messages"][-1].content if result["messages"] else "",
                "step": result["current_step"],
                "visitor_info": result.get("visitor_info")
            }
            
        except Exception as e:
            print(f"Conversation start error: {e}")
            return {
                "success": False,
                "session_id": session_id,
                "message": "システムエラーが発生しました。もう一度お試しください。",
                "step": "error",
                "visitor_info": None,
                "error": str(e)
            }
    
    async def send_message(self, session_id: str, message: str) -> Dict[str, Any]:
        """Send a message to an existing conversation"""
        config = {
            "configurable": {"thread_id": session_id},
            "recursion_limit": 50
        }
        
        try:
            # Get current state
            current_state = await self.graph.aget_state(config)
            
            if not current_state or not current_state.values:
                # Session not found or expired
                return {
                    "success": False,
                    "session_id": session_id,
                    "message": "セッションが見つかりません。新しい会話を開始してください。",
                    "step": "error",
                    "visitor_info": None,
                    "calendar_result": None,
                    "completed": False,
                    "error": "Session not found"
                }
            
            # Create human message
            from langchain_core.messages import HumanMessage
            human_message = HumanMessage(content=message)
            
            # Update state with user message - append to existing messages
            existing_messages = current_state.values.get("messages", [])
            updated_state = {
                **current_state.values,
                "messages": existing_messages + [human_message]
            }
            
            # Process the message through the graph from current step
            # Use astream_events to continue from current state instead of restarting
            current_step = current_state.values.get("current_step", "greeting")
            
            # For continuing conversation, we need to process from the current step
            # Since LangGraph always starts from entry point, we need to handle this differently
            
            # Directly invoke the appropriate node based on current step
            from .nodes import ReceptionNodes
            nodes_instance = ReceptionNodes()
            
            print(f"Processing message for session {session_id}, current step: {current_step}")
            print(f"User message: {message}")
            
            if current_step == "collect_all_info":
                print("Calling collect_all_info_node")
                result = await nodes_instance.collect_all_info_node(updated_state)
            elif current_step == "confirmation":
                print("Calling confirm_info_node (first time)")
                result = await nodes_instance.confirm_info_node(updated_state)
            elif current_step == "confirmation_response":
                print("Calling confirm_info_node (response handling)")
                result = await nodes_instance.confirm_info_node(updated_state)
            elif current_step == "process_visitor_type":
                print("Calling process_visitor_type_node")
                result = await nodes_instance.process_visitor_type_node(updated_state)
            elif current_step == "visitor_type_response":
                print("⚠️  visitor_type_response step should not be reached - auto-processing failed")
                # Fallback: call greeting to restart
                result = await nodes_instance.greeting_node(updated_state)
            elif current_step == "appointment_check":
                print("Calling check_appointment_node")
                result = await nodes_instance.check_appointment_node(updated_state)
            elif current_step == "guidance":
                print("Calling guide_visitor_node")
                result = await nodes_instance.guide_visitor_node(updated_state)
                
                # Auto-continue to Slack notification if guidance is complete
                if result.get("current_step") == "complete":
                    print("✅ Guidance completed, sending Slack notification")
                    slack_result = await nodes_instance.send_slack_node(result)
                    result = slack_result
            else:
                print(f"Unknown step {current_step}, calling greeting_node")
                # Fallback to greeting for unknown states
                result = await nodes_instance.greeting_node(updated_state)
            
            print(f"Node result: {result.get('current_step', 'no_step')}, message: {result.get('messages', [])[-1].content if result.get('messages') else 'no_message'}")
            
            # Update the state in the graph's memory with node specification
            result_step = result.get("current_step", current_step)
            node_name = {
                "collect_all_info": "collect_all_info",
                "confirmation": "confirm_info",
                "confirmation_response": "confirm_info", 
                "process_visitor_type": "process_visitor_type",
                "visitor_type_response": "process_visitor_type",
                "appointment_check": "check_appointment",
                "guidance": "guide_visitor",
                "complete": "send_slack"
            }.get(result_step, "collect_all_info")
            
            await self.graph.aupdate_state(config, result, as_node=node_name)
            
            return {
                "success": True,
                "session_id": session_id,
                "message": result["messages"][-1].content if result["messages"] else "",
                "step": result["current_step"],
                "visitor_info": result.get("visitor_info"),
                "calendar_result": result.get("calendar_result"),
                "completed": result["current_step"] == "complete"
            }
            
        except Exception as e:
            print(f"Message processing error: {e}")
            return {
                "success": False,
                "session_id": session_id,
                "message": "メッセージの処理中にエラーが発生しました。もう一度お試しください。",
                "step": "error",
                "visitor_info": None,
                "calendar_result": None,
                "completed": False,
                "error": str(e)
            }
    
    async def get_conversation_history(self, session_id: str) -> Dict[str, Any]:
        """Get conversation history for a session"""
        config = {
            "configurable": {"thread_id": session_id},
            "recursion_limit": 50
        }
        
        try:
            # Get current state
            current_state = await self.graph.aget_state(config)
            
            if not current_state or not current_state.values:
                return {
                    "success": False,
                    "session_id": session_id,
                    "messages": [],
                    "visitor_info": None,
                    "current_step": None,
                    "calendar_result": None,
                    "completed": False,
                    "error": "Session not found"
                }
            
            state = current_state.values
            
            # Format messages for response
            messages = []
            for msg in state.get("messages", []):
                messages.append({
                    "speaker": "visitor" if msg.__class__.__name__ == "HumanMessage" else "ai",
                    "content": msg.content,
                    "timestamp": getattr(msg, 'timestamp', None)
                })
            
            return {
                "success": True,
                "session_id": session_id,
                "messages": messages,
                "visitor_info": state.get("visitor_info"),
                "current_step": state.get("current_step"),
                "calendar_result": state.get("calendar_result"),
                "completed": state.get("current_step") == "complete"
            }
            
        except Exception as e:
            print(f"History retrieval error: {e}")
            return {
                "success": False,
                "session_id": session_id,
                "messages": [],
                "visitor_info": None,
                "current_step": None,
                "calendar_result": None,
                "completed": False,
                "error": str(e)
            }