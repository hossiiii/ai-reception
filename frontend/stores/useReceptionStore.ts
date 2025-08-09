/**
 * Phase 4: Reception状態管理用Zustandストア
 * 分散したReception関連の状態を一元管理
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { VoiceError } from '@/types/voice';

export interface ReceptionState {
  // Session management
  sessionId: string | null;
  
  // Loading states
  isLoading: boolean;
  isSystemReady: boolean;
  
  // Error handling
  error: string | null;
  voiceError: VoiceError | null;
  
  // UI states
  showWelcome: boolean;
  showCountdown: boolean;
  countdownValue: number;
  
  // Greeting flow
  isGreeting: boolean;
  greetingCompleted: boolean;
  
  // Input mode selection
  inputMode: 'voice' | 'text' | null;
  userSelectedMode: boolean;
}

export interface ReceptionActions {
  // Session actions
  setSessionId: (sessionId: string | null) => void;
  
  // Loading actions
  setIsLoading: (loading: boolean) => void;
  setIsSystemReady: (ready: boolean) => void;
  
  // Error actions
  setError: (error: string | null) => void;
  setVoiceError: (error: VoiceError | null) => void;
  clearErrors: () => void;
  
  // UI actions
  setShowWelcome: (show: boolean) => void;
  setShowCountdown: (show: boolean) => void;
  setCountdownValue: (value: number) => void;
  
  // Greeting actions
  setIsGreeting: (greeting: boolean) => void;
  setGreetingCompleted: (completed: boolean) => void;
  handleGreetingComplete: () => void;
  
  // Input mode actions
  setInputMode: (mode: 'voice' | 'text' | null) => void;
  setUserSelectedMode: (selected: boolean) => void;
  
  // Reset actions
  resetReception: () => void;
  resetSession: () => void;
}

export type ReceptionStore = ReceptionState & ReceptionActions;

// Initial state
const initialState: ReceptionState = {
  // Session management
  sessionId: null,
  
  // Loading states
  isLoading: false,
  isSystemReady: false,
  
  // Error handling
  error: null,
  voiceError: null,
  
  // UI states
  showWelcome: true,
  showCountdown: false,
  countdownValue: 5,
  
  // Greeting flow
  isGreeting: false,
  greetingCompleted: false,
  
  // Input mode selection
  inputMode: null,
  userSelectedMode: false,
};

export const useReceptionStore = create<ReceptionStore>()(
  devtools(
    (set, get) => ({
      ...initialState,
      
      // Session actions
      setSessionId: (sessionId) => 
        set({ sessionId }, false, 'setSessionId'),
      
      // Loading actions
      setIsLoading: (isLoading) => 
        set({ isLoading }, false, 'setIsLoading'),
        
      setIsSystemReady: (isSystemReady) => 
        set({ isSystemReady }, false, 'setIsSystemReady'),
      
      // Error actions
      setError: (error) => 
        set({ error }, false, 'setError'),
        
      setVoiceError: (voiceError) => 
        set({ voiceError }, false, 'setVoiceError'),
        
      clearErrors: () => 
        set({ error: null, voiceError: null }, false, 'clearErrors'),
      
      // UI actions
      setShowWelcome: (showWelcome) => 
        set({ showWelcome }, false, 'setShowWelcome'),
        
      setShowCountdown: (showCountdown) => 
        set({ showCountdown }, false, 'setShowCountdown'),
        
      setCountdownValue: (countdownValue) => 
        set({ countdownValue }, false, 'setCountdownValue'),
      
      // Greeting actions
      setIsGreeting: (isGreeting) => 
        set({ isGreeting }, false, 'setIsGreeting'),
        
      setGreetingCompleted: (greetingCompleted) => 
        set({ greetingCompleted }, false, 'setGreetingCompleted'),
        
      handleGreetingComplete: () => {
        console.log('🎭 Greeting completed via store');
        set({ 
          isGreeting: false, 
          greetingCompleted: true 
        }, false, 'handleGreetingComplete');
      },
      
      // Input mode actions
      setInputMode: (inputMode) => 
        set({ inputMode }, false, 'setInputMode'),
        
      setUserSelectedMode: (userSelectedMode) => 
        set({ userSelectedMode }, false, 'setUserSelectedMode'),
      
      // Reset actions
      resetReception: () => {
        console.log('🔄 Resetting reception state');
        set({ ...initialState }, false, 'resetReception');
      },
      
      resetSession: () => {
        console.log('🔄 Resetting session');
        set({ 
          sessionId: null,
          isGreeting: false,
          greetingCompleted: false,
          inputMode: null,
          userSelectedMode: false,
          error: null,
          voiceError: null,
          isLoading: false
        }, false, 'resetSession');
      },
    }),
    {
      name: 'reception-store', // デバッグ用の名前
    }
  )
);

// セレクター関数（パフォーマンス最適化用）
export const useReceptionSelector = {
  // Session selectors
  sessionId: () => useReceptionStore((state) => state.sessionId),
  hasActiveSession: () => useReceptionStore((state) => state.sessionId !== null),
  
  // Loading selectors
  isLoading: () => useReceptionStore((state) => state.isLoading),
  isSystemReady: () => useReceptionStore((state) => state.isSystemReady),
  
  // Error selectors
  error: () => useReceptionStore((state) => state.error),
  voiceError: () => useReceptionStore((state) => state.voiceError),
  hasErrors: () => useReceptionStore((state) => 
    state.error !== null || state.voiceError !== null
  ),
  
  // UI selectors
  showWelcome: () => useReceptionStore((state) => state.showWelcome),
  showCountdown: () => useReceptionStore((state) => state.showCountdown),
  countdownValue: () => useReceptionStore((state) => state.countdownValue),
  
  // Greeting selectors
  isGreeting: () => useReceptionStore((state) => state.isGreeting),
  greetingCompleted: () => useReceptionStore((state) => state.greetingCompleted),
  isInGreetingFlow: () => useReceptionStore((state) => 
    state.isGreeting || !state.greetingCompleted
  ),
  
  // Input mode selectors
  inputMode: () => useReceptionStore((state) => state.inputMode),
  userSelectedMode: () => useReceptionStore((state) => state.userSelectedMode),
  hasSelectedInputMode: () => useReceptionStore((state) => 
    state.inputMode !== null && state.userSelectedMode
  ),
  
  // Combined state selectors
  canStartConversation: () => useReceptionStore((state) => 
    state.isSystemReady && !state.isLoading && state.error === null
  ),
  
  isReadyForVoiceInput: () => useReceptionStore((state) => 
    state.sessionId !== null && 
    state.inputMode === 'voice' && 
    state.greetingCompleted && 
    !state.isLoading
  ),
};

// Actions を別途エクスポート（テスト等で使用）
export const useReceptionActions = () => useReceptionStore((state) => ({
  // Session
  setSessionId: state.setSessionId,
  
  // Loading
  setIsLoading: state.setIsLoading,
  setIsSystemReady: state.setIsSystemReady,
  
  // Errors
  setError: state.setError,
  setVoiceError: state.setVoiceError,
  clearErrors: state.clearErrors,
  
  // UI
  setShowWelcome: state.setShowWelcome,
  setShowCountdown: state.setShowCountdown,
  setCountdownValue: state.setCountdownValue,
  
  // Greeting
  setIsGreeting: state.setIsGreeting,
  setGreetingCompleted: state.setGreetingCompleted,
  handleGreetingComplete: state.handleGreetingComplete,
  
  // Input mode
  setInputMode: state.setInputMode,
  setUserSelectedMode: state.setUserSelectedMode,
  
  // Reset
  resetReception: state.resetReception,
  resetSession: state.resetSession,
}));