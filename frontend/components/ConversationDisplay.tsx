'use client';

import { useEffect, useRef } from 'react';
import { ConversationDisplayProps, ConversationMessage } from '@/lib/types';

export default function ConversationDisplay({
  messages,
  isLoading,
  isTyping,
  visitorInfo
}: ConversationDisplayProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ 
      behavior: 'smooth',
      block: 'end'
    });
  };

  const formatMessage = (content: string) => {
    // Simple formatting for line breaks and basic structure
    return content
      .split('\n')
      .map((line, index) => (
        <span key={index}>
          {line}
          {index < content.split('\n').length - 1 && <br />}
        </span>
      ));
  };

  const getMessageTime = (message: ConversationMessage) => {
    if (message.timestamp) {
      return new Date(message.timestamp).toLocaleTimeString('ja-JP', {
        hour: '2-digit',
        minute: '2-digit'
      });
    }
    return new Date().toLocaleTimeString('ja-JP', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const renderMessage = (message: ConversationMessage, index: number) => {
    const isAI = message.speaker === 'ai';
    const isVisitor = message.speaker === 'visitor';
    // Create a more stable key using timestamp and content
    const messageKey = `${message.timestamp || index}-${message.speaker}-${message.content.slice(0, 20)}`;

    return (
      <div
        key={messageKey}
        className={`flex ${isVisitor ? 'justify-end' : 'justify-start'} mb-6 animate-slide-up`}
      >
        <div className={`flex max-w-[80%] ${isVisitor ? 'flex-row-reverse' : 'flex-row'} items-start space-x-3`}>
          {/* Avatar */}
          <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center ${
            isAI ? 'bg-gray-100' : 'bg-primary-100'
          }`}>
            {isAI ? (
              <svg
                className="w-6 h-6 text-gray-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                />
              </svg>
            ) : (
              <svg
                className="w-6 h-6 text-primary-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                />
              </svg>
            )}
          </div>

          {/* Message bubble */}
          <div className={`flex flex-col ${isVisitor ? 'items-end' : 'items-start'}`}>
            {/* Speaker label */}
            <div className="mb-1 text-xs text-gray-500 px-1">
              {isAI ? 'AI受付' : (visitorInfo?.name || '来訪者')}
            </div>
            
            {/* Message content */}
            <div className={`px-6 py-4 rounded-2xl shadow-sm ${
              isAI 
                ? 'message-ai' 
                : 'message-visitor'
            }`}>
              <div className={`text-base leading-relaxed ${
                isAI ? 'text-gray-800' : 'text-white'
              }`}>
                {formatMessage(message.content)}
              </div>
            </div>
            
            {/* Timestamp */}
            <div className="mt-1 text-xs text-gray-400 px-1">
              {getMessageTime(message)}
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Visitor info bar (if available) */}
      {visitorInfo && visitorInfo.confirmed && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-4 mx-4 flex-shrink-0">
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 bg-green-500 rounded-full"></div>
            <span className="text-sm font-medium text-green-800">
              {visitorInfo.name}様 ({visitorInfo.company})
            </span>
            {visitorInfo.visitor_type && (
              <span className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded-full">
                {visitorInfo.visitor_type === 'appointment' ? '予約来客' :
                 visitorInfo.visitor_type === 'sales' ? '営業訪問' :
                 visitorInfo.visitor_type === 'delivery' ? '配達業者' : '不明'}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Messages container */}
      <div 
        ref={containerRef}
        className="flex-1 overflow-y-auto scrollbar-hide px-4 py-2"
      >
        {/* Initial welcome message for empty conversation */}
        {messages.length === 0 && !isLoading && (
          <div className="text-center text-gray-500 mt-8">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg
                className="w-8 h-8 text-gray-400"
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
            <p>AIが応答をお待ちしています...</p>
          </div>
        )}

        {/* Messages */}
        {messages.map((message, index) => renderMessage(message, index))}

        {/* Typing indicator */}
        {isTyping && (
          <div className="flex justify-start mb-6">
            <div className="flex items-start space-x-3">
              {/* AI Avatar */}
              <div className="flex-shrink-0 w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center">
                <svg
                  className="w-6 h-6 text-gray-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                  />
                </svg>
              </div>

              {/* Typing bubble */}
              <div className="message-ai">
                <div className="loading-dots">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Loading indicator */}
        {isLoading && !isTyping && (
          <div className="text-center py-4">
            <div className="inline-flex items-center space-x-2 text-gray-500">
              <div className="loading-spinner"></div>
              <span>処理中...</span>
            </div>
          </div>
        )}

        {/* Auto-scroll anchor */}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
}