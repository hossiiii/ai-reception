/**
 * Mock for AudioRecorder class
 */

export interface MockAudioRecorderConfig {
  sampleRate?: number;
  channels?: number;
  bitRate?: number;
  mimeType?: string;
  chunkSize?: number;
}

export class MockAudioRecorder {
  private config: MockAudioRecorderConfig;
  private isRecording = false;
  private hasPermission = false;
  private stream: MediaStream | null = null;
  private onChunkCallback?: (chunk: Blob) => void;
  
  constructor(config: MockAudioRecorderConfig = {}) {
    this.config = {
      sampleRate: 16000,
      channels: 1,
      bitRate: 128000,
      mimeType: 'audio/webm;codecs=opus',
      chunkSize: 100,
      ...config,
    };
  }

  async requestPermission(): Promise<boolean> {
    try {
      // シミュレートされたMediaStream取得
      this.stream = new (global as any).MediaStream() as MediaStream;
      this.hasPermission = true;
      return true;
    } catch (error) {
      this.hasPermission = false;
      throw error;
    }
  }

  async startRecording(): Promise<boolean> {
    if (!this.hasPermission || !this.stream) {
      throw new Error('Permission not granted or no stream available');
    }

    this.isRecording = true;
    
    // シミュレートされた録音データ生成
    setTimeout(() => {
      if (this.isRecording && this.onChunkCallback) {
        const mockBlob = new Blob(['mock audio data'], { type: this.config.mimeType });
        this.onChunkCallback(mockBlob);
      }
    }, 100);

    return true;
  }

  stopRecording(): void {
    this.isRecording = false;
  }

  forceStop(): void {
    this.isRecording = false;
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
    }
  }

  destroy(): void {
    this.forceStop();
    this.hasPermission = false;
    this.stream = null;
  }

  getStream(): MediaStream | null {
    return this.stream;
  }

  isRecordingActive(): boolean {
    return this.isRecording;
  }

  hasAudioPermission(): boolean {
    return this.hasPermission;
  }

  setOnChunkCallback(callback: (chunk: Blob) => void): void {
    this.onChunkCallback = callback;
  }

  getConfig(): MockAudioRecorderConfig {
    return { ...this.config };
  }
}

export const createMockAudioRecorder = (config?: MockAudioRecorderConfig): MockAudioRecorder => {
  return new MockAudioRecorder(config);
};

// Setup function for tests
export const setupAudioRecorderMock = () => {
  beforeEach(() => {
    // Mock the AudioRecorder module
    jest.doMock('@/lib/audio-recorder', () => ({
      AudioRecorder: MockAudioRecorder,
      createAudioRecorder: createMockAudioRecorder,
    }));
  });

  afterEach(() => {
    jest.dontMock('@/lib/audio-recorder');
  });
};