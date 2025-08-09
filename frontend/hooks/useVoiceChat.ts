/**
 * Refactored Voice chat hook - Main integration hook
 * Combines specialized hooks for connection, recording, playback, conversation, and VAD
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { VoiceMessage as WSVoiceMessage } from '@/lib/websocket';
import { 
  VoiceError, 
  createConnectionError, 
  createValidationError,
  ConnectionState,
  RecordingState,
  PlaybackState
} from '@/types/voice';

// Import specialized hooks
import { useVoiceConnection } from './useVoiceConnection';
import { useVoiceRecording } from './useVoiceRecording';
import { useVoicePlayback } from './useVoicePlayback';
import { useConversationFlow, ConversationMessage } from './useConversationFlow';
import { useVADIntegration } from './useVADIntegration';

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
  
  // Greeting mode ref for dynamic updates
  const isGreetingRef = useRef(options.isGreeting || false);
  
  // Error state (not managed by sub-hooks)
  const [error, setError] = useState<VoiceError | null>(null);
  
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
  
  // Combine all states into unified VoiceState
  const allErrors: VoiceError[] = [
    error,
    connection.state.error,
    recording.state.error,
    playback.state.error
  ].filter((err): err is VoiceError => err !== null);
  
  const state: VoiceState = {
    // Connection states
    connectionState: connection.state.state,
    isConnected: connection.state.state === 'connected',
    isConnecting: connection.state.state === 'connecting',
    
    // Recording states
    recordingState: recording.state.state,
    isRecording: recording.state.state === 'recording',
    hasPermission: recording.state.hasPermission,
    isListening: vad.state.isListening,
    
    // Processing state
    isProcessing: conversation.state.isProcessing,
    
    // Playback states
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
    
    // Error handling (typed and backward compatible)
    errors: allErrors,
    hasErrors: allErrors.length > 0,
    error: allErrors.length > 0 ? allErrors[0].message : null,
    
    // Business data
    visitorInfo: conversation.state.visitorInfo,
    calendarResult: conversation.state.calendarResult
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
  
  // Setup WebSocket message handlers
  useEffect(() => {
    if (!connection.client) return;
    
    const handleVoiceResponse = async (message: WSVoiceMessage) => {
      console.log('📥 Received voice response:', message);
      
      // Add AI message
      conversation.addMessage({
        speaker: 'ai',
        content: message.text || '',
        timestamp: new Date().toISOString(),
        audioData: message.audio
      });
      
      // Update conversation state - ensure processing is false
      conversation.updateConversationState({
        currentStep: message.step || 'unknown',
        visitorInfo: message.visitor_info,
        calendarResult: message.calendar_result,
        conversationCompleted: message.completed || false,
        isProcessing: false
      });
      
      console.log('📥 AI response processed, isProcessing set to false');
      
      // Handle audio playback
      if (message.audio) {
        try {
          await playback.playAudioFromBase64(message.audio);
          
          // After playback, start recording if not completed and not in greeting mode
          if (!message.completed && !isGreetingRef.current) {
            console.log('🎤 Starting recording after AI response');
            // Add small delay to ensure playback state is fully updated
            setTimeout(() => {
              startRecording();
            }, 200);
          } else if (message.completed) {
            console.log('🎬 Conversation completed after final audio playback');
            // Stop all recording and VAD when conversation is completed
            if (recording.state.state === 'recording') {
              recording.forceStopRecording();
            }
            vad.stopListening();
          } else if (isGreetingRef.current) {
            console.log('🎭 Greeting mode: skipping auto-recording after AI response');
          }
        } catch (error) {
          console.error('❌ Audio playback error:', error);
        }
      } else {
        // No audio, start recording if not completed and not in greeting mode
        if (!message.completed && !isGreetingRef.current) {
          console.log('🎤 Starting recording (no audio response)');
          // Add small delay to ensure state is fully updated
          setTimeout(() => {
            startRecording();
          }, 200);
        }
      }
    };
    
    const handleTranscription = (message: WSVoiceMessage) => {
      console.log('📝 Received transcription:', message);
      
      if (message.text) {
        conversation.addMessage({
          speaker: 'visitor',
          content: message.text,
          timestamp: new Date().toISOString()
        });
      }
    };
    
    const handleVadStatus = (message: WSVoiceMessage) => {
      // Server-side VAD status (currently using client-side VAD)
      console.log('📊 Server VAD status:', message);
    };
    
    const handleProcessing = (_message: WSVoiceMessage) => {
      conversation.updateConversationState({ isProcessing: true });
    };
    
    const handleReady = (_message: WSVoiceMessage) => {
      conversation.updateConversationState({ isProcessing: false });
    };
    
    const handleError = (message: WSVoiceMessage) => {
      console.error('❌ WebSocket error:', message);
      setError(createValidationError(message.error || message.message || 'Unknown error'));
      conversation.updateConversationState({ isProcessing: false });
    };
    
    const handleConversationCompleted = (_message: WSVoiceMessage) => {
      console.log('✅ Conversation completed');
      conversation.updateConversationState({
        conversationCompleted: true,
        isProcessing: false
      });
      
      // Stop all recording and VAD when conversation is completed
      if (recording.state.state === 'recording') {
        recording.forceStopRecording();
      }
      vad.stopListening();
      console.log('🔇 Stopped recording and VAD after conversation completion');
    };
    
    // Register handlers
    connection.addMessageHandler('voice_response', handleVoiceResponse);
    connection.addMessageHandler('transcription', handleTranscription);
    connection.addMessageHandler('vad_status', handleVadStatus);
    connection.addMessageHandler('processing', handleProcessing);
    connection.addMessageHandler('ready', handleReady);
    connection.addMessageHandler('error', handleError);
    connection.addMessageHandler('conversation_completed', handleConversationCompleted);
    
    return () => {
      // Cleanup handlers
      connection.removeMessageHandler('voice_response', handleVoiceResponse);
      connection.removeMessageHandler('transcription', handleTranscription);
      connection.removeMessageHandler('vad_status', handleVadStatus);
      connection.removeMessageHandler('processing', handleProcessing);
      connection.removeMessageHandler('ready', handleReady);
      connection.removeMessageHandler('error', handleError);
      connection.removeMessageHandler('conversation_completed', handleConversationCompleted);
    };
  }, [connection, conversation, playback, startRecording]);
  
  // Update greeting ref when option changes
  useEffect(() => {
    isGreetingRef.current = options.isGreeting || false;
  }, [options.isGreeting]);
  
  // Auto-start if requested
  useEffect(() => {
    if (options.autoStart) {
      startVoiceChat();
    }
  }, [options.autoStart, startVoiceChat]);
  
  return {
    state,
    messages: conversation.messages,
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