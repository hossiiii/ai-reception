/**
 * Phase 2: Type safety enhancement for voice chat system
 * Defines strict union types to prevent invalid state combinations
 */

// Base state enums as string literals for better type safety
export type ConversationPhase = 'idle' | 'greeting' | 'active' | 'completed';
export type InputMode = 'voice' | 'text';
export type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'error';
export type RecordingState = 'idle' | 'recording' | 'processing';
export type PlaybackState = 'idle' | 'playing';
export type VADState = 'inactive' | 'listening' | 'speech_detected';

// Error type discrimination for better error handling
export type VoiceError = 
  | { type: 'connection'; message: string; code?: 'WEBSOCKET_FAILED' | 'TIMEOUT' | 'NETWORK_ERROR' }
  | { type: 'permission'; message: string; code?: 'MICROPHONE_DENIED' | 'AUDIO_CONTEXT_FAILED' }
  | { type: 'audio'; message: string; code?: 'PLAYBACK_FAILED' | 'RECORDING_FAILED' | 'CODEC_ERROR' }
  | { type: 'processing'; message: string; code?: 'TRANSCRIPTION_FAILED' | 'AI_ERROR' | 'TIMEOUT' }
  | { type: 'validation'; message: string; code?: 'INVALID_STATE' | 'MISSING_DATA' };

// Valid state combinations to prevent impossible states
export type ValidVoiceState = 
  // Idle state - nothing happening
  | {
      phase: 'idle';
      connection: 'disconnected';
      recording: 'idle';
      playback: 'idle';
      vad: 'inactive';
      inputMode?: never; // No input mode when idle
    }
  // Greeting phase - connected but limited functionality
  | {
      phase: 'greeting';
      connection: 'connected';
      recording: 'idle'; // No recording during greeting
      playback: 'idle' | 'playing'; // Can play greeting audio
      vad: 'inactive';
      inputMode?: never; // No input during greeting
    }
  // Active conversation - full functionality
  | {
      phase: 'active';
      connection: 'connected';
      recording: 'idle' | 'recording' | 'processing';
      playback: 'idle' | 'playing';
      vad: 'inactive' | 'listening' | 'speech_detected';
      inputMode: InputMode;
    }
  // Completed conversation - read-only state
  | {
      phase: 'completed';
      connection: 'connected' | 'disconnected';
      recording: 'idle'; // No more recording
      playback: 'idle' | 'playing'; // Can replay responses
      vad: 'inactive';
      inputMode?: never; // No more input
    }
  // Error states can occur in any phase
  | {
      phase: ConversationPhase;
      connection: 'error';
      recording: RecordingState;
      playback: PlaybackState;
      vad: VADState;
      inputMode?: InputMode;
    };

// Connection-specific state types
export interface ConnectionStateInfo {
  state: ConnectionState;
  error: VoiceError | null;
  sessionId: string;
  isReconnecting?: boolean;
  reconnectAttempts?: number;
}

// Recording-specific state types
export interface RecordingStateInfo {
  state: RecordingState;
  hasPermission: boolean;
  isListening: boolean;
  error: VoiceError | null;
  config?: {
    sampleRate: number;
    channels: number;
    chunkSize: number;
  };
}

// Playback-specific state types
export interface PlaybackStateInfo {
  state: PlaybackState;
  currentAudioId?: string;
  error: VoiceError | null;
  queue: string[];
}

// VAD-specific state types
export interface VADStateInfo {
  state: VADState;
  energy: number;
  volume: number;
  confidence: number;
  isActive: boolean;
  config?: {
    energyThreshold: number;
    silenceDuration: number;
    minSpeechDuration: number;
  };
}

// Conversation-specific state types
export interface ConversationStateInfo {
  phase: ConversationPhase;
  currentStep: string;
  isProcessing: boolean;
  conversationStarted: boolean;
  conversationCompleted: boolean;
  visitorInfo?: any;
  calendarResult?: any;
  error: VoiceError | null;
}

// Combined state interface that enforces valid combinations
export interface TypeSafeVoiceState {
  // Core state combination
  phase: ConversationPhase;
  connection: ConnectionState;
  recording: RecordingState;
  playback: PlaybackState;
  vad: VADState;
  inputMode?: InputMode;
  
  // Additional computed properties
  canRecord: boolean;
  canPlayAudio: boolean;
  canAcceptInput: boolean;
  
  // Error aggregation
  errors: VoiceError[];
  hasErrors: boolean;
  
  // Metadata
  sessionId: string;
  timestamp: string;
}

// Type guards for state validation
export function isValidVoiceState(state: any): state is ValidVoiceState {
  if (!state || typeof state !== 'object') return false;
  
  const { phase, connection, recording, playback, vad, inputMode } = state;
  
  // Check required properties exist
  if (!phase || !connection || !recording || !playback || !vad) {
    return false;
  }
  
  // Validate enum values
  const validPhases: ConversationPhase[] = ['idle', 'greeting', 'active', 'completed'];
  const validConnections: ConnectionState[] = ['disconnected', 'connecting', 'connected', 'error'];
  const validRecordings: RecordingState[] = ['idle', 'recording', 'processing'];
  const validPlaybacks: PlaybackState[] = ['idle', 'playing'];
  const validVADs: VADState[] = ['inactive', 'listening', 'speech_detected'];
  const validInputModes: InputMode[] = ['voice', 'text'];
  
  if (!validPhases.includes(phase)) return false;
  if (!validConnections.includes(connection)) return false;
  if (!validRecordings.includes(recording)) return false;
  if (!validPlaybacks.includes(playback)) return false;
  if (!validVADs.includes(vad)) return false;
  if (inputMode && !validInputModes.includes(inputMode)) return false;
  
  // Validate state combinations
  switch (phase) {
    case 'idle':
      return connection === 'disconnected' && 
             recording === 'idle' && 
             playback === 'idle' && 
             vad === 'inactive' && 
             !inputMode;
             
    case 'greeting':
      return connection === 'connected' && 
             recording === 'idle' && 
             vad === 'inactive' && 
             !inputMode;
             
    case 'active':
      return connection === 'connected' && 
             validInputModes.includes(inputMode as InputMode);
             
    case 'completed':
      return recording === 'idle' && 
             vad === 'inactive' && 
             !inputMode;
             
    default:
      return false;
  }
}

export function isConnectionError(error: VoiceError): error is VoiceError & { type: 'connection' } {
  return error.type === 'connection';
}

export function isPermissionError(error: VoiceError): error is VoiceError & { type: 'permission' } {
  return error.type === 'permission';
}

export function isAudioError(error: VoiceError): error is VoiceError & { type: 'audio' } {
  return error.type === 'audio';
}

export function isProcessingError(error: VoiceError): error is VoiceError & { type: 'processing' } {
  return error.type === 'processing';
}

export function isValidationError(error: VoiceError): error is VoiceError & { type: 'validation' } {
  return error.type === 'validation';
}

// Helper functions to create type-safe errors
export const createConnectionError = (message: string, code?: 'WEBSOCKET_FAILED' | 'TIMEOUT' | 'NETWORK_ERROR'): VoiceError => ({
  type: 'connection',
  message,
  code
});

export const createPermissionError = (message: string, code?: 'MICROPHONE_DENIED' | 'AUDIO_CONTEXT_FAILED'): VoiceError => ({
  type: 'permission',
  message,
  code
});

export const createAudioError = (message: string, code?: 'PLAYBACK_FAILED' | 'RECORDING_FAILED' | 'CODEC_ERROR'): VoiceError => ({
  type: 'audio',
  message,
  code
});

export const createProcessingError = (message: string, code?: 'TRANSCRIPTION_FAILED' | 'AI_ERROR' | 'TIMEOUT'): VoiceError => ({
  type: 'processing',
  message,
  code
});

export const createValidationError = (message: string, code?: 'INVALID_STATE' | 'MISSING_DATA'): VoiceError => ({
  type: 'validation',
  message,
  code
});