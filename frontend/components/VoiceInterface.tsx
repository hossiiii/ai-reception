'use client';

import { useEffect, useRef, useState } from 'react';
import { useVoiceChat } from '@/hooks/useVoiceChat';
import VolumeReactiveMic from './VolumeReactiveMic';
import SimpleMessageDisplay from './SimpleMessageDisplay';

export interface VoiceInterfaceProps {
  sessionId?: string;
  onConversationEnd?: () => void;
  onError?: (error: string) => void;
  isGreeting?: boolean;
  onGreetingComplete?: () => void;
}

export default function VoiceInterface({
  sessionId: providedSessionId,
  onConversationEnd,
  onError,
  isGreeting = false,
  onGreetingComplete
}: VoiceInterfaceProps) {
  const onErrorRef = useRef(onError);
  const onGreetingCompleteRef = useRef(onGreetingComplete);
  const [showTextInput, setShowTextInput] = useState(false);
  const [textInputValue, setTextInputValue] = useState('');
  const [greetingPhaseCompleted, setGreetingPhaseCompleted] = useState(false);
  const [effectiveIsGreeting, setEffectiveIsGreeting] = useState(isGreeting);
  const [inputMode, setInputMode] = useState<'voice' | 'text'>('voice');
  const [isInputDisabled, setIsInputDisabled] = useState(false);
  const [userSelectedMode, setUserSelectedMode] = useState(false); // Track if user manually selected mode

  const {
    state,
    messages,
    startVoiceChat,
    stopVoiceChat,
    resetError,
    sendTextInput,
    startRecording,
    forceStopRecording
  } = useVoiceChat({
    sessionId: providedSessionId,
    autoStart: isGreeting,  // Auto-start when in greeting mode
    isGreeting: effectiveIsGreeting  // Pass effective greeting mode to hook
  });

  // Update refs when props change
  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);
  
  useEffect(() => {
    onGreetingCompleteRef.current = onGreetingComplete;
  }, [onGreetingComplete]);

  // Handle errors
  useEffect(() => {
    if (state.error && onErrorRef.current) {
      onErrorRef.current(state.error);
    }
  }, [state.error]);

  // Monitor AI response completion and handle mode-specific actions
  useEffect(() => {
    // Disable input during AI response
    if (state.isPlaying || state.isProcessing) {
      setIsInputDisabled(true);
      setUserSelectedMode(false); // Reset user selection flag during AI response
    } else if (!state.conversationCompleted) {
      // Enable input after AI finishes
      setIsInputDisabled(false);
      
      // Only auto-switch to voice if user hasn't manually selected a mode
      if (!userSelectedMode) {
        if (inputMode === 'text') {
          // Auto-switch back to voice mode after AI response (default behavior)
          setInputMode('voice');
          setShowTextInput(false);
          // Start recording after switching to voice mode
          if (state.conversationStarted && greetingPhaseCompleted) {
            setTimeout(() => {
              console.log('🎤 Auto-switching to voice input after AI response');
              startRecording();
            }, 500);
          }
        } else if (inputMode === 'voice' && state.conversationStarted && greetingPhaseCompleted) {
          // Resume recording in voice mode
          setTimeout(() => {
            console.log('🎤 Resuming voice recording after AI response');
            startRecording();
          }, 500);
        }
      } else {
        // User has manually selected mode, maintain their choice
        if (inputMode === 'voice' && state.conversationStarted && greetingPhaseCompleted) {
          // Only start recording if in voice mode
          setTimeout(() => {
            console.log('🎤 Starting recording in user-selected voice mode');
            startRecording();
          }, 500);
        } else if (inputMode === 'text') {
          // Make sure recording is stopped in text mode
          if (state.isRecording) {
            console.log('🔇 Stopping recording in text mode');
            forceStopRecording();
          }
        }
      }
    }
  }, [state.isPlaying, state.isProcessing, state.conversationCompleted, inputMode, 
      state.conversationStarted, greetingPhaseCompleted, startRecording, userSelectedMode, 
      state.isRecording, forceStopRecording]);

  // Handle greeting completion
  useEffect(() => {
    if (isGreeting && state.conversationStarted && !greetingPhaseCompleted) {
      // Mark greeting phase as completed when AI finishes speaking (after first message)
      if (!state.isPlaying && messages.length > 0 && messages[messages.length - 1]?.speaker === 'ai') {
        console.log('👋 Greeting phase completed - AI finished speaking');
        setGreetingPhaseCompleted(true);
        // Switch to normal mode for useVoiceChat
        setEffectiveIsGreeting(false);
        onGreetingCompleteRef.current?.();
        
        // Start recording after greeting is completed
        setTimeout(() => {
          console.log('🎤 Starting recording after greeting completion');
          startRecording();
        }, 1000); // Small delay to ensure audio playback is fully finished
      }
    }
  }, [isGreeting, state.conversationStarted, state.isPlaying, messages, greetingPhaseCompleted, startRecording]);

  // Handle conversation end
  useEffect(() => {
    if (state.conversationCompleted && !state.isPlaying && onConversationEnd) {
      console.log('🎬 Conversation completed and audio finished, starting 10 second timer for end transition');
      // Wait 10 seconds after conversation is completed AND audio is done playing
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
  }, [state.conversationCompleted, state.isPlaying, onConversationEnd]);

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
      // Keep text input mode open if user selected it
      if (!userSelectedMode) {
        setShowTextInput(false);
      }
    }
  };

  const handleInputModeChange = (mode: 'voice' | 'text') => {
    // Prevent switching during AI response
    if (isInputDisabled) {
      console.log('⚠️ Cannot switch input mode while AI is responding');
      return;
    }

    // Mark this as a user-initiated mode change
    setUserSelectedMode(true);

    // Always stop recording first when switching modes
    if (state.isRecording) {
      console.log('🔇 Force stopping recording before mode switch');
      forceStopRecording();
    }

    // Add a small delay to ensure recording is fully stopped
    setTimeout(() => {
      setInputMode(mode);
      
      if (mode === 'text') {
        setShowTextInput(true);
        // Double-check recording is stopped
        if (state.isRecording) {
          forceStopRecording();
        }
      } else {
        setShowTextInput(false);
        // Start recording when switching to voice mode
        if (state.conversationStarted && greetingPhaseCompleted) {
          setTimeout(() => {
            console.log('🎤 Starting recording after switching to voice mode');
            startRecording();
          }, 300);
        }
      }
    }, 100);
  };

  // Check if we should show text input option based on current step
  const shouldShowTextInputOption = () => {
    // Don't show text input during greeting phase
    if (isGreeting && !greetingPhaseCompleted) return false;
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
    if (isGreeting && !greetingPhaseCompleted) {
      if (state.isPlaying) return 'AIが挨拶しています...';
      if (state.conversationStarted) return '挨拶を開始します...';
      return '挨拶を準備中...';
    }
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
        <div className="p-6 md:p-8 bg-red-50 border border-red-200 rounded-2xl m-4">
          <div className="text-center text-red-800">
            <div className="text-xl md:text-2xl font-medium mb-4">エラーが発生しました</div>
            <div className="text-base md:text-lg mb-6">{state.error}</div>
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
        {/* Input mode selection with dynamic layout */}
        <div className="flex-1 flex flex-col items-center justify-center p-6">
          {shouldShowTextInputOption() && greetingPhaseCompleted ? (
            <>
              <div className="relative flex items-center justify-center w-full max-w-4xl" style={{ minHeight: '300px' }}>
                {/* Voice input (VolumeReactiveMic as button) */}
                <div
                  className={`
                    absolute transition-all duration-500 ease-in-out
                    ${inputMode === 'voice' 
                      ? 'left-1/2 -translate-x-1/2 scale-100 z-10' 
                      : 'left-0 translate-x-0 scale-[0.7] opacity-60 z-0'}
                  `}
                >
                  <VolumeReactiveMic
                    volume={state.vadVolume || 0}
                    isActive={state.vadActive && inputMode === 'voice'}
                    isRecording={state.isRecording && inputMode === 'voice'}
                    status={inputMode === 'voice' ? getStatusText() : '音声入力'}
                    statusColor={inputMode === 'voice' ? getStatusColor() : 'text-gray-400'}
                    onClick={() => !isInputDisabled && handleInputModeChange('voice')}
                    isClickable={!isInputDisabled && inputMode !== 'voice'}
                  />
                </div>

                {/* Text input button */}
                <div
                  className={`
                    absolute transition-all duration-500 ease-in-out
                    ${inputMode === 'text' 
                      ? 'left-1/2 -translate-x-1/2 scale-100 z-10' 
                      : 'right-0 translate-x-0 scale-[0.7] opacity-60 z-0'}
                  `}
                >
                  <div className="flex flex-col items-center justify-center space-y-6">
                    <div className="relative">
                      <button
                        onClick={() => handleInputModeChange('text')}
                        disabled={isInputDisabled}
                        className={`
                          w-40 h-40 rounded-full border-4 transition-all duration-300
                          flex items-center justify-center
                          ${inputMode === 'text'
                            ? 'bg-primary-100 border-primary-500 text-primary-600'
                            : 'bg-gray-100 border-gray-300 text-gray-400 hover:border-gray-400'}
                          ${isInputDisabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                        `}
                        style={{ width: '160px', height: '160px' }}
                      >
                        <svg
                          className="w-16 h-16 transition-colors duration-300"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                          />
                        </svg>
                      </button>
                    </div>
                    <div className="text-center">
                      <div className={`text-xl md:text-2xl font-semibold transition-all duration-300 ${inputMode === 'text' ? 'text-primary-600' : 'text-gray-400'}`}>
                        {inputMode === 'text' ? 'テキスト入力中' : 'テキスト入力'}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Text Input Area - moved below buttons */}
              {showTextInput && inputMode === 'text' && (
                <div className="w-full max-w-2xl mt-8">
                  <div className="bg-gray-50 rounded-2xl p-4 md:p-6">
                    <div className="flex space-x-2">
                      <input
                        type="text"
                        value={textInputValue}
                        onChange={(e) => setTextInputValue(e.target.value)}
                        placeholder="ここに入力してください"
                        className="flex-1 px-4 py-3 md:px-6 md:py-4 text-base md:text-lg border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        autoFocus
                      />
                      <button
                        onClick={handleTextInputSubmit}
                        disabled={!textInputValue.trim() || state.isProcessing}
                        className="px-6 py-3 md:px-8 md:py-4 text-base md:text-lg bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        送信
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </>
          ) : (
            /* Default microphone display when text input is not available */
            <VolumeReactiveMic
              volume={state.vadVolume || 0}
              isActive={state.vadActive && greetingPhaseCompleted}
              isRecording={state.isRecording && greetingPhaseCompleted}
              status={getStatusText()}
              statusColor={getStatusColor()}
            />
          )}
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
        <div className="p-6 md:p-8 bg-green-50 border border-green-200 rounded-2xl m-4 text-center">
          <div className="text-green-800">
            <div className="text-xl md:text-2xl font-medium mb-4">対応完了</div>
            <div className="text-base md:text-lg mb-6">ありがとうございました</div>
            <button
              onClick={handleEndConversation}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
              終了
            </button>
          </div>
        </div>
      )}


      {/* Simple Controls */}
      <div className="p-6 flex-shrink-0">
        {isGreeting && !greetingPhaseCompleted ? (
          /* Greeting mode - no controls */
          <div className="text-center">
            <p className="text-gray-600">
              AIがご挨拶しています。しばらくお待ちください。
            </p>
          </div>
        ) : !state.conversationStarted ? (
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
          /* Simple controls - only show after greeting is completed */
          <div className="text-center space-y-4">
            {/* Status message when input is disabled */}
            {isInputDisabled ? (
              <p className="text-sm text-amber-600 font-medium">
                AIが応答中です。しばらくお待ちください...
              </p>
            ) : null}
            
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