/**
 * Audio recording and playback utilities for voice interface
 * Handles MediaRecorder API and audio data processing
 */

export interface AudioRecorderConfig {
  sampleRate?: number;
  channels?: number;
  bitRate?: number;
  mimeType?: string;
  chunkSize?: number; // in milliseconds
}

export interface AudioChunk {
  data: Blob;
  timestamp: number;
  size: number;
}

export interface AudioRecorderState {
  isRecording: boolean;
  isSupported: boolean;
  hasPermission: boolean;
  errorMessage?: string;
}

export class AudioRecorder {
  private mediaRecorder: MediaRecorder | null = null;
  private audioStream: MediaStream | null = null;
  private audioChunks: Blob[] = [];
  private config: Required<AudioRecorderConfig>;
  private onChunkCallback?: (chunk: AudioChunk) => void;
  private onStateChangeCallback?: (state: AudioRecorderState) => void;
  private chunkInterval: NodeJS.Timeout | null = null;

  constructor(config: AudioRecorderConfig = {}) {
    this.config = {
      sampleRate: 16000, // Standard for speech recognition
      channels: 1, // Mono for voice
      bitRate: 128000,
      mimeType: 'audio/webm;codecs=opus', // Good browser support
      chunkSize: 100, // 100ms chunks for real-time processing
      ...config
    };

    console.log('🎤 AudioRecorder initialized with config:', this.config);
  }

  /**
   * Check if audio recording is supported
   */
  static isSupported(): boolean {
    return !!(navigator.mediaDevices && 
              typeof navigator.mediaDevices.getUserMedia === 'function' &&
              typeof window.MediaRecorder === 'function');
  }

  /**
   * Request microphone permission
   */
  async requestPermission(): Promise<boolean> {
    try {
      if (!AudioRecorder.isSupported()) {
        throw new Error('Audio recording is not supported in this browser');
      }

      // Check for HTTPS requirement
      if (location.protocol !== 'https:' && location.hostname !== 'localhost') {
        throw new Error('Audio recording requires HTTPS connection');
      }

      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: this.config.sampleRate,
          channelCount: this.config.channels,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });

      // Stop the test stream
      stream.getTracks().forEach(track => track.stop());

      console.log('✅ Microphone permission granted');
      this.updateState({ hasPermission: true });
      return true;

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error('❌ Microphone permission denied:', errorMessage);
      this.updateState({ 
        hasPermission: false, 
        errorMessage 
      });
      return false;
    }
  }

  /**
   * Start recording audio
   */
  async startRecording(): Promise<boolean> {
    try {
      if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
        console.warn('⚠️ Already recording');
        return true;
      }

      // Get audio stream
      this.audioStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: this.config.sampleRate,
          channelCount: this.config.channels,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });

      // Create MediaRecorder
      this.mediaRecorder = new MediaRecorder(this.audioStream, {
        mimeType: this.config.mimeType,
        audioBitsPerSecond: this.config.bitRate
      });

      // Clear previous chunks
      this.audioChunks = [];

      // Set up event handlers
      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          this.audioChunks.push(event.data);
          
          // Call chunk callback if provided
          if (this.onChunkCallback) {
            this.onChunkCallback({
              data: event.data,
              timestamp: Date.now(),
              size: event.data.size
            });
          }
        }
      };

      this.mediaRecorder.onstart = () => {
        console.log('🎤 Recording started');
        this.updateState({ isRecording: true });
      };

      this.mediaRecorder.onstop = () => {
        console.log('🔇 Recording stopped');
        this.updateState({ isRecording: false });
        this.cleanup();
      };

      this.mediaRecorder.onerror = (event) => {
        console.error('❌ MediaRecorder error:', event);
        this.updateState({ 
          isRecording: false, 
          errorMessage: 'Recording error occurred' 
        });
        this.cleanup();
      };

      // Start recording with chunk intervals
      this.mediaRecorder.start(this.config.chunkSize);
      
      return true;

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown recording error';
      console.error('❌ Failed to start recording:', errorMessage);
      this.updateState({ 
        isRecording: false, 
        errorMessage 
      });
      return false;
    }
  }

  /**
   * Stop recording audio
   */
  stopRecording(): Blob | null {
    if (!this.mediaRecorder || this.mediaRecorder.state === 'inactive') {
      console.warn('⚠️ Not currently recording');
      return null;
    }

    this.mediaRecorder.stop();

    // Return combined audio blob
    if (this.audioChunks.length > 0) {
      const audioBlob = new Blob(this.audioChunks, { 
        type: this.config.mimeType 
      });
      console.log(`🎵 Recording complete: ${audioBlob.size} bytes`);
      return audioBlob;
    }

    return null;
  }

  /**
   * Get current recording state
   */
  getState(): AudioRecorderState {
    return {
      isRecording: this.mediaRecorder?.state === 'recording' || false,
      isSupported: AudioRecorder.isSupported(),
      hasPermission: true, // Will be updated when permission is checked
      errorMessage: undefined
    };
  }

  /**
   * Set callback for audio chunks (real-time processing)
   */
  setChunkCallback(callback: (chunk: AudioChunk) => void) {
    this.onChunkCallback = callback;
  }

  /**
   * Set callback for state changes
   */
  setStateChangeCallback(callback: (state: AudioRecorderState) => void) {
    this.onStateChangeCallback = callback;
  }

  /**
   * Clean up resources
   */
  private cleanup() {
    if (this.audioStream) {
      this.audioStream.getTracks().forEach(track => track.stop());
      this.audioStream = null;
    }

    if (this.chunkInterval) {
      clearInterval(this.chunkInterval);
      this.chunkInterval = null;
    }
  }

  /**
   * Update state and notify callback
   */
  private updateState(partialState: Partial<AudioRecorderState>) {
    const currentState = this.getState();
    const newState = { ...currentState, ...partialState };
    
    if (this.onStateChangeCallback) {
      this.onStateChangeCallback(newState);
    }
  }

  /**
   * Destroy recorder and clean up
   */
  destroy() {
    if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
      this.mediaRecorder.stop();
    }
    this.cleanup();
    console.log('🗑️ AudioRecorder destroyed');
  }
}

/**
 * Audio playback utilities
 */
export class AudioPlayer {
  private audioContext: AudioContext | null = null;
  private currentSource: AudioBufferSourceNode | null = null;

  constructor() {
    if (typeof window !== 'undefined' && 'AudioContext' in window) {
      this.audioContext = new AudioContext();
    } else if (typeof window !== 'undefined' && 'webkitAudioContext' in window) {
      // @ts-ignore
      this.audioContext = new webkitAudioContext();
    }
    
    console.log('🔊 AudioPlayer initialized');
  }

  /**
   * Play audio from base64 data
   */
  async playAudioFromBase64(base64Data: string): Promise<void> {
    try {
      if (!this.audioContext) {
        throw new Error('AudioContext not supported');
      }

      // Resume audio context if suspended (user interaction requirement)
      if (this.audioContext.state === 'suspended') {
        await this.audioContext.resume();
      }

      // Convert base64 to binary
      const binaryString = atob(base64Data);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }

      // Decode audio data
      const audioBuffer = await this.audioContext.decodeAudioData(bytes.buffer);

      // Stop any currently playing audio
      this.stop();

      // Create and configure audio source
      this.currentSource = this.audioContext.createBufferSource();
      this.currentSource.buffer = audioBuffer;
      this.currentSource.connect(this.audioContext.destination);

      // Create promise that resolves when audio finishes playing
      return new Promise<void>((resolve, reject) => {
        if (!this.currentSource) {
          reject(new Error('Audio source not available'));
          return;
        }

        // Clean up when finished
        this.currentSource.onended = () => {
          this.currentSource = null;
          console.log('🔇 Audio playback finished');
          resolve();
        };

        // Handle errors
        this.currentSource.onerror = (error) => {
          console.error('❌ Audio source error:', error);
          this.currentSource = null;
          reject(error);
        };

        // Play audio
        this.currentSource.start(0);
        console.log('🔊 Playing audio');
      });

    } catch (error) {
      console.error('❌ Audio playback error:', error);
      throw error;
    }
  }

  /**
   * Play audio from Blob
   */
  async playAudioFromBlob(audioBlob: Blob): Promise<void> {
    try {
      const arrayBuffer = await audioBlob.arrayBuffer();
      
      if (!this.audioContext) {
        throw new Error('AudioContext not supported');
      }

      // Resume audio context if suspended
      if (this.audioContext.state === 'suspended') {
        await this.audioContext.resume();
      }

      // Decode and play
      const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
      
      this.stop();
      
      this.currentSource = this.audioContext.createBufferSource();
      this.currentSource.buffer = audioBuffer;
      this.currentSource.connect(this.audioContext.destination);

      // Create promise that resolves when audio finishes playing
      return new Promise<void>((resolve, reject) => {
        if (!this.currentSource) {
          reject(new Error('Audio source not available'));
          return;
        }

        // Clean up when finished
        this.currentSource.onended = () => {
          this.currentSource = null;
          console.log('🔇 Audio playback from blob finished');
          resolve();
        };

        // Handle errors
        this.currentSource.onerror = (error) => {
          console.error('❌ Audio source error:', error);
          this.currentSource = null;
          reject(error);
        };

        // Play audio
        this.currentSource.start(0);
        console.log('🔊 Playing audio from blob');
      });

    } catch (error) {
      console.error('❌ Audio playback error:', error);
      throw error;
    }
  }

  /**
   * Stop current audio playback
   */
  stop() {
    if (this.currentSource) {
      try {
        this.currentSource.stop();
      } catch (error) {
        // Ignore error if already stopped
      }
      this.currentSource = null;
    }
  }

  /**
   * Check if audio is currently playing
   */
  isPlaying(): boolean {
    return this.currentSource !== null;
  }

  /**
   * Destroy player and clean up
   */
  destroy() {
    this.stop();
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
    console.log('🗑️ AudioPlayer destroyed');
  }
}

/**
 * Factory functions
 */
export function createAudioRecorder(config?: AudioRecorderConfig): AudioRecorder {
  return new AudioRecorder(config);
}

export function createAudioPlayer(): AudioPlayer {
  return new AudioPlayer();
}