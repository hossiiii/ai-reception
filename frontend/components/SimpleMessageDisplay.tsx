'use client';

import { ConversationMessage } from '@/lib/types';

interface SimpleMessageDisplayProps {
  messages: ConversationMessage[];
  isLoading: boolean;
  isTyping: boolean;
  visitorInfo?: {
    name?: string;
    company?: string;
    visitor_type?: string;
    confirmed?: boolean;
  };
}

export default function SimpleMessageDisplay({
  messages,
  isLoading,
  isTyping,
  visitorInfo
}: SimpleMessageDisplayProps) {
  // 最新のAIメッセージと最新のユーザーメッセージを取得
  const getLatestMessages = () => {
    const aiMessages = messages.filter(m => m.speaker === 'ai');
    const visitorMessages = messages.filter(m => m.speaker === 'visitor');
    
    const latestAI = aiMessages.length > 0 ? aiMessages[aiMessages.length - 1] : null;
    const latestVisitor = visitorMessages.length > 0 ? visitorMessages[visitorMessages.length - 1] : null;
    
    return { latestAI, latestVisitor };
  };

  const { latestAI, latestVisitor } = getLatestMessages();

  const formatMessage = (content: string) => {
    return content
      .split('\n')
      .map((line, index) => (
        <span key={index}>
          {line}
          {index < content.split('\n').length - 1 && <br />}
        </span>
      ));
  };

  return (
    <div className="flex flex-col space-y-6 p-6 h-full justify-center">
      {/* Visitor info (if available) */}
      {visitorInfo && visitorInfo.confirmed && (
        <div className="text-center p-4 bg-green-50 border border-green-200 rounded-2xl">
          <div className="flex items-center justify-center space-x-2">
            <div className="w-3 h-3 bg-green-500 rounded-full"></div>
            <span className="text-lg font-medium text-green-800">
              {visitorInfo.name}様 ({visitorInfo.company})
            </span>
          </div>
        </div>
      )}

      {/* Latest visitor message */}
      {latestVisitor && (
        <div className="bg-primary-100 rounded-2xl p-6 text-center">
          <div className="text-sm text-primary-600 font-medium mb-2">
            来訪者の入力
          </div>
          <div className="text-lg text-primary-800">
            {formatMessage(latestVisitor.content)}
          </div>
        </div>
      )}

      {/* Typing indicator */}
      {isTyping && (
        <div className="bg-gray-100 rounded-2xl p-6 text-center">
          <div className="text-sm text-gray-600 font-medium mb-2">
            AI受付
          </div>
          <div className="flex items-center justify-center space-x-2">
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse"></div>
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse" style={{ animationDelay: '0.1s' }}></div>
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
          </div>
        </div>
      )}

      {/* Latest AI response */}
      {latestAI && !isTyping && (
        <div className="bg-gray-100 rounded-2xl p-6 text-center">
          <div className="text-sm text-gray-600 font-medium mb-2">
            AI受付からのご案内
          </div>
          <div className="text-lg text-gray-800">
            {formatMessage(latestAI.content)}
          </div>
        </div>
      )}

      {/* Initial state */}
      {messages.length === 0 && !isLoading && !isTyping && (
        <div className="text-center text-gray-500">
          <div className="text-xl mb-2">お話しください</div>
          <div className="text-sm">AIが対応させていただきます</div>
        </div>
      )}

      {/* Loading indicator */}
      {isLoading && !isTyping && messages.length === 0 && (
        <div className="text-center">
          <div className="inline-flex items-center space-x-2 text-gray-500">
            <div className="w-4 h-4 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin"></div>
            <span>準備中...</span>
          </div>
        </div>
      )}
    </div>
  );
}