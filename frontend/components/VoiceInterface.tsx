'use client';

import { useEffect, useRef, useState } from 'react';
import { useVoiceChat } from '@/hooks/useVoiceChat';
import VolumeReactiveMic from './VolumeReactiveMic';
import SimpleMessageDisplay from './SimpleMessageDisplay';

export interface VoiceInterfaceProps {
  sessionId?: string;
  onConversationEnd?: () => void;
  onError?: (error: string) => void;
}

export default function VoiceInterface({
  sessionId: providedSessionId,
  onConversationEnd,
  onError
}: VoiceInterfaceProps) {
  const {
    state,
    messages,
    startVoiceChat,
    stopVoiceChat,
    resetError,
    sendTextInput
  } = useVoiceChat({
    sessionId: providedSessionId,
    autoStart: false
  });

  const onErrorRef = useRef(onError);
  const [showTextInput, setShowTextInput] = useState(false);
  const [textInputValue, setTextInputValue] = useState('');

  // Update ref when onError changes
  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  // Handle errors
  useEffect(() => {
    if (state.error && onErrorRef.current) {
      onErrorRef.current(state.error);
    }
  }, [state.error]);

  // Handle conversation end
  useEffect(() => {
    if (state.conversationCompleted && onConversationEnd) {
      console.log('🎬 Conversation completed detected, starting 10 second timer for end transition');
      // Wait 10 seconds after conversation is completed (audio is already done playing)
      const timer = setTimeout(() => {
        console.log('🎬 10 second timer completed, calling onConversationEnd');
        onConversationEnd();
      }, 10000);
      
      return () => {
        console.log('🎬 Cleaning up conversation end timer');
        clearTimeout(timer);
      };
    }
    // Add return statement for all code paths
    return undefined;
  }, [state.conversationCompleted, onConversationEnd]);

  // Use messages directly for SimpleMessageDisplay

  const handleStartChat = async () => {
    await startVoiceChat();
    // VADが自動で音声を検知して録音を開始するため、
    // 手動での録音開始は不要
  };

  const handleEndConversation = () => {
    stopVoiceChat();
    onConversationEnd?.();
  };


  const handleTextInputSubmit = () => {
    if (textInputValue.trim()) {
      sendTextInput(textInputValue);
      setTextInputValue('');
      setShowTextInput(false);
    }
  };

  // Check if we should show text input option based on current step
  const shouldShowTextInputOption = () => {
    // Show text input option during confirmation step (when collecting name/company)
    return state.currentStep === 'collect_all_info' || 
           state.currentStep === 'confirmation_response' ||
           state.currentStep === 'confirmation_check';
  };

  const getStatusText = () => {
    if (state.conversationCompleted) return '対応完了';
    if (state.isConnecting) return '接続中...';
    if (!state.isConnected) return '未接続';
    if (state.isProcessing) return '処理中...';
    if (state.isPlaying) return '音声再生中...';
    if (state.isRecording && state.vadActive) return '音声を検出中...';
    if (state.isRecording) return 'お話しください';
    if (state.isListening) return '話しかけてください';
    return '準備完了';
  };

  const getStatusColor = () => {
    if (state.error) return 'text-red-600';
    if (state.isRecording && state.vadActive) return 'text-blue-600 font-semibold';
    if (state.isProcessing || state.isConnecting) return 'text-yellow-600';
    if (state.isConnected && state.conversationStarted) return 'text-green-600';
    if (state.conversationCompleted) return 'text-green-600';
    return 'text-gray-600';
  };


  return (
    <div className="flex flex-col h-full bg-white rounded-2xl shadow-soft">

      {/* Error display */}
      {state.error && (
        <div className="p-6 bg-red-50 border border-red-200 rounded-2xl m-4">
          <div className="text-center text-red-800">
            <div className="text-lg font-medium mb-2">エラーが発生しました</div>
            <div className="text-sm mb-4">{state.error}</div>
            <button
              onClick={resetError}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              再試行
            </button>
          </div>
        </div>
      )}

      {/* Main content area */}
      <div className="flex-1 flex flex-col">
        {/* Volume-reactive microphone */}
        <div className="flex-1 flex items-center justify-center p-6">
          <VolumeReactiveMic
            volume={state.vadVolume || 0}
            isActive={state.vadActive}
            isRecording={state.isRecording}
            status={getStatusText()}
            statusColor={getStatusColor()}
          />
        </div>
        
        {/* Messages display */}
        <div className="flex-shrink-0">
          <SimpleMessageDisplay
            messages={messages}
            isLoading={state.isProcessing}
            isTyping={state.isProcessing}
            visitorInfo={state.visitorInfo}
          />
        </div>
      </div>

      {/* Completion message */}
      {state.conversationCompleted && (
        <div className="p-6 bg-green-50 border border-green-200 rounded-2xl m-4 text-center">
          <div className="text-green-800">
            <div className="text-lg font-medium mb-2">対応完了</div>
            <div className="text-sm mb-4">ありがとうございました</div>
            <button
              onClick={handleEndConversation}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
              終了
            </button>
          </div>
        </div>
      )}

      {/* Text Input Section */}
      {showTextInput && (
        <div className="p-4 bg-gray-50 rounded-2xl m-4">
          <div className="text-center">
            <p className="text-sm text-gray-700 mb-4">
              テキストで入力してください
            </p>
            <div className="flex space-x-2">
              <input
                type="text"
                value={textInputValue}
                onChange={(e) => setTextInputValue(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleTextInputSubmit()}
                placeholder="ここに入力してください"
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                autoFocus
              />
              <button
                onClick={handleTextInputSubmit}
                disabled={!textInputValue.trim() || state.isProcessing}
                className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                送信
              </button>
              <button
                onClick={() => setShowTextInput(false)}
                className="px-4 py-2 text-gray-600 hover:text-gray-800 hover:bg-gray-200 rounded-lg transition-colors"
              >
                ✕
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Simple Controls */}
      <div className="p-6 flex-shrink-0">
        {!state.conversationStarted ? (
          /* Start Voice Chat Button */
          <button
            onClick={handleStartChat}
            disabled={state.isConnecting}
            className="w-full btn-primary py-6 text-xl rounded-2xl disabled:opacity-50 disabled:cursor-not-allowed touch-safe"
          >
            {state.isConnecting ? (
              <span>接続中...</span>
            ) : (
              <span>音声受付を開始</span>
            )}
          </button>
        ) : (
          /* Simple controls */
          <div className="text-center space-y-4">
            {/* Text input option (only when appropriate) */}
            {shouldShowTextInputOption() && !showTextInput && (
              <button
                onClick={() => setShowTextInput(true)}
                className="w-full py-3 px-4 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg font-medium transition-colors"
              >
                テキストで入力する
              </button>
            )}
            
            
            {/* End conversation button */}
            <button
              onClick={handleEndConversation}
              className="px-6 py-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
            >
              会話を終了
            </button>
          </div>
        )}
      </div>
    </div>
  );
}