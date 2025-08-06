/**
 * Client-side Voice Activity Detection (VAD)
 * Provides real-time voice activity analysis and visual feedback
 */

export interface VADConfig {
  fftSize?: number;
  smoothingTimeConstant?: number;
  energyThreshold?: number;
  silenceDuration?: number; // in milliseconds
  minSpeechDuration?: number; // in milliseconds
  updateInterval?: number; // in milliseconds
}

export interface VADResult {
  isActive: boolean;
  energy: number;
  volume: number; // 0-100 for UI display
  timestamp: number;
  confidence: number;
}

export interface VADState {
  isActive: boolean;
  energy: number;
  volume: number;
  consecutiveSilence: number;
  consecutiveSpeech: number;
  history: number[]; // Energy history for smoothing
}

export type VADCallback = (result: VADResult) => void;

export class ClientVoiceActivityDetector {
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private source: MediaStreamAudioSourceNode | null = null;
  private dataArray: Uint8Array | null = null;
  private config: Required<VADConfig>;
  private state: VADState;
  private animationFrame: number | null = null;
  private callbacks: VADCallback[] = [];
  private isRunning = false;

  constructor(config: VADConfig = {}) {
    this.config = {
      fftSize: 256,
      smoothingTimeConstant: 0.8,
      energyThreshold: 30, // 0-100 scale - 30を超えたら発話検出
      silenceDuration: 1500, // 1.5 seconds - 30を下回る状態が1500ms続いたら発話終了
      minSpeechDuration: 300, // 300ms
      updateInterval: 50, // 50ms updates (20 FPS)
      ...config
    };

    this.state = {
      isActive: false,
      energy: 0,
      volume: 0,
      consecutiveSilence: 0,
      consecutiveSpeech: 0,
      history: []
    };

    console.log('🎤 Client VAD initialized with config:', this.config);
  }

  /**
   * Initialize VAD with audio stream
   */
  async initialize(stream: MediaStream): Promise<boolean> {
    try {
      // Create audio context
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      
      // Resume context if suspended (user interaction requirement)
      if (this.audioContext.state === 'suspended') {
        await this.audioContext.resume();
      }

      // Create analyser node
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = this.config.fftSize;
      this.analyser.smoothingTimeConstant = this.config.smoothingTimeConstant;

      // Connect audio stream to analyser
      this.source = this.audioContext.createMediaStreamSource(stream);
      this.source.connect(this.analyser);

      // Create data array for frequency analysis
      this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);

      console.log('✅ Client VAD initialized successfully');
      return true;

    } catch (error) {
      console.error('❌ Failed to initialize Client VAD:', error);
      return false;
    }
  }

  /**
   * Start voice activity detection
   */
  start() {
    if (this.isRunning) {
      console.warn('⚠️ VAD already running');
      return;
    }

    if (!this.analyser || !this.dataArray) {
      console.error('❌ VAD not initialized');
      return;
    }

    this.isRunning = true;
    this.resetState();
    this.analyze();
    console.log('🎤 VAD started');
  }

  /**
   * Stop voice activity detection
   */
  stop() {
    this.isRunning = false;
    
    if (this.animationFrame) {
      cancelAnimationFrame(this.animationFrame);
      this.animationFrame = null;
    }

    console.log('🔇 VAD stopped');
  }

  /**
   * Add callback for VAD results
   */
  addCallback(callback: VADCallback) {
    this.callbacks.push(callback);
  }

  /**
   * Remove callback
   */
  removeCallback(callback: VADCallback) {
    const index = this.callbacks.indexOf(callback);
    if (index > -1) {
      this.callbacks.splice(index, 1);
    }
  }

  /**
   * Get current VAD state
   */
  getState(): VADState {
    return { ...this.state };
  }

  /**
   * Update VAD configuration
   */
  updateConfig(newConfig: Partial<VADConfig>) {
    this.config = { ...this.config, ...newConfig };
    console.log('🔧 VAD config updated:', newConfig);
  }

  /**
   * Main analysis loop
   */
  private analyze() {
    if (!this.isRunning || !this.analyser || !this.dataArray) {
      return;
    }

    // Get frequency data
    this.analyser.getByteFrequencyData(this.dataArray as Uint8Array<ArrayBuffer>);

    // Calculate energy and volume
    const energy = this.calculateEnergy(this.dataArray);
    const volume = this.calculateVolume(this.dataArray);

    // Update history for smoothing (but use raw energy for threshold check)
    this.updateHistory(energy);

    // Use raw energy for threshold comparison (not smoothed)
    // エネルギーが30を超えたら即座に発話として検出
    const isAboveThreshold = energy > this.config.energyThreshold;

    // Update state counters
    this.updateStateCounters(isAboveThreshold);

    // Calculate confidence
    const confidence = this.calculateConfidence(energy, isAboveThreshold);

    // Update state
    this.state.energy = energy; // Use raw energy instead of smoothed
    this.state.volume = volume;
    const previousActive = this.state.isActive;
    this.state.isActive = this.shouldBeActive();

    // Log state transitions for debugging
    if (previousActive !== this.state.isActive) {
      console.log(`📊 VAD State Change: ${previousActive ? 'ACTIVE' : 'INACTIVE'} → ${this.state.isActive ? 'ACTIVE' : 'INACTIVE'}`);
    }
    
    // Log energy for debugging (only when above threshold)
    if (isAboveThreshold && this.state.consecutiveSpeech <= this.config.updateInterval) {
      console.log(`🎤 Energy spike: ${energy.toFixed(1)} (threshold: ${this.config.energyThreshold})`);
    }

    // Create result
    const result: VADResult = {
      isActive: this.state.isActive,
      energy: this.state.energy,
      volume: this.state.volume,
      timestamp: Date.now(),
      confidence
    };

    // Call callbacks
    this.callbacks.forEach(callback => {
      try {
        callback(result);
      } catch (error) {
        console.error('❌ VAD callback error:', error);
      }
    });

    // Schedule next analysis
    this.animationFrame = requestAnimationFrame(() => {
      setTimeout(() => this.analyze(), this.config.updateInterval);
    });
  }

  /**
   * Calculate energy from frequency data
   */
  private calculateEnergy(dataArray: Uint8Array): number {
    let sum = 0;
    let maxValue = 0;
    
    // Focus on speech frequency range (80Hz - 3000Hz)
    // FFT bins represent frequency ranges, calculate relevant bins
    const sampleRate = this.audioContext?.sampleRate || 44100;
    const binSize = sampleRate / (this.config.fftSize * 2);
    const startBin = Math.floor(80 / binSize);
    const endBin = Math.floor(3000 / binSize);

    for (let i = startBin; i < Math.min(endBin, dataArray.length); i++) {
      sum += dataArray[i];
      maxValue = Math.max(maxValue, dataArray[i]);
    }

    // Use average instead of RMS for more sensitive detection
    // Normalize to 0-100 scale
    const avgEnergy = (sum / (endBin - startBin)) / 255 * 100;
    
    // Boost the energy value to make it more sensitive
    const boostedEnergy = avgEnergy * 1.5;
    
    return Math.min(100, boostedEnergy);
  }

  /**
   * Calculate volume level for UI display
   */
  private calculateVolume(dataArray: Uint8Array): number {
    let sum = 0;
    for (let i = 0; i < dataArray.length; i++) {
      sum += dataArray[i];
    }
    
    // Normalize to 0-100 scale
    const volume = (sum / dataArray.length) / 255 * 100;
    return Math.min(100, volume);
  }

  /**
   * Update energy history for smoothing
   */
  private updateHistory(energy: number) {
    this.state.history.push(energy);
    
    // Keep only recent history (2 seconds worth)
    const maxHistory = Math.floor(2000 / this.config.updateInterval);
    if (this.state.history.length > maxHistory) {
      this.state.history = this.state.history.slice(-maxHistory);
    }
  }


  /**
   * Update state counters for speech/silence detection
   */
  private updateStateCounters(isActive: boolean) {
    if (isActive) {
      this.state.consecutiveSpeech += this.config.updateInterval;
      this.state.consecutiveSilence = 0;
    } else {
      this.state.consecutiveSilence += this.config.updateInterval;
      this.state.consecutiveSpeech = 0;
    }
  }

  /**
   * Determine if should be considered active based on duration thresholds
   */
  private shouldBeActive(): boolean {
    // 新しく発話が始まった場合（エネルギーが閾値を超えている）
    if (this.state.consecutiveSpeech > 0 && !this.state.isActive) {
      console.log(`🎤 Speech started (energy above threshold)`);
      return true;
    }
    
    // 既に発話中の場合
    if (this.state.isActive) {
      // 無音が1500ms未満なら発話継続
      if (this.state.consecutiveSilence < this.config.silenceDuration) {
        // デバッグ: 無音継続時間をログ出力
        if (this.state.consecutiveSilence > 0 && this.state.consecutiveSilence % 500 === 0) {
          console.log(`⏱️ Silence duration: ${this.state.consecutiveSilence}ms / ${this.config.silenceDuration}ms`);
        }
        return true;
      } else {
        // 1500ms無音が続いたら発話終了
        console.log(`🔇 Speech ended after ${this.state.consecutiveSilence}ms of silence`);
        return false;
      }
    }

    return false;
  }

  /**
   * Calculate confidence score for VAD decision
   */
  private calculateConfidence(energy: number, isActive: boolean): number {
    if (this.state.history.length < 5) {
      return 0.5; // Low confidence with insufficient history
    }

    // Base confidence on energy level relative to threshold
    const energyRatio = energy / this.config.energyThreshold;
    let confidence = 0.5;

    if (isActive) {
      // Higher confidence for stronger signals above threshold
      confidence = Math.min(0.95, 0.5 + 0.4 * (energyRatio - 1));
    } else {
      // Higher confidence for signals well below threshold
      confidence = Math.min(0.95, 0.5 + 0.4 * (1 - energyRatio));
    }

    // Adjust based on consistency
    const recentEnergies = this.state.history.slice(-10);
    const variance = this.calculateVariance(recentEnergies);
    const consistencyFactor = Math.max(0.5, 1.0 - variance / 100);
    
    return Math.max(0.1, Math.min(0.95, confidence * consistencyFactor));
  }

  /**
   * Calculate variance of energy values
   */
  private calculateVariance(values: number[]): number {
    if (values.length === 0) return 0;
    
    const mean = values.reduce((sum, val) => sum + val, 0) / values.length;
    const variance = values.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / values.length;
    
    return variance;
  }

  /**
   * Reset VAD state
   */
  private resetState() {
    this.state = {
      isActive: false,
      energy: 0,
      volume: 0,
      consecutiveSilence: 0,
      consecutiveSpeech: 0,
      history: []
    };
  }

  /**
   * Destroy VAD and clean up resources
   */
  destroy() {
    this.stop();
    
    if (this.source) {
      this.source.disconnect();
      this.source = null;
    }

    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }

    this.callbacks.length = 0;
    console.log('🗑️ Client VAD destroyed');
  }
}

/**
 * Factory function to create ClientVoiceActivityDetector
 */
export function createClientVAD(config?: VADConfig): ClientVoiceActivityDetector {
  return new ClientVoiceActivityDetector(config);
}