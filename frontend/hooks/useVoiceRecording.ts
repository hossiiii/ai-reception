/**
 * Voice recording management hook
 * Handles audio recording, permissions, and integration with WebSocket
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { 
  AudioRecorder, 
  createAudioRecorder 
} from '@/lib/audio-recorder';
import { VoiceWebSocketClient } from '@/lib/websocket';
import { 
  RecordingState,
  RecordingStateInfo, 
  createAudioError,
  createPermissionError
} from '@/types/voice';

export interface UseVoiceRecordingOptions {
  sampleRate?: number;
  channels?: number;
  chunkSize?: number;
}

export interface UseVoiceRecordingReturn {
  // State
  state: RecordingStateInfo;
  
  // Actions
  requestPermission: () => Promise<boolean>;
  startRecording: () => Promise<boolean>;
  stopRecording: () => Blob | null;
  forceStopRecording: () => void;
  
  // Utility
  isReady: boolean;
}

export function useVoiceRecording(
  wsClient: VoiceWebSocketClient | null,
  options: UseVoiceRecordingOptions = {}
): UseVoiceRecordingReturn {
  const {
    sampleRate = 16000,
    channels = 1,
    chunkSize = 100
  } = options;
  
  // Audio recorder instance
  const audioRecorder = useRef<AudioRecorder | null>(null);
  
  // Recording state
  const [state, setState] = useState<RecordingStateInfo>({
    state: 'idle',
    hasPermission: false,
    isListening: false,
    error: null,
    config: {
      sampleRate,
      channels,
      chunkSize
    }
  });
  
  // Update state helper
  const updateState = useCallback((updates: Partial<RecordingStateInfo>) => {
    setState(prev => ({ ...prev, ...updates }));
  }, []);
  
  // Initialize audio recorder
  useEffect(() => {
    console.log('🎤 Initializing audio recorder');
    
    // Create audio recorder
    audioRecorder.current = createAudioRecorder({
      sampleRate,
      channels,
      chunkSize
    });
    
    // Setup chunk callback (optional for debugging)
    audioRecorder.current.setChunkCallback(async (chunk) => {
      console.log(`📊 Audio chunk received: ${chunk.size} bytes`);
    });
    
    // Setup state change callback
    audioRecorder.current.setStateChangeCallback((recorderState) => {
      let newState: RecordingState = 'idle';
      if (recorderState.isRecording) {
        newState = 'recording';
      }
      // Note: AudioRecorderState doesn't have isProcessing, 
      // processing state is managed by conversation layer
      
      const error = recorderState.errorMessage 
        ? createAudioError(recorderState.errorMessage, 'RECORDING_FAILED')
        : null;
      
      updateState({
        state: newState,
        hasPermission: recorderState.hasPermission,
        isListening: recorderState.isRecording,
        error
      });
    });
    
    return () => {
      // Cleanup on unmount
      if (audioRecorder.current) {
        audioRecorder.current.destroy();
        audioRecorder.current = null;
      }
    };
  }, [sampleRate, channels, chunkSize, updateState]);
  
  // Request microphone permission
  const requestPermission = useCallback(async (): Promise<boolean> => {
    if (!audioRecorder.current) {
      const error = createAudioError('Audio recorder not initialized', 'RECORDING_FAILED');
      updateState({ error });
      return false;
    }
    
    try {
      const hasPermission = await audioRecorder.current.requestPermission();
      if (!hasPermission) {
        const error = createPermissionError('Microphone permission denied', 'MICROPHONE_DENIED');
        updateState({ error });
        return false;
      }
      
      console.log('✅ Microphone permission granted');
      return true;
    } catch (error) {
      console.error('❌ Failed to request microphone permission:', error);
      const voiceError = createPermissionError(
        error instanceof Error ? error.message : 'Failed to request microphone permission',
        'AUDIO_CONTEXT_FAILED'
      );
      updateState({ error: voiceError });
      return false;
    }
  }, [updateState]);
  
  // Start recording
  const startRecording = useCallback(async (): Promise<boolean> => {
    if (!audioRecorder.current) {
      const error = createAudioError('Audio recorder not initialized', 'RECORDING_FAILED');
      updateState({ error });
      return false;
    }
    
    if (!wsClient?.isConnected()) {
      const error = createAudioError('WebSocket not connected', 'RECORDING_FAILED');
      updateState({ error });
      return false;
    }
    
    // Don't start if already recording
    if (state.state === 'recording') {
      console.log('⚠️ Already recording, skipping start');
      return true;
    }
    
    // Ensure permission is granted
    if (!state.hasPermission) {
      const hasPermission = await requestPermission();
      if (!hasPermission) {
        return false;
      }
    }
    
    try {
      const started = await audioRecorder.current.startRecording();
      if (started) {
        console.log('🎤 Recording started');
        return true;
      } else {
        const error = createAudioError('Failed to start recording', 'RECORDING_FAILED');
        updateState({ error });
        return false;
      }
    } catch (error) {
      console.error('❌ Failed to start recording:', error);
      const voiceError = createAudioError(
        error instanceof Error ? error.message : 'Failed to start recording',
        'RECORDING_FAILED'
      );
      updateState({ error: voiceError });
      return false;
    }
  }, [state.state, state.hasPermission, wsClient, requestPermission, updateState]);
  
  // Stop recording and send to WebSocket
  const stopRecording = useCallback((): Blob | null => {
    if (!audioRecorder.current) {
      console.log('⚠️ Audio recorder not available for stopping');
      return null;
    }
    
    if (!wsClient?.isConnected()) {
      console.log('⚠️ WebSocket not connected, cannot send audio');
      return null;
    }
    
    // Get the complete audio blob
    const audioBlob = audioRecorder.current.stopRecording();
    
    if (audioBlob) {
      console.log(`🔇 Audio blob details: size=${audioBlob.size}, type=${audioBlob.type}`);
      
      // Send complete audio file as end_speech command with data
      wsClient.sendCommand('end_speech_with_audio', {
        audio_size: audioBlob.size,
        mime_type: audioBlob.type
      });
      
      // Send the audio blob
      wsClient.sendAudioData(audioBlob);
      
      console.log(`🔇 Recording stopped and sent to server (${audioBlob.size} bytes)`);
    } else {
      // Fallback to simple end_speech command
      wsClient.sendCommand('end_speech');
      console.log('🔇 Recording stopped with simple end_speech command');
    }
    
    return audioBlob;
  }, [wsClient]);
  
  // Force stop recording without sending data
  const forceStopRecording = useCallback(() => {
    if (audioRecorder.current) {
      audioRecorder.current.forceStopRecording();
      console.log('🔇 Force stopped recording');
    }
  }, []);
  
  // Check if ready for recording
  const isReady = Boolean(
    audioRecorder.current && 
    wsClient?.isConnected() && 
    state.hasPermission
  );
  
  return {
    state,
    requestPermission,
    startRecording,
    stopRecording,
    forceStopRecording,
    isReady
  };
}