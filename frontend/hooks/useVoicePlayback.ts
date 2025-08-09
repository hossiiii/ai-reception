/**
 * Voice playback management hook
 * Handles audio playback from base64 data and playback state management
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { 
  AudioPlayer, 
  createAudioPlayer 
} from '@/lib/audio-recorder';
import { 
  PlaybackStateInfo, 
  createAudioError 
} from '@/types/voice';

export interface UseVoicePlaybackReturn {
  // State
  state: PlaybackStateInfo;
  
  // Actions
  playAudioFromBase64: (base64Audio: string) => Promise<void>;
  playLastResponse: () => void;
  stopPlayback: () => void;
  
  // Utility
  isReady: boolean;
  hasLastAudio: boolean;
}

export function useVoicePlayback(): UseVoicePlaybackReturn {
  // Audio player instance
  const audioPlayer = useRef<AudioPlayer | null>(null);
  const lastAudioResponse = useRef<string | null>(null);
  
  // Playback state
  const [state, setState] = useState<PlaybackStateInfo>({
    state: 'idle',
    error: null,
    queue: []
  });
  
  // Update state helper
  const updateState = useCallback((updates: Partial<PlaybackStateInfo>) => {
    setState(prev => ({ ...prev, ...updates }));
  }, []);
  
  // Initialize audio player
  useEffect(() => {
    console.log('🔊 Initializing audio player');
    
    // Create audio player
    audioPlayer.current = createAudioPlayer();
    
    return () => {
      // Cleanup on unmount
      if (audioPlayer.current) {
        audioPlayer.current.destroy();
        audioPlayer.current = null;
      }
    };
  }, []);
  
  // Play audio from base64 data
  const playAudioFromBase64 = useCallback(async (base64Audio: string): Promise<void> => {
    if (!audioPlayer.current || !base64Audio) {
      console.log('🔊 Audio playback skipped: no player or audio data');
      const error = createAudioError('No audio player or data available', 'PLAYBACK_FAILED');
      updateState({ error });
      return;
    }
    
    // Store last audio for replay
    lastAudioResponse.current = base64Audio;
    
    try {
      console.log('🔊 Starting audio playback...');
      updateState({ state: 'playing', error: null });
      
      await audioPlayer.current.playAudioFromBase64(base64Audio);
      
      console.log('🔊 Audio playback completed successfully');
    } catch (error) {
      console.error('❌ Audio playback error:', error);
      const voiceError = createAudioError(
        error instanceof Error ? error.message : 'Audio playback failed',
        'PLAYBACK_FAILED'
      );
      updateState({ error: voiceError });
      throw error; // Re-throw to allow caller to handle
    } finally {
      console.log('🔊 Setting playback to idle');
      updateState({ state: 'idle' });
    }
  }, [updateState]);
  
  // Play last response
  const playLastResponse = useCallback(() => {
    if (lastAudioResponse.current) {
      console.log('🔊 Replaying last audio response');
      playAudioFromBase64(lastAudioResponse.current);
    } else {
      console.log('⚠️ No last audio response available');
      const error = createAudioError('No last audio response available', 'PLAYBACK_FAILED');
      updateState({ error });
    }
  }, [playAudioFromBase64, updateState]);
  
  // Stop playback (if supported by audio player)
  const stopPlayback = useCallback(() => {
    if (audioPlayer.current && state.state === 'playing') {
      // AudioPlayer doesn't currently expose a stop method
      // but we can update our state
      updateState({ state: 'idle' });
      console.log('🔊 Audio playback stopped');
    }
  }, [state.state, updateState]);
  
  // Check if ready for playback
  const isReady = Boolean(audioPlayer.current);
  
  // Check if has last audio
  const hasLastAudio = Boolean(lastAudioResponse.current);
  
  return {
    state,
    playAudioFromBase64,
    playLastResponse,
    stopPlayback,
    isReady,
    hasLastAudio
  };
}