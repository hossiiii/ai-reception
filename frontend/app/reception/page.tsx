'use client';

import { useState, useEffect } from 'react';
import VoiceInterface from '@/components/VoiceInterface';
import { apiClient } from '@/lib/api';

export default function ReceptionPage() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSystemReady, setIsSystemReady] = useState(false);
  const [showCountdown, setShowCountdown] = useState(false);
  const [countdownValue, setCountdownValue] = useState(5);
  const [isGreeting, setIsGreeting] = useState(false);
  const [greetingCompleted, setGreetingCompleted] = useState(false);

  // Check system health and start greeting on mount
  useEffect(() => {
    checkSystemHealth().then(() => {
      startGreeting();
    });
  }, []);

  const startGreeting = async () => {
    setIsGreeting(true);
    try {
      // Start conversation session for greeting
      const response = await apiClient.startConversation();
      if (response.success) {
        setSessionId(response.session_id);
        // Greeting will be handled by VoiceInterface automatically
      } else {
        throw new Error(response.error || '挨拶の開始に失敗しました');
      }
    } catch (error) {
      console.error('Failed to start greeting:', error);
      setError(error instanceof Error ? error.message : '挨拶の開始に失敗しました');
      setIsGreeting(false);
    }
  };

  const handleGreetingComplete = () => {
    console.log('Greeting completed');
    setIsGreeting(false);
    setGreetingCompleted(true);
  };

  const checkSystemHealth = async () => {
    try {
      await apiClient.healthCheck();
      setIsSystemReady(true);
    } catch (error) {
      console.error('System health check failed:', error);
      setIsSystemReady(false);
      setError('システムに接続できません。管理者にお問い合わせください。');
    }
  };

  // This function is no longer needed as conversation starts automatically with greeting

  const handleConversationEnd = () => {
    // Start countdown instead of immediately resetting
    setShowCountdown(true);
    setCountdownValue(5);
  };

  const handleRestartGreeting = () => {
    setGreetingCompleted(false);
    setSessionId(null);
    setError(null);
    startGreeting();
  };

  // Countdown effect
  useEffect(() => {
    if (showCountdown && countdownValue > 0) {
      const timer = setTimeout(() => {
        setCountdownValue(prev => prev - 1);
      }, 1000);
      return () => clearTimeout(timer);
    } else if (showCountdown && countdownValue === 0) {
      // Reset to greeting screen
      setShowCountdown(false);
      setSessionId(null);
      setError(null);
      setCountdownValue(5);
      setGreetingCompleted(false);
      startGreeting();
    }
    // Add return statement for all code paths
    return undefined;
  }, [showCountdown, countdownValue]);

  const handleError = (errorMessage: string) => {
    setError(errorMessage);
  };

  const handleRetry = () => {
    setError(null);
    setSessionId(null);
    setGreetingCompleted(false);
    checkSystemHealth().then(() => {
      startGreeting();
    });
  };

  return (
    <div className="flex flex-col h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Header */}
      <header className="bg-white shadow-soft flex-shrink-0">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
                <svg
                  className="w-5 h-5 text-white"
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
              <h1 className="text-xl font-semibold text-gray-900">
                AI音声受付システム
              </h1>
            </div>
            
            {/* System status */}
            <div className="flex items-center space-x-2">
              <div className={isSystemReady ? 'status-online' : 'status-error'}></div>
              <span className="text-sm text-gray-600">
                {isSystemReady ? 'システム稼働中' : 'システムエラー'}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 p-4 overflow-hidden">
        <div className="max-w-4xl mx-auto h-full">
          {error ? (
            /* Error state */
            <div className="flex items-center justify-center h-full">
              <div className="card-lg text-center max-w-md">
                <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg
                    className="w-8 h-8 text-red-600"
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
                </div>
                <h2 className="text-xl font-semibold text-gray-900 mb-2">
                  エラーが発生しました
                </h2>
                <p className="text-gray-600 mb-6">
                  {error}
                </p>
                <button
                  onClick={handleRetry}
                  className="btn-primary"
                >
                  再試行
                </button>
              </div>
            </div>
          ) : sessionId && (isGreeting || greetingCompleted) ? (
            /* Voice interface or countdown */
            <div className="h-full">
              {showCountdown ? (
                /* Countdown screen */
                <div className="flex items-center justify-center h-full">
                  <div className="text-center">
                    <div className="mb-8">
                      <h2 className="text-3xl font-bold text-gray-900 mb-4">
                        ご利用ありがとうございました
                      </h2>
                      <p className="text-xl text-gray-600 mb-8">
                        まもなく受付開始画面に戻ります
                      </p>
                    </div>
                    
                    <div className="w-32 h-32 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-8">
                      <span className="text-5xl font-bold text-primary-600">
                        {countdownValue}
                      </span>
                    </div>
                    
                    <div className="text-gray-500">
                      {countdownValue > 0 ? '受付開始画面に戻るまで' : '画面を切り替えています...'}
                    </div>
                  </div>
                </div>
              ) : (
                <VoiceInterface
                  sessionId={sessionId}
                  onConversationEnd={handleConversationEnd}
                  onError={handleError}
                  isGreeting={isGreeting}
                  onGreetingComplete={handleGreetingComplete}
                />
              )}
            </div>
          ) : (
            /* Loading/Preparing screen */
            <div className="flex items-center justify-center h-full">
              <div className="text-center max-w-2xl">
                <div className="w-32 h-32 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-8">
                  <svg
                    className="w-16 h-16 text-primary-600 animate-pulse"
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
                
                <h1 className="text-5xl font-bold text-gray-900 mb-6">
                  いらっしゃいませ
                </h1>
                
                <p className="text-2xl text-gray-600 mb-8 leading-relaxed">
                  AI受付システムを準備しています...
                </p>
                
                {!isSystemReady && (
                  <div className="text-lg text-gray-500 animate-pulse">
                    システム初期化中
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 py-4 flex-shrink-0">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between text-sm text-gray-500">
            <div>
              AI Reception System v2.0.0
            </div>
            <div className="flex items-center space-x-4">
              <span>Step2: Voice-enabled Reception</span>
              {process.env.NODE_ENV === 'development' && (
                <span className="px-2 py-1 bg-yellow-100 text-yellow-800 rounded text-xs">
                  Development
                </span>
              )}
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}