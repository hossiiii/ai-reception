/**
 * Voice Activity Detection (VAD) integration hook
 * Handles client-side VAD for automatic recording start/stop
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { 
  ClientVoiceActivityDetector, 
  VADResult, 
  createClientVAD 
} from '@/lib/vad';

export interface VADState {
  isActive: boolean;
  energy: number;
  volume: number;
  confidence: number;
  isListening: boolean;
}

export interface VADConfig {
  energyThreshold?: number;
  silenceDuration?: number;
  minSpeechDuration?: number;
}

export interface UseVADIntegrationOptions {
  vadConfig?: VADConfig;
  onSpeechStart?: () => void;
  onSpeechEnd?: () => void;
}

export interface UseVADIntegrationReturn {
  // State
  state: VADState;
  
  // Actions
  startListening: () => Promise<boolean>;
  stopListening: () => void;
  updateThresholds: (config: Partial<VADConfig>) => void;
  
  // Utility
  isReady: boolean;
}

const defaultConfig: Required<VADConfig> = {
  energyThreshold: 30,
  silenceDuration: 1500,
  minSpeechDuration: 100
};

export function useVADIntegration(options: UseVADIntegrationOptions = {}): UseVADIntegrationReturn {
  const { vadConfig = {}, onSpeechStart, onSpeechEnd } = options;
  
  // Merge with default config
  const config = { ...defaultConfig, ...vadConfig };
  
  // VAD instance and stream
  const vad = useRef<ClientVoiceActivityDetector | null>(null);
  const currentStream = useRef<MediaStream | null>(null);
  
  // VAD state
  const [state, setState] = useState<VADState>({
    isActive: false,
    energy: 0,
    volume: 0,
    confidence: 0,
    isListening: false
  });
  
  // Track previous active state for transitions
  const previousActive = useRef<boolean>(false);
  
  // Update state helper
  const updateState = useCallback((updates: Partial<VADState>) => {
    setState(prev => ({ ...prev, ...updates }));
  }, []);
  
  // Initialize VAD
  useEffect(() => {
    console.log('👂 Initializing VAD with config:', config);
    
    // Create VAD instance
    vad.current = createClientVAD(config);
    
    return () => {
      // Cleanup on unmount
      if (vad.current) {
        vad.current.destroy();
        vad.current = null;
      }
      
      // Stop media stream tracks
      if (currentStream.current) {
        currentStream.current.getTracks().forEach(track => track.stop());
        currentStream.current = null;
      }
    };
  }, [config.energyThreshold, config.silenceDuration, config.minSpeechDuration]);
  
  // Setup VAD callback
  useEffect(() => {
    if (!vad.current) return;
    
    const vadCallback = (vadResult: VADResult) => {
      // Update VAD state
      updateState({
        isActive: vadResult.isActive,
        energy: vadResult.energy,
        volume: vadResult.volume,
        confidence: vadResult.confidence
      });
      
      // Detect speech start transition (inactive -> active)
      if (!previousActive.current && vadResult.isActive) {
        console.log('👂 VAD detected speech start');
        if (onSpeechStart) {
          onSpeechStart();
        }
      }
      
      // Detect speech end transition (active -> inactive)
      if (previousActive.current && !vadResult.isActive) {
        console.log('👂 VAD detected speech end');
        if (onSpeechEnd) {
          onSpeechEnd();
        }
      }
      
      // Update previous state
      previousActive.current = vadResult.isActive;
    };
    
    vad.current.addCallback(vadCallback);
    
    return () => {
      if (vad.current) {
        vad.current.removeCallback(vadCallback);
      }
    };
  }, [onSpeechStart, onSpeechEnd, updateState]);
  
  // Start listening for voice activity
  const startListening = useCallback(async (): Promise<boolean> => {
    if (!vad.current) {
      console.error('❌ VAD not initialized');
      return false;
    }
    
    if (state.isListening) {
      console.log('👂 Already listening for voice activity');
      return true;
    }
    
    try {
      // Get microphone stream
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: true 
      });
      
      // Store stream reference
      currentStream.current = stream;
      
      // Initialize and start VAD
      await vad.current.initialize(stream);
      vad.current.start();
      
      updateState({ isListening: true });
      console.log('👂 Started listening for voice activity');
      return true;
      
    } catch (error) {
      console.error('❌ Failed to start VAD listening:', error);
      return false;
    }
  }, [state.isListening, updateState]);
  
  // Stop listening for voice activity
  const stopListening = useCallback(() => {
    if (vad.current) {
      vad.current.stop();
    }
    
    // Stop media stream tracks
    if (currentStream.current) {
      currentStream.current.getTracks().forEach(track => track.stop());
      currentStream.current = null;
    }
    
    updateState({ 
      isListening: false,
      isActive: false,
      energy: 0,
      volume: 0,
      confidence: 0
    });
    
    // Reset previous state
    previousActive.current = false;
    
    console.log('👂 Stopped listening for voice activity and released media stream');
  }, [updateState]);
  
  // Update VAD thresholds
  const updateThresholds = useCallback((newConfig: Partial<VADConfig>) => {
    if (vad.current) {
      // VAD doesn't currently expose a method to update thresholds
      // This would require recreating the VAD instance
      console.log('⚙️ VAD threshold update requested:', newConfig);
      // For now, just log the request
    }
  }, []);
  
  // Check if ready
  const isReady = Boolean(vad.current);
  
  return {
    state,
    startListening,
    stopListening,
    updateThresholds,
    isReady
  };
}