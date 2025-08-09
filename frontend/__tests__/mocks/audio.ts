/**
 * Enhanced Audio API mocks for testing
 */

// Mock AudioContext with full API surface
export class MockAudioContext implements Partial<AudioContext> {
  state: AudioContextState = 'running';
  currentTime = 0;
  sampleRate = 48000;
  baseLatency = 0.01;
  
  destination = {
    maxChannelCount: 2,
    channelCount: 2,
    channelCountMode: 'max' as ChannelCountMode,
    channelInterpretation: 'speakers' as ChannelInterpretation,
    numberOfInputs: 1,
    numberOfOutputs: 0,
    connect: jest.fn(),
    disconnect: jest.fn(),
    context: this as any,
  };

  // Track created nodes for testing
  createdNodes: any[] = [];

  createMediaStreamSource = jest.fn((stream: MediaStream) => {
    const node = {
      connect: jest.fn(),
      disconnect: jest.fn(),
      mediaStream: stream,
      context: this,
    };
    this.createdNodes.push(node);
    return node as any;
  });

  createScriptProcessor = jest.fn((
    bufferSize = 4096,
    numberOfInputChannels = 2,
    numberOfOutputChannels = 2
  ) => {
    const node = {
      bufferSize,
      numberOfInputChannels,
      numberOfOutputChannels,
      connect: jest.fn(),
      disconnect: jest.fn(),
      onaudioprocess: null as any,
      context: this,
    };
    this.createdNodes.push(node);
    return node as any;
  });

  createAnalyser = jest.fn(() => {
    const node = {
      fftSize: 2048,
      frequencyBinCount: 1024,
      minDecibels: -100,
      maxDecibels: -30,
      smoothingTimeConstant: 0.8,
      connect: jest.fn(),
      disconnect: jest.fn(),
      getByteFrequencyData: jest.fn((array: Uint8Array) => {
        // Simulate some frequency data
        for (let i = 0; i < array.length; i++) {
          array[i] = Math.floor(Math.random() * 256);
        }
      }),
      getByteTimeDomainData: jest.fn((array: Uint8Array) => {
        // Simulate waveform data
        for (let i = 0; i < array.length; i++) {
          array[i] = 128 + Math.floor(Math.sin(i * 0.1) * 50);
        }
      }),
      getFloatFrequencyData: jest.fn(),
      getFloatTimeDomainData: jest.fn(),
      context: this,
    };
    this.createdNodes.push(node);
    return node as any;
  });

  createGain = jest.fn(() => {
    const node = {
      gain: {
        value: 1,
        setValueAtTime: jest.fn(),
        linearRampToValueAtTime: jest.fn(),
        exponentialRampToValueAtTime: jest.fn(),
      },
      connect: jest.fn(),
      disconnect: jest.fn(),
      context: this,
    };
    this.createdNodes.push(node);
    return node as any;
  });

  close = jest.fn(() => {
    this.state = 'closed';
    return Promise.resolve();
  });

  resume = jest.fn(() => {
    this.state = 'running';
    return Promise.resolve();
  });

  suspend = jest.fn(() => {
    this.state = 'suspended';
    return Promise.resolve();
  });

  // Test helpers
  simulateTime(seconds: number) {
    this.currentTime += seconds;
  }

  getCreatedNodes() {
    return [...this.createdNodes];
  }

  reset() {
    this.createdNodes = [];
    this.currentTime = 0;
    this.state = 'running';
  }
}

// Mock MediaRecorder with realistic behavior
export class MockMediaRecorder implements Partial<MediaRecorder> {
  state: RecordingState = 'inactive';
  stream: MediaStream;
  mimeType: string;
  audioBitsPerSecond?: number;
  
  // Event handlers
  ondataavailable: ((event: BlobEvent) => void) | null = null;
  onstart: ((event: Event) => void) | null = null;
  onstop: ((event: Event) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onpause: ((event: Event) => void) | null = null;
  onresume: ((event: Event) => void) | null = null;

  // Test helpers
  private recordedChunks: Blob[] = [];
  private recordingTimer?: NodeJS.Timeout;
  private dataTimer?: NodeJS.Timeout;

  constructor(stream: MediaStream, options?: MediaRecorderOptions) {
    this.stream = stream;
    this.mimeType = options?.mimeType || 'audio/webm';
    this.audioBitsPerSecond = options?.audioBitsPerSecond;
  }

  start(timeslice?: number) {
    if (this.state !== 'inactive') {
      throw new Error('InvalidStateError: MediaRecorder is not inactive');
    }

    this.state = 'recording';
    this.recordedChunks = [];

    if (this.onstart) {
      setTimeout(() => this.onstart!(new Event('start')), 0);
    }

    // Simulate periodic data availability
    if (timeslice && timeslice > 0) {
      this.dataTimer = setInterval(() => {
        this.produceData();
      }, timeslice);
    }
  }

  stop() {
    if (this.state === 'inactive') {
      throw new Error('InvalidStateError: MediaRecorder is not recording');
    }

    this.state = 'inactive';

    if (this.dataTimer) {
      clearInterval(this.dataTimer);
      this.dataTimer = undefined;
    }

    // Produce final data
    this.produceData();

    if (this.onstop) {
      setTimeout(() => this.onstop!(new Event('stop')), 0);
    }
  }

  pause() {
    if (this.state !== 'recording') {
      throw new Error('InvalidStateError: MediaRecorder is not recording');
    }

    this.state = 'paused';

    if (this.dataTimer) {
      clearInterval(this.dataTimer);
      this.dataTimer = undefined;
    }

    if (this.onpause) {
      this.onpause(new Event('pause'));
    }
  }

  resume() {
    if (this.state !== 'paused') {
      throw new Error('InvalidStateError: MediaRecorder is not paused');
    }

    this.state = 'recording';

    if (this.onresume) {
      this.onresume(new Event('resume'));
    }
  }

  requestData() {
    if (this.state === 'inactive') {
      throw new Error('InvalidStateError: MediaRecorder is not recording');
    }
    this.produceData();
  }

  private produceData() {
    const mockData = new Blob(
      [`mock audio data ${Date.now()}`],
      { type: this.mimeType }
    );
    
    this.recordedChunks.push(mockData);

    if (this.ondataavailable) {
      const event = new BlobEvent('dataavailable', { data: mockData });
      this.ondataavailable(event);
    }
  }

  // Test helpers
  getRecordedChunks() {
    return [...this.recordedChunks];
  }

  simulateError(message = 'Recording error') {
    if (this.onerror) {
      const error = new Event('error');
      Object.defineProperty(error, 'message', { value: message });
      this.onerror(error);
    }
    this.stop();
  }

  static isTypeSupported(mimeType: string): boolean {
    const supportedTypes = [
      'audio/webm',
      'audio/webm;codecs=opus',
      'audio/wav',
      'audio/ogg',
      'audio/mp4',
    ];
    return supportedTypes.includes(mimeType.toLowerCase());
  }
}

// Mock MediaStream and MediaStreamTrack
export class MockMediaStreamTrack implements Partial<MediaStreamTrack> {
  enabled = true;
  id = `track-${Math.random().toString(36).substr(2, 9)}`;
  kind: 'audio' | 'video' = 'audio';
  label = 'Mock Audio Track';
  muted = false;
  readyState: MediaStreamTrackState = 'live';
  
  // Event handlers
  onended: ((event: Event) => void) | null = null;
  onmute: ((event: Event) => void) | null = null;
  onunmute: ((event: Event) => void) | null = null;

  stop = jest.fn(() => {
    this.readyState = 'ended';
    if (this.onended) {
      this.onended(new Event('ended'));
    }
  });

  clone = jest.fn(() => {
    return new MockMediaStreamTrack();
  });

  getCapabilities = jest.fn(() => ({}));
  getConstraints = jest.fn(() => ({}));
  getSettings = jest.fn(() => ({
    deviceId: 'default',
    groupId: 'default',
    sampleRate: 48000,
    channelCount: 1,
    echoCancellation: true,
    noiseSuppression: true,
  }));

  applyConstraints = jest.fn(() => Promise.resolve());
}

export class MockMediaStream implements Partial<MediaStream> {
  id = `stream-${Math.random().toString(36).substr(2, 9)}`;
  active = true;
  
  private tracks: MockMediaStreamTrack[] = [];

  constructor(tracks?: MediaStreamTrack[]) {
    if (tracks) {
      this.tracks = tracks as MockMediaStreamTrack[];
    } else {
      // Create a default audio track
      this.tracks = [new MockMediaStreamTrack()];
    }
  }

  getTracks = jest.fn(() => [...this.tracks]);
  
  getAudioTracks = jest.fn(() => 
    this.tracks.filter(t => t.kind === 'audio')
  );
  
  getVideoTracks = jest.fn(() => 
    this.tracks.filter(t => t.kind === 'video')
  );

  getTrackById = jest.fn((id: string) => 
    this.tracks.find(t => t.id === id) || null
  );

  addTrack = jest.fn((track: MediaStreamTrack) => {
    this.tracks.push(track as MockMediaStreamTrack);
  });

  removeTrack = jest.fn((track: MediaStreamTrack) => {
    const index = this.tracks.indexOf(track as MockMediaStreamTrack);
    if (index > -1) {
      this.tracks.splice(index, 1);
    }
  });

  clone = jest.fn(() => {
    return new MockMediaStream(this.tracks.map(t => t.clone()));
  });

  // Test helper
  simulateTrackEnd() {
    this.tracks.forEach(track => track.stop());
    this.active = false;
  }
}

// Setup function for audio mocks
export const setupAudioMocks = () => {
  const originalAudioContext = (global as any).AudioContext;
  const originalMediaRecorder = (global as any).MediaRecorder;
  const originalMediaStream = (global as any).MediaStream;

  beforeEach(() => {
    (global as any).AudioContext = MockAudioContext;
    (global as any).webkitAudioContext = MockAudioContext;
    (global as any).MediaRecorder = MockMediaRecorder;
    (global as any).MediaStream = MockMediaStream;
    (global as any).MediaStreamTrack = MockMediaStreamTrack;

    // Mock BlobEvent if not available
    if (typeof BlobEvent === 'undefined') {
      (global as any).BlobEvent = class BlobEvent extends Event {
        data: Blob;
        constructor(type: string, init: { data: Blob }) {
          super(type);
          this.data = init.data;
        }
      };
    }

    // Mock navigator.mediaDevices
    Object.defineProperty(navigator, 'mediaDevices', {
      writable: true,
      configurable: true,
      value: {
        getUserMedia: jest.fn(() => 
          Promise.resolve(new MockMediaStream() as any)
        ),
        enumerateDevices: jest.fn(() => 
          Promise.resolve([
            {
              deviceId: 'default',
              kind: 'audioinput' as MediaDeviceKind,
              label: 'Default Microphone',
              groupId: 'default',
              toJSON: () => ({}),
            },
          ])
        ),
        getSupportedConstraints: jest.fn(() => ({
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        })),
      },
    });
  });

  afterEach(() => {
    (global as any).AudioContext = originalAudioContext;
    (global as any).webkitAudioContext = originalAudioContext;
    (global as any).MediaRecorder = originalMediaRecorder;
    (global as any).MediaStream = originalMediaStream;
  });
};