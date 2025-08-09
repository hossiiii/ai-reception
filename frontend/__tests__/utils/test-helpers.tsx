/**
 * Test utilities for improved testing experience
 */

import React, { ReactElement } from 'react';
import { render as rtlRender, RenderOptions } from '@testing-library/react';
import { act as rtlAct } from '@testing-library/react';

// Custom render function with providers
export function render(
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) {
  // You can add providers here if needed (e.g., theme, router, etc.)
  function Wrapper({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
  }

  return rtlRender(ui, { wrapper: Wrapper, ...options });
}

// Re-export act from @testing-library/react
export const act = rtlAct;

// Re-export everything from @testing-library/react
export * from '@testing-library/react';

// Mock timers utility
export const mockTimers = () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });
};

// Wait utility with better error handling
export const waitForWithTimeout = async (
  callback: () => void | Promise<void>,
  timeout = 5000
) => {
  const startTime = Date.now();
  
  while (Date.now() - startTime < timeout) {
    try {
      await callback();
      return;
    } catch (error) {
      if (Date.now() - startTime >= timeout) {
        throw error;
      }
      await new Promise(resolve => setTimeout(resolve, 50));
    }
  }
};

// Mock fetch utility
export const mockFetch = (response: any, options?: { delay?: number; status?: number }) => {
  const mockResponse = {
    ok: options?.status ? options.status >= 200 && options.status < 300 : true,
    status: options?.status || 200,
    json: async () => {
      if (options?.delay) {
        await new Promise(resolve => setTimeout(resolve, options.delay));
      }
      return response;
    },
    text: async () => JSON.stringify(response),
  };

  return jest.fn(() => Promise.resolve(mockResponse));
};

// Create mock WebSocket
export class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState: number;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;

  constructor(public url: string) {
    this.readyState = MockWebSocket.CONNECTING;
    setTimeout(() => this.connect(), 0);
  }

  connect() {
    this.readyState = MockWebSocket.OPEN;
    if (this.onopen) {
      this.onopen(new Event('open'));
    }
  }

  send(data: string | ArrayBuffer | Blob) {
    if (this.readyState !== MockWebSocket.OPEN) {
      throw new Error('WebSocket is not open');
    }
    // Mock echo or custom response logic here
  }

  close(code?: number, reason?: string) {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close', { code, reason }));
    }
  }

  // Helper to simulate receiving a message
  receiveMessage(data: any) {
    if (this.onmessage) {
      this.onmessage(new MessageEvent('message', { data: JSON.stringify(data) }));
    }
  }

  // Helper to simulate an error
  simulateError() {
    if (this.onerror) {
      this.onerror(new Event('error'));
    }
  }
}

// Mock Audio APIs
export class MockAudioContext {
  state: 'suspended' | 'running' | 'closed' = 'running';
  destination = { maxChannelCount: 2 };
  sampleRate = 48000;

  createMediaStreamSource = jest.fn(() => ({
    connect: jest.fn(),
    disconnect: jest.fn(),
  }));

  createScriptProcessor = jest.fn((bufferSize, inputChannels, outputChannels) => ({
    connect: jest.fn(),
    disconnect: jest.fn(),
    onaudioprocess: null,
  }));

  createAnalyser = jest.fn(() => ({
    connect: jest.fn(),
    disconnect: jest.fn(),
    fftSize: 2048,
    frequencyBinCount: 1024,
    getByteFrequencyData: jest.fn(),
    getByteTimeDomainData: jest.fn(),
  }));

  close = jest.fn(() => Promise.resolve());
  resume = jest.fn(() => Promise.resolve());
  suspend = jest.fn(() => Promise.resolve());
}

export class MockMediaRecorder {
  state: 'inactive' | 'recording' | 'paused' = 'inactive';
  ondataavailable: ((event: any) => void) | null = null;
  onstart: (() => void) | null = null;
  onstop: (() => void) | null = null;
  onerror: ((event: any) => void) | null = null;

  constructor(public stream: MediaStream, public options?: MediaRecorderOptions) {}

  start(timeslice?: number) {
    this.state = 'recording';
    if (this.onstart) this.onstart();
    
    // Simulate data available
    setTimeout(() => {
      if (this.ondataavailable) {
        this.ondataavailable({
          data: new Blob(['mock audio data'], { type: 'audio/webm' })
        });
      }
    }, 100);
  }

  stop() {
    this.state = 'inactive';
    if (this.onstop) this.onstop();
  }

  pause() {
    this.state = 'paused';
  }

  resume() {
    this.state = 'recording';
  }

  static isTypeSupported(mimeType: string) {
    return ['audio/webm', 'audio/wav'].includes(mimeType);
  }
}

// Mock navigator.mediaDevices
export const mockMediaDevices = () => {
  const mockStream = {
    getTracks: () => [{
      stop: jest.fn(),
      kind: 'audio',
    }],
    getAudioTracks: () => [{
      stop: jest.fn(),
    }],
  };

  Object.defineProperty(navigator, 'mediaDevices', {
    writable: true,
    value: {
      getUserMedia: jest.fn(() => Promise.resolve(mockStream)),
      enumerateDevices: jest.fn(() => Promise.resolve([
        { kind: 'audioinput', label: 'Default Microphone', deviceId: 'default' }
      ])),
    },
  });

  return mockStream;
};

// Create a test message event
export const createMessageEvent = (data: any) => {
  return new MessageEvent('message', {
    data: typeof data === 'string' ? data : JSON.stringify(data),
  });
};

// Helper to test async state updates
export const testAsyncStateUpdate = async (
  callback: () => void | Promise<void>,
  assertion: () => void
) => {
  await act(async () => {
    await callback();
  });
  assertion();
};