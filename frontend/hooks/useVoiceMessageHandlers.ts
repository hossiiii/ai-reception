/**
 * Phase 3: WebSocketメッセージハンドラー管理フック
 * 複雑なuseEffectを単一責務に分割し、依存関係を最小化
 */

import { useEffect, useCallback } from 'react';
import { VoiceMessage as WSVoiceMessage } from '@/lib/websocket';
import { createValidationError } from '@/types/voice';
import type { UseVoiceConnectionReturn } from './useVoiceConnection';
import type { UseVoiceRecordingReturn } from './useVoiceRecording';
import type { UseVoicePlaybackReturn } from './useVoicePlayback';
import type { UseConversationFlowReturn } from './useConversationFlow';
import type { UseVADIntegrationReturn } from './useVADIntegration';

export interface UseVoiceMessageHandlersOptions {
  connection: UseVoiceConnectionReturn;
  recording: UseVoiceRecordingReturn;
  playback: UseVoicePlaybackReturn;
  conversation: UseConversationFlowReturn;
  vad: UseVADIntegrationReturn;
  isGreetingRef: React.MutableRefObject<boolean>;
  startRecording: () => Promise<boolean>;
  setError: (error: any) => void;
}

export interface UseVoiceMessageHandlersReturn {
  // No external interface needed - manages handlers internally
}

export function useVoiceMessageHandlers(options: UseVoiceMessageHandlersOptions): UseVoiceMessageHandlersReturn {
  const {
    connection,
    recording,
    playback,
    conversation,
    vad,
    isGreetingRef,
    startRecording,
    setError
  } = options;

  // Create stable handler functions
  const handleVoiceResponse = useCallback(async (message: WSVoiceMessage) => {
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
  }, [
    conversation,
    playback,
    isGreetingRef,
    startRecording,
    recording,
    vad
  ]);

  const handleTranscription = useCallback((message: WSVoiceMessage) => {
    console.log('📝 Received transcription:', message);
    
    if (message.text) {
      conversation.addMessage({
        speaker: 'visitor',
        content: message.text,
        timestamp: new Date().toISOString()
      });
    }
  }, [conversation]);

  const handleVadStatus = useCallback((message: WSVoiceMessage) => {
    // Server-side VAD status (currently using client-side VAD)
    console.log('📊 Server VAD status:', message);
  }, []);

  const handleProcessing = useCallback((_message: WSVoiceMessage) => {
    conversation.updateConversationState({ isProcessing: true });
  }, [conversation]);

  const handleReady = useCallback((_message: WSVoiceMessage) => {
    conversation.updateConversationState({ isProcessing: false });
  }, [conversation]);

  const handleError = useCallback((message: WSVoiceMessage) => {
    console.error('❌ WebSocket error:', message);
    setError(createValidationError(message.error || message.message || 'Unknown error'));
    conversation.updateConversationState({ isProcessing: false });
  }, [setError, conversation]);

  const handleConversationCompleted = useCallback((_message: WSVoiceMessage) => {
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
  }, [conversation, recording, vad]);

  // Register handlers when connection is available
  useEffect(() => {
    if (!connection.client) return;

    console.log('🔗 Registering WebSocket message handlers');
    
    // Register all handlers
    connection.addMessageHandler('voice_response', handleVoiceResponse);
    connection.addMessageHandler('transcription', handleTranscription);
    connection.addMessageHandler('vad_status', handleVadStatus);
    connection.addMessageHandler('processing', handleProcessing);
    connection.addMessageHandler('ready', handleReady);
    connection.addMessageHandler('error', handleError);
    connection.addMessageHandler('conversation_completed', handleConversationCompleted);
    
    return () => {
      console.log('🧹 Cleaning up WebSocket message handlers');
      
      // Cleanup all handlers
      connection.removeMessageHandler('voice_response', handleVoiceResponse);
      connection.removeMessageHandler('transcription', handleTranscription);
      connection.removeMessageHandler('vad_status', handleVadStatus);
      connection.removeMessageHandler('processing', handleProcessing);
      connection.removeMessageHandler('ready', handleReady);
      connection.removeMessageHandler('error', handleError);
      connection.removeMessageHandler('conversation_completed', handleConversationCompleted);
    };
  }, [
    connection,
    handleVoiceResponse,
    handleTranscription,
    handleVadStatus,
    handleProcessing,
    handleReady,
    handleError,
    handleConversationCompleted
  ]);

  return {};
}