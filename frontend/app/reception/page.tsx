'use client';

import { useEffect } from 'react';
import VoiceInterface from '@/components/VoiceInterface';
import ReceptionButton from '@/components/ReceptionButton';
import { apiClient } from '@/lib/api';
import { useReceptionStore } from '@/stores/useReceptionStore';

export default function ReceptionPage() {
  // Phase 4: Use Zustand store selectors to avoid infinite loops
  const sessionId = useReceptionStore(state => state.sessionId);
  const isLoading = useReceptionStore(state => state.isLoading);
  const error = useReceptionStore(state => state.error);
  const isSystemReady = useReceptionStore(state => state.isSystemReady);
  const showCountdown = useReceptionStore(state => state.showCountdown);
  const countdownValue = useReceptionStore(state => state.countdownValue);
  const isGreeting = useReceptionStore(state => state.isGreeting);
  const showWelcome = useReceptionStore(state => state.showWelcome);
  
  const setSessionId = useReceptionStore(state => state.setSessionId);
  const setIsLoading = useReceptionStore(state => state.setIsLoading);
  const setError = useReceptionStore(state => state.setError);
  const setIsSystemReady = useReceptionStore(state => state.setIsSystemReady);
  const setShowCountdown = useReceptionStore(state => state.setShowCountdown);
  const setCountdownValue = useReceptionStore(state => state.setCountdownValue);
  const setIsGreeting = useReceptionStore(state => state.setIsGreeting);
  const setShowWelcome = useReceptionStore(state => state.setShowWelcome);
  const handleGreetingComplete = useReceptionStore(state => state.handleGreetingComplete);
  const resetReception = useReceptionStore(state => state.resetReception);
  const resetSession = useReceptionStore(state => state.resetSession);

  // Check system health on mount (don't auto-start greeting)
  useEffect(() => {
    checkSystemHealth();
  }, []);

  // handleGreetingComplete is now provided by the store

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

  const handleStartConversation = async () => {
    if (!isSystemReady) {
      setError('システムが利用できません。');
      return;
    }

    setShowWelcome(false);  // Hide welcome screen
    setIsLoading(true);
    setError(null);

    try {
      const response = await apiClient.startConversation();
      
      if (response.success) {
        setSessionId(response.session_id);
        setIsGreeting(true);  // Start greeting mode
      } else {
        throw new Error(response.error || '会話の開始に失敗しました');
      }
    } catch (error) {
      console.error('Failed to start conversation:', error);
      setError(error instanceof Error ? error.message : '会話の開始に失敗しました');
      setShowWelcome(true);  // Show welcome screen again on error
    } finally {
      setIsLoading(false);
    }
  };

  const handleConversationEnd = () => {
    // Start countdown instead of immediately resetting
    setShowCountdown(true);
    setCountdownValue(5);
  };


  // Countdown effect
  useEffect(() => {
    if (showCountdown && countdownValue > 0) {
      const timer = setTimeout(() => {
        setCountdownValue(prev => prev - 1);
      }, 1000);
      return () => clearTimeout(timer);
    } else if (showCountdown && countdownValue === 0) {
      // Reset to welcome screen using store action
      resetReception();
    }
    // Add return statement for all code paths
    return undefined;
  }, [showCountdown, countdownValue]);

  const handleError = (errorMessage: string) => {
    setError(errorMessage);
  };

  const handleRetry = () => {
    resetReception();
    checkSystemHealth();
  };

  return (
    <div className="h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Main content */}
      <main className="h-full p-4 overflow-hidden">
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
                <h2 className="text-2xl font-semibold text-gray-900 mb-4">
                  エラーが発生しました
                </h2>
                <p className="text-xl text-gray-600 mb-8">
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
          ) : sessionId && !showWelcome ? (
            /* Voice interface or countdown */
            <div className="h-full">
              {showCountdown ? (
                /* Countdown screen */
                <div className="flex items-center justify-center h-full">
                  <div className="text-center">
                    <div className="mb-8">
                      <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-6">
                        ご利用ありがとうございました
                      </h2>
                      <p className="text-2xl md:text-3xl text-gray-600 mb-10">
                        まもなく受付開始画面に戻ります
                      </p>
                    </div>
                    
                    <div className="w-32 h-32 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-8">
                      <span className="text-5xl font-bold text-primary-600">
                        {countdownValue}
                      </span>
                    </div>
                    
                    <div className="text-xl text-gray-500">
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
            /* Welcome screen */
            <div className="flex items-center justify-center h-full">
              <div className="text-center max-w-2xl">
                {/* Welcome message */}
                <div className="mb-12">
                  <div className="w-32 h-32 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-8">
                    <svg
                      className="w-16 h-16 text-primary-600"
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
                  
                  <h1 className="text-6xl md:text-7xl font-bold text-gray-900 mb-8">
                    いらっしゃいませ
                  </h1>
                  
                  <p className="text-3xl md:text-4xl text-gray-600 mb-12 leading-relaxed">
                    こちらは音声対話受付システムです。<br />
                    下のボタンを押して音声受付を開始してください。
                  </p>
                </div>

                {/* Start button */}
                <ReceptionButton
                  onStartConversation={handleStartConversation}
                  disabled={!isSystemReady}
                  loading={isLoading}
                />

                {/* Instructions */}
                <div className="mt-12 p-6 bg-blue-50 rounded-2xl">
                  <h3 className="text-xl md:text-2xl font-semibold text-blue-900 mb-6">
                    ご利用方法
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-base md:text-lg text-blue-800">
                    <div className="flex items-center space-x-2 md:space-x-3">
                      <div className="w-6 h-6 md:w-8 md:h-8 bg-blue-200 rounded-full flex items-center justify-center text-xs md:text-sm font-bold">
                        1
                      </div>
                      <span className="font-medium">「受付開始」ボタンを押す</span>
                    </div>
                    <div className="flex items-center space-x-2 md:space-x-3">
                      <div className="w-6 h-6 md:w-8 md:h-8 bg-blue-200 rounded-full flex items-center justify-center text-xs md:text-sm font-bold">
                        2
                      </div>
                      <span className="font-medium">お名前と会社名を音声で話す</span>
                    </div>
                    <div className="flex items-center space-x-2 md:space-x-3">
                      <div className="w-6 h-6 md:w-8 md:h-8 bg-blue-200 rounded-full flex items-center justify-center text-xs md:text-sm font-bold">
                        3
                      </div>
                      <span className="font-medium">AIが音声で適切にご案内</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>

    </div>
  );
}