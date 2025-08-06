/**
 * Voice chat hook for managing voice conversation state
 * Integrates AudioRecorder, WebSocket, VAD, and AudioPlayer
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { 
  AudioRecorder, 
  AudioPlayer, 
  createAudioRecorder, 
  createAudioPlayer 
} from '@/lib/audio-recorder';
import { 
  VoiceWebSocketClient, 
  VoiceMessage as WSVoiceMessage, 
  createVoiceWebSocketClient 
} from '@/lib/websocket';
import { 
  ClientVoiceActivityDetector, 
  VADResult, 
  createClientVAD 
} from '@/lib/vad';

export interface ConversationMessage {
  speaker: 'visitor' | 'ai';
  content: string;
  timestamp: string;
  audioData?: string; // base64 for AI responses
}

export interface VoiceState {
  // Connection states
  isConnected: boolean;
  isConnecting: boolean;
  
  // Recording states
  isRecording: boolean;
  hasPermission: boolean;
  
  // Processing states
  isProcessing: boolean;
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
  
  // Error handling
  error: string | null;
  
  // Visitor information
  visitorInfo?: any;
  calendarResult?: any;
}

export interface UseVoiceChatOptions {
  sessionId?: string;
  autoStart?: boolean;
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
  
  // Core services
  const audioRecorder = useRef<AudioRecorder | null>(null);
  const audioPlayer = useRef<AudioPlayer | null>(null);
  const wsClient = useRef<VoiceWebSocketClient | null>(null);
  const vad = useRef<ClientVoiceActivityDetector | null>(null);
  
  // State management
  const [state, setState] = useState<VoiceState>({
    isConnected: false,
    isConnecting: false,
    isRecording: false,
    hasPermission: false,
    isProcessing: false,
    isPlaying: false,
    vadActive: false,
    vadEnergy: 0,
    vadVolume: 0,
    vadConfidence: 0,
    conversationStarted: false,
    conversationCompleted: false,
    currentStep: 'greeting',
    error: null
  });
  
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const lastAudioResponse = useRef<string | null>(null);
  
  // Update state helper
  const updateState = useCallback((updates: Partial<VoiceState>) => {
    setState(prev => ({ ...prev, ...updates }));
  }, []);
  
  // Add message helper
  const addMessage = useCallback((message: ConversationMessage) => {
    setMessages(prev => [...prev, message]);
  }, []);
  
  // Initialize services
  useEffect(() => {
    console.log(`🎙️ Initializing voice chat for session: ${sessionId}`);
    
    // Create audio services
    audioRecorder.current = createAudioRecorder({
      sampleRate: 16000,
      channels: 1,
      chunkSize: 100 // 100ms chunks
    });
    
    audioPlayer.current = createAudioPlayer();
    
    // Create WebSocket client
    wsClient.current = createVoiceWebSocketClient(sessionId);
    
    // Create VAD
    vad.current = createClientVAD({
      energyThreshold: options.vadConfig?.energyThreshold || 30,  // エネルギー閾値30
      silenceDuration: options.vadConfig?.silenceDuration || 1500,  // 無音継続1500ms
      minSpeechDuration: options.vadConfig?.minSpeechDuration || 100  // 最小発話時間を短縮
    });
    
    return () => {
      // Cleanup on unmount
      audioRecorder.current?.destroy();
      audioPlayer.current?.destroy();
      wsClient.current?.destroy();
      vad.current?.destroy();
    };
  }, [sessionId, options.vadConfig]);
  
  // Placeholder for WebSocket handlers - will be moved after function definitions
  
  // Setup audio recorder handlers
  useEffect(() => {
    if (!audioRecorder.current) return;
    
    // Disable chunk-by-chunk sending for now
    // We'll send the complete audio when recording stops
    audioRecorder.current.setChunkCallback(async (chunk) => {
      // Just log chunk info for debugging
      console.log(`📊 Audio chunk received: ${chunk.size} bytes`);
    });
    
    audioRecorder.current.setStateChangeCallback((recorderState) => {
      updateState({
        isRecording: recorderState.isRecording,
        hasPermission: recorderState.hasPermission,
        error: recorderState.errorMessage || null
      });
    });
    
  }, [updateState]);
  
  // Setup VAD handlers
  useEffect(() => {
    if (!vad.current) return;
    
    vad.current.addCallback((vadResult: VADResult) => {
      updateState({
        vadActive: vadResult.isActive,
        vadVolume: vadResult.volume,
        vadEnergy: vadResult.energy,
        vadConfidence: vadResult.confidence
      });
    });
    
  }, [updateState]);
  
  // Play audio from base64
  const playAudioFromBase64 = useCallback(async (base64Audio: string) => {
    if (!audioPlayer.current || !base64Audio) {
      console.log('🔊 Audio playback skipped: no player or audio data');
      return;
    }
    
    try {
      console.log('🔊 Starting audio playback...');
      updateState({ isPlaying: true });
      await audioPlayer.current.playAudioFromBase64(base64Audio);
      console.log('🔊 Audio playback completed successfully');
    } catch (error) {
      console.error('❌ Audio playback error:', error);
      updateState({ error: 'Audio playback failed' });
    } finally {
      console.log('🔊 Setting isPlaying to false');
      updateState({ isPlaying: false });
    }
  }, [updateState]);
  
  // Start voice chat
  const startVoiceChat = useCallback(async (): Promise<boolean> => {
    try {
      updateState({ isConnecting: true, error: null });
      
      // Request microphone permission
      if (audioRecorder.current) {
        const hasPermission = await audioRecorder.current.requestPermission();
        if (!hasPermission) {
          updateState({ 
            error: 'Microphone permission is required for voice chat',
            isConnecting: false
          });
          return false;
        }
      }
      
      // Connect WebSocket
      if (wsClient.current) {
        const connected = await wsClient.current.connect();
        if (!connected) {
          updateState({ 
            error: 'Failed to connect to voice service',
            isConnecting: false
          });
          return false;
        }
      }
      
      updateState({ 
        conversationStarted: true,
        isConnecting: false
      });
      
      console.log('✅ Voice chat started successfully');
      return true;
      
    } catch (error) {
      console.error('❌ Failed to start voice chat:', error);
      updateState({ 
        error: error instanceof Error ? error.message : 'Failed to start voice chat',
        isConnecting: false
      });
      return false;
    }
  }, [updateState]);
  
  // Stop voice chat
  const stopVoiceChat = useCallback(() => {
    // Stop recording
    if (audioRecorder.current && state.isRecording) {
      audioRecorder.current.stopRecording();
    }
    
    // Stop VAD
    if (vad.current) {
      vad.current.stop();
    }
    
    // Disconnect WebSocket
    if (wsClient.current) {
      wsClient.current.disconnect();
    }
    
    updateState({
      conversationStarted: false,
      isRecording: false,
      vadActive: false
    });
    
    console.log('🔇 Voice chat stopped');
  }, [state.isRecording, updateState]);
  
  // Start recording
  const startRecording = useCallback(async (): Promise<boolean> => {
    if (!audioRecorder.current || !wsClient.current?.isConnected()) {
      updateState({ error: 'Voice chat not ready' });
      return false;
    }
    
    try {
      // Initialize VAD with microphone stream
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: true 
      });
      
      if (vad.current) {
        await vad.current.initialize(stream);
        vad.current.start();
      }
      
      // Start recording
      const started = await audioRecorder.current.startRecording();
      if (started) {
        console.log('🎤 Recording started');
        return true;
      }
      
      updateState({ error: 'Failed to start recording' });
      return false;
      
    } catch (error) {
      console.error('❌ Failed to start recording:', error);
      updateState({ 
        error: error instanceof Error ? error.message : 'Failed to start recording'
      });
      return false;
    }
  }, [updateState]);
  
  // Stop recording
  const stopRecording = useCallback(() => {
    if (audioRecorder.current) {
      // Get the complete audio blob
      const audioBlob = audioRecorder.current.stopRecording();
      
      // Send the complete audio file if available
      if (audioBlob && wsClient.current?.isConnected()) {
        // Send complete audio file as end_speech command with data
        wsClient.current.sendCommand('end_speech_with_audio', {
          audio_size: audioBlob.size,
          mime_type: audioBlob.type
        });
        
        // Send the audio blob
        wsClient.current.sendAudioData(audioBlob);
      } else {
        // Fallback to simple end_speech command
        wsClient.current?.sendCommand('end_speech');
      }
    }
    
    if (vad.current) {
      vad.current.stop();
    }
    
    console.log('🔇 Recording stopped');
  }, []);
  
  // Play last response
  const playLastResponse = useCallback(() => {
    if (lastAudioResponse.current) {
      playAudioFromBase64(lastAudioResponse.current);
    }
  }, [playAudioFromBase64]);
  
  // Reset error
  const resetError = useCallback(() => {
    updateState({ error: null });
  }, [updateState]);
  
  // Send text input
  const sendTextInput = useCallback((text: string) => {
    if (!wsClient.current?.isConnected() || !text.trim()) {
      updateState({ error: 'Cannot send text: not connected or empty input' });
      return;
    }
    
    // Send text input command
    wsClient.current.sendCommand('text_input', { text: text.trim() });
    
    // Add visitor message
    addMessage({
      speaker: 'visitor',
      content: text.trim(),
      timestamp: new Date().toISOString()
    });
    
    // Set processing state
    updateState({ isProcessing: true });
  }, [updateState, addMessage]);
  
  // Setup WebSocket message handlers (moved after function definitions)
  useEffect(() => {
    if (!wsClient.current) return;
    
    const handleVoiceResponse = (message: WSVoiceMessage) => {
      console.log('📥 Received voice response:', message);
      
      // Add AI message
      addMessage({
        speaker: 'ai',
        content: message.text || '',
        timestamp: new Date().toISOString(),
        audioData: message.audio
      });
      
      // Store audio for playback
      if (message.audio) {
        lastAudioResponse.current = message.audio;
        
        // Auto-play response and update completion status after playback
        if (message.completed) {
          // If this is the final message, wait for audio to finish
          console.log('🎬 Starting final audio playback...');
          playAudioFromBase64(message.audio).then(() => {
            console.log('🎬 Final audio playback completed, setting conversationCompleted to true');
            // Update conversation state after audio finishes
            updateState({
              currentStep: message.step || 'unknown',
              visitorInfo: message.visitor_info,
              calendarResult: message.calendar_result,
              conversationCompleted: true,
              isProcessing: false
            });
          }).catch((error) => {
            console.error('❌ Error during final audio playback:', error);
            // Still set completion even if audio fails
            updateState({
              currentStep: message.step || 'unknown',
              visitorInfo: message.visitor_info,
              calendarResult: message.calendar_result,
              conversationCompleted: true,
              isProcessing: false
            });
          });
        } else {
          // For non-final messages, update state immediately
          updateState({
            currentStep: message.step || 'unknown',
            visitorInfo: message.visitor_info,
            calendarResult: message.calendar_result,
            conversationCompleted: false,
            isProcessing: false
          });
          playAudioFromBase64(message.audio);
        }
      } else {
        // No audio, update state immediately
        updateState({
          currentStep: message.step || 'unknown',
          visitorInfo: message.visitor_info,
          calendarResult: message.calendar_result,
          conversationCompleted: message.completed || false,
          isProcessing: false
        });
      }
    };
    
    const handleTranscription = (message: WSVoiceMessage) => {
      console.log('📝 Received transcription:', message);
      
      if (message.text) {
        // Add visitor message
        addMessage({
          speaker: 'visitor',
          content: message.text,
          timestamp: new Date().toISOString()
        });
      }
    };
    
    const handleVadStatus = (message: WSVoiceMessage) => {
      updateState({
        vadActive: message.is_speech || false,
        vadEnergy: message.energy_level || 0,
        vadConfidence: message.confidence || 0
      });
    };
    
    const handleProcessing = (_message: WSVoiceMessage) => {
      updateState({
        isProcessing: true
      });
    };
    
    const handleReady = (_message: WSVoiceMessage) => {
      updateState({
        isProcessing: false
      });
    };
    
    const handleError = (message: WSVoiceMessage) => {
      console.error('❌ WebSocket error:', message);
      updateState({
        error: message.error || message.message || 'Unknown error',
        isProcessing: false
      });
    };
    
    const handleConversationCompleted = (_message: WSVoiceMessage) => {
      console.log('✅ Conversation completed');
      updateState({
        conversationCompleted: true,
        isProcessing: false
      });
    };
    
    // WebSocket state change handler
    const handleStateChange = (wsState: any) => {
      updateState({
        isConnected: wsState.connected,
        isConnecting: wsState.connecting,
        error: wsState.error || null
      });
    };
    
    // Register handlers
    wsClient.current.addMessageHandler('voice_response', handleVoiceResponse);
    wsClient.current.addMessageHandler('transcription', handleTranscription);
    wsClient.current.addMessageHandler('vad_status', handleVadStatus);
    wsClient.current.addMessageHandler('processing', handleProcessing);
    wsClient.current.addMessageHandler('ready', handleReady);
    wsClient.current.addMessageHandler('error', handleError);
    wsClient.current.addMessageHandler('conversation_completed', handleConversationCompleted);
    wsClient.current.addStateChangeHandler(handleStateChange);
    
    // Cleanup function to remove handlers
    return () => {
      if (wsClient.current) {
        wsClient.current.removeMessageHandler('voice_response', handleVoiceResponse);
        wsClient.current.removeMessageHandler('transcription', handleTranscription);
        wsClient.current.removeMessageHandler('vad_status', handleVadStatus);
        wsClient.current.removeMessageHandler('processing', handleProcessing);
        wsClient.current.removeMessageHandler('ready', handleReady);
        wsClient.current.removeMessageHandler('error', handleError);
        wsClient.current.removeMessageHandler('conversation_completed', handleConversationCompleted);
        wsClient.current.removeStateChangeHandler(handleStateChange);
      }
    };
  }, [addMessage, updateState, playAudioFromBase64]);
  
  // Auto-start if requested
  useEffect(() => {
    if (options.autoStart) {
      startVoiceChat();
    }
  }, [options.autoStart, startVoiceChat]);
  
  return {
    state,
    messages,
    startVoiceChat,
    stopVoiceChat,
    startRecording,
    stopRecording,
    playLastResponse,
    resetError,
    sendTextInput,
    sessionId
  };
}