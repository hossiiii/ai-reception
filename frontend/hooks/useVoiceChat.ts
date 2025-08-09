/**
 * Refactored Voice chat hook - Main integration hook
 * Combines specialized hooks for connection, recording, playback, conversation, and VAD
 */

import { useState, useRef, useCallback } from 'react';
import { 
  VoiceError, 
  createConnectionError, 
  createValidationError,
  ConnectionState,
  RecordingState,
  PlaybackState
} from '@/types/voice';

// Phase 4: Import Zustand stores (for future use)
// import { useVoiceStore, useVoiceSelector, useVoiceActions } from '@/stores/useVoiceStore';

// Import specialized hooks
import { useVoiceConnection } from './useVoiceConnection';
import { useVoiceRecording } from './useVoiceRecording';
import { useVoicePlayback } from './useVoicePlayback';
import { useConversationFlow, ConversationMessage } from './useConversationFlow';
import { useVADIntegration } from './useVADIntegration';

// Phase 3: Import effect management hooks
import { useVoiceMessageHandlers } from './useVoiceMessageHandlers';
import { useVoiceAutoStart } from './useVoiceAutoStart';
import { useGreetingMode } from './useGreetingMode';

// Re-export types for backward compatibility
export type { ConversationMessage } from './useConversationFlow';

export interface VoiceState {
  // Connection state
  connectionState: ConnectionState;
  isConnected: boolean;
  isConnecting: boolean;
  
  // Recording state  
  recordingState: RecordingState;
  isRecording: boolean;
  hasPermission: boolean;
  isListening: boolean;
  
  // Processing states
  isProcessing: boolean;
  
  // Playback state
  playbackState: PlaybackState;
  isPlaying: boolean;
  
  // VAD states
  vadActive: boolean;
  vadEnergy: number;
  vadVolume: number;
  vadConfidence: number;
  
  // Conversation states
  conversationStarted: boolean;
  conversationCompleted: boolean;
  currentStep: string;
  
  // Error handling (typed errors)
  errors: VoiceError[];
  hasErrors: boolean;
  error: string | null; // Backward compatibility
  
  // Visitor information
  visitorInfo?: any;
  calendarResult?: any;
}

export interface UseVoiceChatOptions {
  sessionId?: string;
  autoStart?: boolean;
  isGreeting?: boolean;
  vadConfig?: {
    energyThreshold?: number;
    silenceDuration?: number;
    minSpeechDuration?: number;
  };
}

export interface UseVoiceChatReturn {
  // State
  state: VoiceState;
  messages: ConversationMessage[];
  
  // Actions
  startVoiceChat: () => Promise<boolean>;
  stopVoiceChat: () => void;
  startRecording: () => Promise<boolean>;
  stopRecording: () => void;
  forceStopRecording: () => void;
  playLastResponse: () => void;
  resetError: () => void;
  sendTextInput: (text: string) => void;
  
  // Utility
  sessionId: string;
}

// Simple UUID generation function
function generateSessionId(): string {
  return 'session-' + Math.random().toString(36).substr(2, 9) + '-' + Date.now().toString(36);
}

export function useVoiceChat(options: UseVoiceChatOptions = {}): UseVoiceChatReturn {
  // Generate session ID
  const sessionId = useRef(options.sessionId || generateSessionId()).current;
  
  // Phase 4: Zustand integration temporarily disabled to fix infinite loop
  // const voiceState = useVoiceSelector.state();
  // const voiceActions = useVoiceActions();
  
  // Initialize session ID in store
  // useEffect(() => {
  //   voiceActions.setSessionId(sessionId);
  // }, [sessionId, voiceActions]);
  
  // Error state (temporary bridge during migration)
  const [, setError] = useState<VoiceError | null>(null);
  
  // Phase 3: Use greeting mode management hook
  const { isGreetingRef } = useGreetingMode({ isGreeting: options.isGreeting });
  
  // Initialize specialized hooks
  const connection = useVoiceConnection({ 
    sessionId,
    autoConnect: false 
  });
  
  const recording = useVoiceRecording(
    connection.client,
    {
      sampleRate: 16000,
      channels: 1,
      chunkSize: 100
    }
  );
  
  const playback = useVoicePlayback();
  
  const conversation = useConversationFlow();
  
  const vad = useVADIntegration({
    vadConfig: options.vadConfig,
    onSpeechStart: () => {
      // Auto-start recording is disabled in current implementation
      // console.log('👂 VAD detected speech start - could auto-start recording');
    },
    onSpeechEnd: () => {
      // Auto-stop recording if currently recording and not processing
      if (recording.state.state === 'recording' && !conversation.state.isProcessing) {
        console.log('👂 VAD detected speech end - auto-stopping recording and VAD');
        setTimeout(() => {
          recording.stopRecording();
          // Stop VAD listening after sending audio to prevent continuous detection
          vad.stopListening();
        }, 100);
      }
    }
  });
  
  // Phase 4: Create combined state from specialized hooks (removing problematic sync effects)
  const state: VoiceState = {
    // Connection state
    connectionState: connection.state.state,
    isConnected: connection.state.state === 'connected',
    isConnecting: connection.state.state === 'connecting',
    
    // Recording state  
    recordingState: recording.state.state,
    isRecording: recording.state.state === 'recording',
    hasPermission: recording.state.hasPermission,
    isListening: vad.state.isListening,
    
    // Processing states
    isProcessing: conversation.state.isProcessing,
    
    // Playback state
    playbackState: playback.state.state,
    isPlaying: playback.state.state === 'playing',
    
    // VAD states
    vadActive: vad.state.isActive,
    vadEnergy: vad.state.energy,
    vadVolume: vad.state.volume,
    vadConfidence: vad.state.confidence,
    
    // Conversation states
    conversationStarted: conversation.state.conversationStarted,
    conversationCompleted: conversation.state.conversationCompleted,
    currentStep: conversation.state.currentStep,
    
    // Error handling (combined from specialized hooks)
    errors: [
      connection.state.error,
      recording.state.error,
      playback.state.error
    ].filter(Boolean) as VoiceError[],
    hasErrors: !!(connection.state.error || recording.state.error || playback.state.error),
    error: connection.state.error?.message || recording.state.error?.message || playback.state.error?.message || null,
    
    // Visitor information
    visitorInfo: conversation.state.visitorInfo,
    calendarResult: conversation.state.calendarResult,
  };
  
  // Start voice chat
  const startVoiceChat = useCallback(async (): Promise<boolean> => {
    try {
      setError(null);
      
      // Request microphone permission first
      const hasPermission = await recording.requestPermission();
      if (!hasPermission) {
        setError(createValidationError('Microphone permission is required for voice chat'));
        return false;
      }
      
      // Connect WebSocket
      const connected = await connection.connect();
      if (!connected) {
        setError(createConnectionError('Failed to connect to voice service'));
        return false;
      }
      
      // Update conversation state
      conversation.updateConversationState({ conversationStarted: true });
      
      console.log('✅ Voice chat started successfully');
      
      // Only start recording if not in greeting mode
      if (!isGreetingRef.current) {
        setTimeout(() => {
          console.log('🎤 Starting initial recording after connection');
          startRecording();
        }, 2000);
      } else {
        console.log('🎭 Greeting mode: recording disabled until greeting completes');
      }
      
      return true;
      
    } catch (error) {
      console.error('❌ Failed to start voice chat:', error);
      setError(createValidationError(error instanceof Error ? error.message : 'Failed to start voice chat'));
      return false;
    }
  }, [connection, recording, conversation, isGreetingRef]);
  
  // Stop voice chat
  const stopVoiceChat = useCallback(() => {
    // Force stop recording if active
    if (recording.state.state === 'recording') {
      recording.forceStopRecording();
    }
    
    // Stop VAD listening
    vad.stopListening();
    
    // Disconnect WebSocket
    connection.disconnect();
    
    // Reset conversation state
    conversation.updateConversationState({
      conversationStarted: false
    });
    
    console.log('🔇 Voice chat stopped');
  }, [recording, vad, connection, conversation]);
  
  // Start recording with VAD integration
  const startRecording = useCallback(async (): Promise<boolean> => {
    console.log(`🎤 startRecording called - isProcessing: ${conversation.state.isProcessing}, isPlaying: ${playback.state.state === 'playing'}`);
    
    // Don't start recording if playing audio
    if (playback.state.state === 'playing') {
      console.log(`⚠️ Cannot start recording - audio is playing`);
      return false;
    }
    
    // If processing is stuck, reset it for recording restart
    if (conversation.state.isProcessing) {
      console.log('⚠️ Processing state stuck, resetting for recording restart');
      conversation.updateConversationState({ isProcessing: false });
    }
    
    // Don't start recording if conversation is already completed
    if (conversation.state.conversationCompleted) {
      console.log('⚠️ Cannot start recording - conversation already completed');
      return false;
    }
    
    // Start VAD listening first
    const vadStarted = await vad.startListening();
    if (!vadStarted) {
      console.log('⚠️ Failed to start VAD listening');
      return false;
    }
    
    // Final check before starting recording
    if (conversation.state.isProcessing) {
      console.log('⚠️ Processing state still true, forcing reset');
      conversation.updateConversationState({ isProcessing: false });
    }
    
    // Start recording
    const started = await recording.startRecording();
    if (started) {
      console.log('🎤 Recording started with VAD integration');
      return true;
    }
    
    // If recording failed, stop VAD
    vad.stopListening();
    return false;
  }, [recording, vad, conversation.state.isProcessing, playback.state.state]);
  
  // Stop recording
  const stopRecording = useCallback(() => {
    // Set processing state immediately to prevent new recordings
    conversation.updateConversationState({ isProcessing: true });
    
    // Stop recording and send data
    recording.stopRecording();
    
    // Stop VAD
    vad.stopListening();
    
    console.log('🔇 Recording stopped and processing started');
  }, [recording, vad, conversation]);
  
  // Force stop recording
  const forceStopRecording = useCallback(() => {
    recording.forceStopRecording();
    vad.stopListening();
    console.log('🔇 Force stopped recording');
  }, [recording, vad]);
  
  // Play last response
  const playLastResponse = useCallback(() => {
    playback.playLastResponse();
  }, [playback]);
  
  // Reset error
  const resetError = useCallback(() => {
    setError(null);
  }, []);
  
  // Send text input
  const sendTextInput = useCallback((text: string) => {
    if (!connection.client?.isConnected()) {
      setError(createValidationError('Cannot send text: not connected'));
      return;
    }
    
    // Use conversation hook to add message and set processing
    conversation.sendTextInput(text, (trimmedText) => {
      // Send to WebSocket
      connection.client?.sendCommand('text_input', { text: trimmedText });
    });
  }, [connection.client, conversation]);
  
  // Phase 3: Use message handlers management hook
  useVoiceMessageHandlers({
    connection,
    recording,
    playback,
    conversation,
    vad,
    isGreetingRef,
    startRecording,
    setError
  });
  
  // Phase 3: Use auto-start management hook
  useVoiceAutoStart({
    autoStart: options.autoStart || false,
    startVoiceChat
  });
  
  return {
    state,
    messages: conversation.messages, // Use hook messages directly
    startVoiceChat,
    stopVoiceChat,
    startRecording,
    stopRecording,
    forceStopRecording,
    playLastResponse,
    resetError,
    sendTextInput,
    sessionId
  };
}