/**
 * Enhanced WebSocket mock for testing
 */

export interface MockWebSocketOptions {
  autoConnect?: boolean;
  connectDelay?: number;
  failConnection?: boolean;
}

export class EnhancedMockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  // Static tracking of all instances
  static instances: EnhancedMockWebSocket[] = [];
  static lastInstance: EnhancedMockWebSocket | null = null;

  readyState: number;
  url: string;
  protocols?: string | string[];
  
  // Event handlers
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;

  // Test helpers
  sentMessages: any[] = [];
  private options: MockWebSocketOptions;
  private connectionTimer?: NodeJS.Timeout;

  constructor(url: string, protocols?: string | string[]) {
    this.url = url;
    this.protocols = protocols;
    this.readyState = EnhancedMockWebSocket.CONNECTING;
    this.options = {
      autoConnect: true,
      connectDelay: 0,
      failConnection: false,
    };

    // Track instance
    EnhancedMockWebSocket.instances.push(this);
    EnhancedMockWebSocket.lastInstance = this;

    // Auto-connect if enabled
    if (this.options.autoConnect && !this.options.failConnection) {
      this.connectionTimer = setTimeout(() => this.mockConnect(), this.options.connectDelay || 0);
    } else if (this.options.failConnection) {
      this.connectionTimer = setTimeout(() => this.mockError(), this.options.connectDelay || 0);
    }
  }

  // Configure mock behavior
  configure(options: MockWebSocketOptions) {
    this.options = { ...this.options, ...options };
  }

  // Mock connection success
  mockConnect() {
    if (this.readyState !== EnhancedMockWebSocket.CONNECTING) return;
    
    this.readyState = EnhancedMockWebSocket.OPEN;
    if (this.onopen) {
      this.onopen(new Event('open'));
    }
  }

  // Mock connection error
  mockError(reason = 'Connection failed') {
    if (this.onerror) {
      const error = new Event('error');
      Object.defineProperty(error, 'message', { value: reason });
      this.onerror(error);
    }
    this.mockClose(1006, reason);
  }

  // Mock receiving a message
  mockReceiveMessage(data: any) {
    if (this.readyState !== EnhancedMockWebSocket.OPEN) {
      console.warn('Cannot receive message: WebSocket is not open');
      return;
    }

    const messageData = typeof data === 'string' ? data : JSON.stringify(data);
    
    if (this.onmessage) {
      this.onmessage(new MessageEvent('message', { data: messageData }));
    }
  }

  // Mock closing connection
  mockClose(code = 1000, reason = 'Normal closure') {
    if (this.readyState === EnhancedMockWebSocket.CLOSED) return;
    
    this.readyState = EnhancedMockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close', { code, reason, wasClean: code === 1000 }));
    }
  }

  // WebSocket interface methods
  send(data: string | ArrayBuffer | Blob) {
    if (this.readyState !== EnhancedMockWebSocket.OPEN) {
      throw new Error('InvalidStateError: WebSocket is not open');
    }

    // Parse and track sent messages
    let parsedData;
    try {
      parsedData = typeof data === 'string' ? JSON.parse(data) : data;
    } catch {
      parsedData = data;
    }
    
    this.sentMessages.push(parsedData);

    // Optional: Auto-respond to certain messages
    this.handleAutoResponse(parsedData);
  }

  close(code?: number, reason?: string) {
    if (this.connectionTimer) {
      clearTimeout(this.connectionTimer);
    }
    this.mockClose(code, reason);
  }

  // Auto-response handler for common patterns
  private handleAutoResponse(data: any) {
    // Override in tests for specific auto-response behavior
  }

  // Test helper methods
  static reset() {
    EnhancedMockWebSocket.instances = [];
    EnhancedMockWebSocket.lastInstance = null;
  }

  static getInstance(index = 0): EnhancedMockWebSocket | undefined {
    return EnhancedMockWebSocket.instances[index];
  }

  getLastSentMessage() {
    return this.sentMessages[this.sentMessages.length - 1];
  }

  getSentMessages() {
    return [...this.sentMessages];
  }

  clearSentMessages() {
    this.sentMessages = [];
  }

  isConnected() {
    return this.readyState === EnhancedMockWebSocket.OPEN;
  }
}

// Setup function for tests
export const setupWebSocketMock = () => {
  // Store original WebSocket
  const originalWebSocket = global.WebSocket;

  beforeEach(() => {
    EnhancedMockWebSocket.reset();
    (global as any).WebSocket = EnhancedMockWebSocket;
  });

  afterEach(() => {
    EnhancedMockWebSocket.reset();
    (global as any).WebSocket = originalWebSocket;
  });

  return {
    getWebSocketInstance: () => EnhancedMockWebSocket.lastInstance,
    getAllInstances: () => EnhancedMockWebSocket.instances,
  };
};