'use client';

import { useEffect, useRef } from 'react';
import { useVoiceChat } from '@/hooks/useVoiceChat';
import AudioVisualizer from './AudioVisualizer';
import ConversationDisplay from './ConversationDisplay';

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
    startRecording,
    stopRecording,
    playLastResponse,
    resetError
  } = useVoiceChat({
    sessionId: providedSessionId,
    autoStart: false
  });

  const onErrorRef = useRef(onError);

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
      setTimeout(() => {
        onConversationEnd();
      }, 10000); // 10 seconds delay like ChatInterface
    }
  }, [state.conversationCompleted, onConversationEnd]);

  // Convert ConversationMessage to format expected by ConversationDisplay
  const displayMessages = messages.map(msg => ({
    speaker: msg.speaker,
    content: msg.content,
    timestamp: msg.timestamp
  }));

  const handleStartChat = async () => {
    const success = await startVoiceChat();
    if (success) {
      // Auto-start recording after connection
      setTimeout(() => {
        startRecording();
      }, 1000);
    }
  };

  const handleEndConversation = () => {
    stopVoiceChat();
    onConversationEnd?.();
  };

  const handleToggleRecording = () => {
    if (state.isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  const getConnectionStatusText = () => {
    if (state.isConnecting) return '接続中...';
    if (!state.isConnected) return '未接続';
    if (state.isProcessing) return '処理中...';
    if (state.isPlaying) return '音声再生中...';
    if (state.isRecording && state.vadActive) return '音声検出中...';
    if (state.isRecording) return '音声待機中...';
    return '準備完了';
  };

  const getStatusColor = () => {
    if (state.error) return 'text-red-600';
    if (state.isProcessing || state.isConnecting) return 'text-yellow-600';
    if (state.isConnected && state.conversationStarted) return 'text-green-600';
    return 'text-gray-600';
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-2xl shadow-soft">
      {/* Header */}
      <div className="flex items-center justify-between p-6 border-b border-gray-200 flex-shrink-0">
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
                d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
              />
            </svg>
          </div>
          <div>
            <h2 className="font-semibold text-gray-900">
              AI音声受付対応
            </h2>
            <p className={`text-sm ${getStatusColor()}`}>
              {state.conversationCompleted 
                ? '対応完了' 
                : getConnectionStatusText()}
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
        <div className="mx-6 mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex-shrink-0">
          <div className="flex items-center justify-between">
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
            <button
              onClick={resetError}
              className="text-sm text-red-600 hover:text-red-800 font-medium"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Messages area */}
      <div className="flex-1 overflow-hidden">
        <ConversationDisplay
          messages={displayMessages}
          isLoading={state.isProcessing}
          isTyping={state.isProcessing}
          visitorInfo={state.visitorInfo}
        />
      </div>

      {/* Audio Visualizer */}
      <div className="mx-6 mb-4 flex-shrink-0">
        <AudioVisualizer
          isActive={state.vadActive}
          energy={state.vadEnergy}
          volume={state.vadVolume}
          confidence={state.vadConfidence}
          isRecording={state.isRecording}
          isPlaying={state.isPlaying}
        />
      </div>

      {/* Completion message */}
      {state.conversationCompleted && (
        <div className="mx-6 mb-4 p-4 bg-green-50 border border-green-200 rounded-lg flex-shrink-0">
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

      {/* Voice Controls */}
      <div className="p-6 border-t border-gray-200 flex-shrink-0">
        {!state.conversationStarted ? (
          /* Start Voice Chat Button */
          <button
            onClick={handleStartChat}
            disabled={state.isConnecting}
            className="w-full btn-primary py-6 text-xl rounded-2xl disabled:opacity-50 disabled:cursor-not-allowed touch-safe"
          >
            {state.isConnecting ? (
              <div className="flex items-center justify-center space-x-2">
                <div className="loading-spinner border-white border-t-transparent w-6 h-6"></div>
                <span>接続中...</span>
              </div>
            ) : (
              <div className="flex items-center justify-center space-x-2">
                <svg
                  className="w-8 h-8"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
                  />
                </svg>
                <span>音声受付を開始</span>
              </div>
            )}
          </button>
        ) : (
          /* Voice Control Buttons */
          <div className="flex space-x-4">
            {/* Recording Toggle */}
            <button
              onClick={handleToggleRecording}
              disabled={state.isProcessing || state.conversationCompleted}
              className={`flex-1 py-4 px-6 rounded-2xl text-lg font-medium transition-all duration-200 touch-safe ${
                state.isRecording
                  ? 'bg-red-600 hover:bg-red-700 text-white'
                  : 'bg-green-600 hover:bg-green-700 text-white'
              } disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              <div className="flex items-center justify-center space-x-2">
                {state.isRecording ? (
                  <>
                    <div className="w-4 h-4 bg-white rounded-sm"></div>
                    <span>録音停止</span>
                  </>
                ) : (
                  <>
                    <svg
                      className="w-6 h-6"
                      fill="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                    </svg>
                    <span>録音開始</span>
                  </>
                )}
              </div>
            </button>

            {/* Replay Last Response */}
            <button
              onClick={playLastResponse}
              disabled={state.isProcessing || state.isPlaying}
              className="px-6 py-4 bg-blue-600 hover:bg-blue-700 text-white rounded-2xl font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed touch-safe"
              aria-label="最後の応答を再生"
            >
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
                  d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1.586a1 1 0 01.707.293l2.414 2.414a1 1 0 00.707.293H15a2 2 0 002-2V9a2 2 0 00-2-2h-1.586a1 1 0 01-.707-.293L9.293 4.293A1 1 0 008.586 4H7a2 2 0 00-2 2v8a2 2 0 002 2h1.586a1 1 0 01.707.293l2.414 2.414A1 1 0 0013.414 20H15a2 2 0 002-2v-1a2 2 0 00-2-2h-1.586a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 008.586 14H7a2 2 0 00-2-2V9z"
                />
              </svg>
            </button>
          </div>
        )}
        
        {/* Helper text */}
        <div className="mt-3 text-center text-xs text-gray-500">
          {!state.conversationStarted 
            ? 'マイクへのアクセス許可が必要です' 
            : state.conversationCompleted
            ? '対応完了'
            : state.isRecording
            ? 'お話しください'
            : '録音ボタンを押してください'}
        </div>
      </div>
    </div>
  );
}