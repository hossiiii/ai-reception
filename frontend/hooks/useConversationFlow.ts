/**
 * Conversation flow management hook
 * Handles messages, conversation state, and business logic data
 */

import { useState, useCallback } from 'react';

export interface ConversationMessage {
  speaker: 'visitor' | 'ai';
  content: string;
  timestamp: string;
  audioData?: string; // base64 for AI responses
}

export interface ConversationState {
  conversationStarted: boolean;
  conversationCompleted: boolean;
  currentStep: string;
  isProcessing: boolean;
  
  // Business data
  visitorInfo?: any;
  calendarResult?: any;
}

export interface UseConversationFlowReturn {
  // State
  state: ConversationState;
  messages: ConversationMessage[];
  
  // Actions
  addMessage: (message: ConversationMessage) => void;
  updateConversationState: (updates: Partial<ConversationState>) => void;
  sendTextInput: (text: string, onSend?: (text: string) => void) => void;
  resetConversation: () => void;
  
  // Getters
  lastMessage: ConversationMessage | null;
  visitorMessages: ConversationMessage[];
  aiMessages: ConversationMessage[];
}

const initialState: ConversationState = {
  conversationStarted: false,
  conversationCompleted: false,
  currentStep: 'greeting',
  isProcessing: false,
  visitorInfo: undefined,
  calendarResult: undefined
};

export function useConversationFlow(): UseConversationFlowReturn {
  // Conversation state
  const [state, setState] = useState<ConversationState>(initialState);
  
  // Messages
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  
  // Update conversation state helper
  const updateConversationState = useCallback((updates: Partial<ConversationState>) => {
    setState(prev => ({ ...prev, ...updates }));
  }, []);
  
  // Add message to conversation
  const addMessage = useCallback((message: ConversationMessage) => {
    console.log(`💬 Adding ${message.speaker} message:`, message.content);
    setMessages(prev => [...prev, message]);
  }, []);
  
  // Send text input
  const sendTextInput = useCallback((text: string, onSend?: (text: string) => void) => {
    if (!text.trim()) {
      console.log('⚠️ Cannot send empty text input');
      return;
    }
    
    // Add visitor message immediately
    const visitorMessage: ConversationMessage = {
      speaker: 'visitor',
      content: text.trim(),
      timestamp: new Date().toISOString()
    };
    
    addMessage(visitorMessage);
    
    // Set processing state
    updateConversationState({ isProcessing: true });
    
    // Call external send function if provided
    if (onSend) {
      onSend(text.trim());
    }
    
    console.log('📤 Text input sent:', text.trim());
  }, [addMessage, updateConversationState]);
  
  // Reset conversation
  const resetConversation = useCallback(() => {
    setState(initialState);
    setMessages([]);
    console.log('🔄 Conversation reset');
  }, []);
  
  // Getters
  const lastMessage = messages.length > 0 ? messages[messages.length - 1] : null;
  const visitorMessages = messages.filter(msg => msg.speaker === 'visitor');
  const aiMessages = messages.filter(msg => msg.speaker === 'ai');
  
  return {
    state,
    messages,
    addMessage,
    updateConversationState,
    sendTextInput,
    resetConversation,
    lastMessage,
    visitorMessages,
    aiMessages
  };
}