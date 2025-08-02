'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { ChatInterfaceProps, ConversationMessage, VisitorInfo, ChatState } from '@/lib/types';
import { apiClient, getErrorMessage } from '@/lib/api';
import ConversationDisplay from './ConversationDisplay';

export default function ChatInterface({
  sessionId,
  onConversationEnd,
  onError
}: ChatInterfaceProps) {
  const [state, setState] = useState<ChatState>({
    isLoading: false,
    isTyping: false,
    error: null,
    sessionId: sessionId || null,
    conversationStarted: false,
    conversationCompleted: false
  });

  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [visitorInfo, setVisitorInfo] = useState<VisitorInfo | undefined>();
  const [inputMessage, setInputMessage] = useState('');
  const [isInputDisabled, setIsInputDisabled] = useState(false);
  const [loadedSessionId, setLoadedSessionId] = useState<string | null>(null);

  const inputRef = useRef<HTMLInputElement>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const onErrorRef = useRef(onError);

  // Update ref when onError changes
  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  const loadConversation = useCallback(async () => {
    if (!sessionId) return;

    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const response = await apiClient.getConversationHistory(sessionId);
      
      if (response.success) {
        // Ensure messages are unique to prevent duplicates
        const uniqueMessages = response.messages.filter((message, index, arr) => {
          return index === arr.findIndex(m => 
            m.content === message.content && 
            m.speaker === message.speaker && 
            m.timestamp === message.timestamp
          );
        });
        setMessages(uniqueMessages);
        setVisitorInfo(response.visitor_info);
        setState(prev => ({
          ...prev,
          conversationStarted: true,
          conversationCompleted: response.completed,
          isLoading: false
        }));
        
        // Mark this sessionId as loaded
        setLoadedSessionId(sessionId);
        
        // Disable input if conversation is completed
        setIsInputDisabled(response.completed);
      } else {
        throw new Error(response.error || 'Failed to load conversation');
      }
    } catch (error) {
      const errorMessage = getErrorMessage(error);
      setState(prev => ({ ...prev, error: errorMessage, isLoading: false }));
      onErrorRef.current?.(errorMessage);
    }
  }, [sessionId]);

  // Load conversation on mount or sessionId change - only once per sessionId
  useEffect(() => {
    if (sessionId && sessionId !== loadedSessionId && !state.conversationStarted) {
      loadConversation();
    }
  }, [sessionId, loadedSessionId, state.conversationStarted]); // Remove loadConversation from dependencies

  // Focus input when not disabled
  useEffect(() => {
    if (!isInputDisabled && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isInputDisabled, state.conversationCompleted]);

  const sendMessage = async (message: string) => {
    if (!sessionId || !message.trim() || state.isLoading || state.conversationCompleted) {
      return;
    }

    const userMessage: ConversationMessage = {
      speaker: 'visitor',
      content: message.trim(),
      timestamp: new Date().toISOString()
    };

    // Add user message immediately
    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setState(prev => ({ ...prev, isLoading: true, isTyping: true, error: null }));

    try {
      const response = await apiClient.sendMessage(sessionId, message.trim());
      
      if (response.success) {
        // Add AI response
        const aiMessage: ConversationMessage = {
          speaker: 'ai',
          content: response.message,
          timestamp: new Date().toISOString()
        };
        
        // Prevent duplicate messages by checking if the same content already exists
        setMessages(prev => {
          const isDuplicate = prev.some(msg => 
            msg.content === aiMessage.content && 
            msg.speaker === aiMessage.speaker
          );
          return isDuplicate ? prev : [...prev, aiMessage];
        });
        
        // Update visitor info if provided
        if (response.visitor_info) {
          setVisitorInfo(response.visitor_info);
        }
        
        // Check if conversation is completed
        if (response.completed || response.step === 'complete') {
          setState(prev => ({ 
            ...prev, 
            conversationCompleted: true,
            isLoading: false,
            isTyping: false
          }));
          setIsInputDisabled(true);
          
          // Auto-end conversation after a delay
          setTimeout(() => {
            handleEndConversation();
          }, 10000); // 10 seconds delay
        } else {
          setState(prev => ({ 
            ...prev, 
            isLoading: false,
            isTyping: false
          }));
        }
      } else {
        throw new Error(response.error || 'Failed to send message');
      }
    } catch (error) {
      const errorMessage = getErrorMessage(error);
      setState(prev => ({ ...prev, error: errorMessage, isLoading: false, isTyping: false }));
      onErrorRef.current?.(errorMessage);
      
      // Remove the user message if there was an error
      setMessages(prev => prev.slice(0, -1));
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputMessage.trim() && !state.isLoading && !state.conversationCompleted) {
      sendMessage(inputMessage);
    }
  };

  const handleEndConversation = async () => {
    if (sessionId) {
      try {
        await apiClient.endConversation(sessionId);
      } catch (error) {
        console.error('Failed to end conversation:', error);
      }
    }
    onConversationEnd?.();
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (inputMessage.trim() && !state.isLoading && !state.conversationCompleted) {
        sendMessage(inputMessage);
      }
    }
  };

  return (
    <div className="flex flex-col h-full max-h-[calc(100vh-120px)] bg-white rounded-2xl shadow-soft">
      {/* Header */}
      <div className="flex items-center justify-between p-6 border-b border-gray-200">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
            <svg
              className="w-5 h-5 text-primary-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
              />
            </svg>
          </div>
          <div>
            <h2 className="font-semibold text-gray-900">
              AI受付対応
            </h2>
            <p className="text-sm text-gray-500">
              {state.conversationCompleted 
                ? '対応完了' 
                : state.isLoading 
                ? '処理中...' 
                : 'お気軽にお話しください'}
            </p>
          </div>
        </div>
        
        {/* End conversation button */}
        <button
          onClick={handleEndConversation}
          className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
          aria-label="会話を終了"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>

      {/* Error display */}
      {state.error && (
        <div className="mx-6 mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-center space-x-2">
            <svg
              className="w-5 h-5 text-red-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"
              />
            </svg>
            <p className="text-sm text-red-800">{state.error}</p>
          </div>
        </div>
      )}

      {/* Messages area */}
      <div className="flex-1 min-h-0">
        <ConversationDisplay
          messages={messages}
          isLoading={state.isLoading}
          isTyping={state.isTyping}
          visitorInfo={visitorInfo}
        />
      </div>

      {/* Completion message */}
      {state.conversationCompleted && (
        <div className="mx-6 mb-4 p-4 bg-green-50 border border-green-200 rounded-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <svg
                className="w-5 h-5 text-green-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <p className="text-sm text-green-800 font-medium">
                対応が完了しました。ありがとうございました。
              </p>
            </div>
            <button
              onClick={handleEndConversation}
              className="text-sm text-green-600 hover:text-green-800 font-medium"
            >
              終了
            </button>
          </div>
        </div>
      )}

      {/* Input area */}
      <div className="p-6 border-t border-gray-200">
        <form ref={formRef} onSubmit={handleSubmit} className="flex space-x-4">
          <input
            ref={inputRef}
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={isInputDisabled || state.isLoading}
            placeholder={
              state.conversationCompleted 
                ? '対応が完了しました' 
                : state.isLoading 
                ? '処理中...' 
                : 'メッセージを入力してください...'
            }
            className="input-primary-lg flex-1 disabled:bg-gray-100 disabled:cursor-not-allowed"
            maxLength={500}
            autoComplete="off"
            autoCorrect="off"
            autoCapitalize="off"
          />
          
          <button
            type="submit"
            disabled={!inputMessage.trim() || isInputDisabled || state.isLoading}
            className="btn-primary px-8 py-4 text-lg rounded-2xl disabled:opacity-50 disabled:cursor-not-allowed touch-safe"
          >
            {state.isLoading ? (
              <div className="loading-spinner border-white border-t-transparent w-5 h-5"></div>
            ) : (
              <svg
                className="w-6 h-6"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                />
              </svg>
            )}
          </button>
        </form>
        
        {/* Input helper text */}
        <div className="mt-2 flex items-center justify-between text-xs text-gray-500">
          <span>
            {state.conversationCompleted 
              ? '対応完了' 
              : 'Enterキーで送信'}
          </span>
          <span>{inputMessage.length}/500</span>
        </div>
      </div>
    </div>
  );
}