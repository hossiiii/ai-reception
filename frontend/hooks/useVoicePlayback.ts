/**
 * Voice playback management hook
 * Handles audio playback from base64 data and playback state management
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { 
  AudioPlayer, 
  createAudioPlayer 
} from '@/lib/audio-recorder';

export interface PlaybackState {
  isPlaying: boolean;
  error: string | null;
}

export interface UseVoicePlaybackReturn {
  // State
  state: PlaybackState;
  
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
  const [state, setState] = useState<PlaybackState>({
    isPlaying: false,
    error: null
  });
  
  // Update state helper
  const updateState = useCallback((updates: Partial<PlaybackState>) => {
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
      updateState({ error: 'No audio player or data available' });
      return;
    }
    
    // Store last audio for replay
    lastAudioResponse.current = base64Audio;
    
    try {
      console.log('🔊 Starting audio playback...');
      updateState({ isPlaying: true, error: null });
      
      await audioPlayer.current.playAudioFromBase64(base64Audio);
      
      console.log('🔊 Audio playback completed successfully');
    } catch (error) {
      console.error('❌ Audio playback error:', error);
      updateState({ 
        error: error instanceof Error ? error.message : 'Audio playback failed'
      });
      throw error; // Re-throw to allow caller to handle
    } finally {
      console.log('🔊 Setting isPlaying to false');
      updateState({ isPlaying: false });
    }
  }, [updateState]);
  
  // Play last response
  const playLastResponse = useCallback(() => {
    if (lastAudioResponse.current) {
      console.log('🔊 Replaying last audio response');
      playAudioFromBase64(lastAudioResponse.current);
    } else {
      console.log('⚠️ No last audio response available');
      updateState({ error: 'No last audio response available' });
    }
  }, [playAudioFromBase64, updateState]);
  
  // Stop playback (if supported by audio player)
  const stopPlayback = useCallback(() => {
    if (audioPlayer.current && state.isPlaying) {
      // AudioPlayer doesn't currently expose a stop method
      // but we can update our state
      updateState({ isPlaying: false });
      console.log('🔊 Audio playback stopped');
    }
  }, [state.isPlaying, updateState]);
  
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