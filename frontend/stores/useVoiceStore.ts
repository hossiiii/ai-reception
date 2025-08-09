/**
 * Phase 4: Voice状態管理用Zustandストア
 * 音声チャット関連の状態を統合管理
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { 
  VoiceError,
  ConnectionState,
  RecordingState,
  PlaybackState,
  VADState
} from '@/types/voice';
import type { ConversationMessage } from '@/hooks/useConversationFlow';

export interface VoiceStateCore {
  // Connection state
  connectionState: ConnectionState;
  connectionError: VoiceError | null;
  
  // Recording state
  recordingState: RecordingState;
  hasPermission: boolean;
  recordingError: VoiceError | null;
  
  // Playback state
  playbackState: PlaybackState;
  playbackError: VoiceError | null;
  lastAudioId: string | null;
  
  // VAD state
  vadState: VADState;
  vadEnergy: number;
  vadVolume: number;
  vadConfidence: number;
  isListening: boolean;
  
  // Conversation state
  messages: ConversationMessage[];
  currentStep: string;
  isProcessing: boolean;
  conversationStarted: boolean;
  conversationCompleted: boolean;
  
  // Business data
  visitorInfo?: any;
  calendarResult?: any;
  
  // Session info
  sessionId: string;
}

export interface VoiceActions {
  // Session actions
  setSessionId: (sessionId: string) => void;
  
  // Connection actions
  setConnectionState: (state: ConnectionState, error?: VoiceError | null) => void;
  
  // Recording actions
  setRecordingState: (state: RecordingState, error?: VoiceError | null) => void;
  setHasPermission: (hasPermission: boolean) => void;
  
  // Playback actions
  setPlaybackState: (state: PlaybackState, error?: VoiceError | null) => void;
  setLastAudioId: (audioId: string | null) => void;
  
  // VAD actions
  setVADState: (state: VADState) => void;
  setVADMetrics: (energy: number, volume: number, confidence: number) => void;
  setIsListening: (listening: boolean) => void;
  
  // Conversation actions
  addMessage: (message: ConversationMessage) => void;
  updateConversationState: (updates: {
    currentStep?: string;
    isProcessing?: boolean;
    conversationStarted?: boolean;
    conversationCompleted?: boolean;
    visitorInfo?: any;
    calendarResult?: any;
  }) => void;
  
  // Reset actions
  resetVoiceState: () => void;
  resetConversation: () => void;
}

export type VoiceStore = VoiceStateCore & VoiceActions;

// Initial state
const createInitialState = (sessionId: string = 'default'): VoiceStateCore => ({
  // Connection state
  connectionState: 'disconnected',
  connectionError: null,
  
  // Recording state
  recordingState: 'idle',
  hasPermission: false,
  recordingError: null,
  
  // Playback state
  playbackState: 'idle',
  playbackError: null,
  lastAudioId: null,
  
  // VAD state
  vadState: 'inactive',
  vadEnergy: 0,
  vadVolume: 0,
  vadConfidence: 0,
  isListening: false,
  
  // Conversation state
  messages: [],
  currentStep: 'initial',
  isProcessing: false,
  conversationStarted: false,
  conversationCompleted: false,
  
  // Business data
  visitorInfo: undefined,
  calendarResult: undefined,
  
  // Session info
  sessionId,
});

export const useVoiceStore = create<VoiceStore>()(
  devtools(
    (set, get) => ({
      ...createInitialState(),
      
      // Session actions
      setSessionId: (sessionId) => 
        set({ sessionId }, false, 'setSessionId'),
      
      // Connection actions
      setConnectionState: (connectionState, connectionError = null) => 
        set({ connectionState, connectionError }, false, 'setConnectionState'),
      
      // Recording actions
      setRecordingState: (recordingState, recordingError = null) => 
        set({ recordingState, recordingError }, false, 'setRecordingState'),
        
      setHasPermission: (hasPermission) => 
        set({ hasPermission }, false, 'setHasPermission'),
      
      // Playback actions
      setPlaybackState: (playbackState, playbackError = null) => 
        set({ playbackState, playbackError }, false, 'setPlaybackState'),
        
      setLastAudioId: (lastAudioId) => 
        set({ lastAudioId }, false, 'setLastAudioId'),
      
      // VAD actions
      setVADState: (vadState) => 
        set({ vadState }, false, 'setVADState'),
        
      setVADMetrics: (vadEnergy, vadVolume, vadConfidence) => 
        set({ 
          vadEnergy, 
          vadVolume, 
          vadConfidence 
        }, false, 'setVADMetrics'),
        
      setIsListening: (isListening) => 
        set({ isListening }, false, 'setIsListening'),
      
      // Conversation actions
      addMessage: (message) => {
        const currentMessages = get().messages;
        set({ 
          messages: [...currentMessages, message] 
        }, false, 'addMessage');
      },
      
      updateConversationState: (updates) => 
        set(updates, false, 'updateConversationState'),
      
      // Reset actions
      resetVoiceState: () => {
        const currentSessionId = get().sessionId;
        console.log('🔄 Resetting voice state');
        set(createInitialState(currentSessionId), false, 'resetVoiceState');
      },
      
      resetConversation: () => {
        console.log('🔄 Resetting conversation');
        set({ 
          messages: [],
          currentStep: 'initial',
          isProcessing: false,
          conversationStarted: false,
          conversationCompleted: false,
          visitorInfo: undefined,
          calendarResult: undefined
        }, false, 'resetConversation');
      },
    }),
    {
      name: 'voice-store',
    }
  )
);

// セレクター関数（パフォーマンス最適化用）
export const useVoiceSelector = {
  // Session selectors
  sessionId: () => useVoiceStore((state) => state.sessionId),
  
  // Connection selectors
  connectionState: () => useVoiceStore((state) => state.connectionState),
  isConnected: () => useVoiceStore((state) => state.connectionState === 'connected'),
  isConnecting: () => useVoiceStore((state) => state.connectionState === 'connecting'),
  connectionError: () => useVoiceStore((state) => state.connectionError),
  
  // Recording selectors
  recordingState: () => useVoiceStore((state) => state.recordingState),
  isRecording: () => useVoiceStore((state) => state.recordingState === 'recording'),
  hasPermission: () => useVoiceStore((state) => state.hasPermission),
  recordingError: () => useVoiceStore((state) => state.recordingError),
  
  // Playback selectors
  playbackState: () => useVoiceStore((state) => state.playbackState),
  isPlaying: () => useVoiceStore((state) => state.playbackState === 'playing'),
  playbackError: () => useVoiceStore((state) => state.playbackError),
  
  // VAD selectors
  vadState: () => useVoiceStore((state) => state.vadState),
  vadActive: () => useVoiceStore((state) => state.vadState !== 'inactive'),
  vadMetrics: () => useVoiceStore((state) => ({
    energy: state.vadEnergy,
    volume: state.vadVolume,
    confidence: state.vadConfidence
  })),
  isListening: () => useVoiceStore((state) => state.isListening),
  
  // Conversation selectors
  messages: () => useVoiceStore((state) => state.messages),
  messageCount: () => useVoiceStore((state) => state.messages.length),
  lastMessage: () => useVoiceStore((state) => {
    const messages = state.messages;
    return messages.length > 0 ? messages[messages.length - 1] : null;
  }),
  currentStep: () => useVoiceStore((state) => state.currentStep),
  isProcessing: () => useVoiceStore((state) => state.isProcessing),
  conversationStarted: () => useVoiceStore((state) => state.conversationStarted),
  conversationCompleted: () => useVoiceStore((state) => state.conversationCompleted),
  
  // Business data selectors
  visitorInfo: () => useVoiceStore((state) => state.visitorInfo),
  calendarResult: () => useVoiceStore((state) => state.calendarResult),
  
  // Combined state selectors
  allErrors: () => useVoiceStore((state) => [
    state.connectionError,
    state.recordingError,
    state.playbackError
  ].filter(Boolean) as VoiceError[]),
  
  hasErrors: () => useVoiceStore((state) => 
    state.connectionError !== null || 
    state.recordingError !== null || 
    state.playbackError !== null
  ),
  
  canRecord: () => useVoiceStore((state) => 
    state.connectionState === 'connected' &&
    state.recordingState === 'idle' &&
    state.hasPermission &&
    !state.isProcessing &&
    state.playbackState === 'idle'
  ),
  
  canPlayAudio: () => useVoiceStore((state) => 
    state.playbackState === 'idle' &&
    state.recordingState !== 'recording'
  ),
  
  // Legacy compatibility selectors (for backward compatibility)
  state: () => useVoiceStore((state) => ({
    // Connection states
    connectionState: state.connectionState,
    isConnected: state.connectionState === 'connected',
    isConnecting: state.connectionState === 'connecting',
    
    // Recording states
    recordingState: state.recordingState,
    isRecording: state.recordingState === 'recording',
    hasPermission: state.hasPermission,
    isListening: state.isListening,
    
    // Processing state
    isProcessing: state.isProcessing,
    
    // Playback states
    playbackState: state.playbackState,
    isPlaying: state.playbackState === 'playing',
    
    // VAD states
    vadActive: state.vadState !== 'inactive',
    vadEnergy: state.vadEnergy,
    vadVolume: state.vadVolume,
    vadConfidence: state.vadConfidence,
    
    // Conversation states
    conversationStarted: state.conversationStarted,
    conversationCompleted: state.conversationCompleted,
    currentStep: state.currentStep,
    
    // Error handling (backward compatible)
    errors: [state.connectionError, state.recordingError, state.playbackError].filter(Boolean) as VoiceError[],
    hasErrors: state.connectionError !== null || state.recordingError !== null || state.playbackError !== null,
    error: state.connectionError?.message || state.recordingError?.message || state.playbackError?.message || null,
    
    // Business data
    visitorInfo: state.visitorInfo,
    calendarResult: state.calendarResult,
  })),
};

// Actions を別途エクスポート
export const useVoiceActions = () => useVoiceStore((state) => ({
  // Session
  setSessionId: state.setSessionId,
  
  // Connection
  setConnectionState: state.setConnectionState,
  
  // Recording
  setRecordingState: state.setRecordingState,
  setHasPermission: state.setHasPermission,
  
  // Playback
  setPlaybackState: state.setPlaybackState,
  setLastAudioId: state.setLastAudioId,
  
  // VAD
  setVADState: state.setVADState,
  setVADMetrics: state.setVADMetrics,
  setIsListening: state.setIsListening,
  
  // Conversation
  addMessage: state.addMessage,
  updateConversationState: state.updateConversationState,
  
  // Reset
  resetVoiceState: state.resetVoiceState,
  resetConversation: state.resetConversation,
}));