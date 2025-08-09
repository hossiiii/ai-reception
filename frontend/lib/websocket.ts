/**
 * WebSocket client for real-time voice communication
 * Handles connection management, audio streaming, and message handling
 */

export interface VoiceMessage {
  type: 'voice_response' | 'transcription' | 'vad_status' | 'processing' | 'ready' | 
        'error' | 'conversation_completed' | 'audio_reset' | 'status' | 'pong';
  session_id: string;
  timestamp: number;
  text?: string;
  audio?: string; // base64 encoded
  step?: string;
  visitor_info?: any;
  calendar_result?: any;
  completed?: boolean;
  error?: string;
  message?: string;
  // VAD specific fields
  is_speech?: boolean;
  energy_level?: number;
  confidence?: number;
  duration_ms?: number;
  // Status fields
  vad_state?: any;
  buffer_size?: number;
  collecting_speech?: boolean;
}

export interface VoiceWebSocketConfig {
  reconnectAttempts?: number;
  reconnectDelay?: number;
  heartbeatInterval?: number;
  maxReconnectDelay?: number;
}

export interface VoiceWebSocketState {
  connected: boolean;
  connecting: boolean;
  error?: string;
  lastHeartbeat?: number;
  reconnectAttempts: number;
}

export type MessageHandler = (message: VoiceMessage) => void;
export type StateChangeHandler = (state: VoiceWebSocketState) => void;

export class VoiceWebSocketClient {
  private ws: WebSocket | null = null;
  private config: Required<VoiceWebSocketConfig>;
  private sessionId: string;
  private baseUrl: string;
  private messageHandlers: Map<string, MessageHandler[]> = new Map();
  private stateChangeHandlers: StateChangeHandler[] = [];
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private state: VoiceWebSocketState;

  constructor(sessionId: string, baseUrl?: string, config: VoiceWebSocketConfig = {}) {
    this.sessionId = sessionId;
    this.baseUrl = baseUrl || this.getDefaultBaseUrl();
    this.config = {
      reconnectAttempts: 5,
      reconnectDelay: 1000,
      heartbeatInterval: 30000, // 30 seconds
      maxReconnectDelay: 30000, // 30 seconds max
      ...config
    };
    
    this.state = {
      connected: false,
      connecting: false,
      reconnectAttempts: 0
    };

    console.log(`🔌 VoiceWebSocketClient created for session: ${sessionId}`);
  }

  /**
   * Get default WebSocket URL for backend server
   */
  private getDefaultBaseUrl(): string {
    // In development, always connect to backend server on port 8000
    if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
      return 'ws://localhost:8000';
    }
    
    // In production, use the API URL from environment variables
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (apiUrl) {
      // Convert HTTP/HTTPS to WS/WSS protocol
      return apiUrl.replace(/^https:/, 'wss:').replace(/^http:/, 'ws:');
    }
    
    // Fallback: determine protocol based on current page protocol
    const protocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//localhost:8000`;
  }

  /**
   * Connect to WebSocket server
   */
  async connect(): Promise<boolean> {
    if (this.ws && (this.ws.readyState === WebSocket.CONNECTING || this.ws.readyState === WebSocket.OPEN)) {
      console.warn('⚠️ WebSocket already connected or connecting');
      return true;
    }

    this.updateState({ connecting: true, error: undefined });

    try {
      const wsUrl = `${this.baseUrl}/ws/voice/${this.sessionId}`;
      console.log(`🔌 Connecting to WebSocket: ${wsUrl}`);
      
      this.ws = new WebSocket(wsUrl);
      
      return new Promise((resolve, reject) => {
        if (!this.ws) {
          reject(new Error('Failed to create WebSocket'));
          return;
        }

        const timeout = setTimeout(() => {
          this.updateState({ 
            connecting: false, 
            error: 'Connection timeout' 
          });
          reject(new Error('Connection timeout'));
        }, 10000); // 10 second timeout

        this.ws.onopen = () => {
          clearTimeout(timeout);
          console.log('✅ WebSocket connected');
          this.updateState({ 
            connected: true, 
            connecting: false, 
            reconnectAttempts: 0 
          });
          this.startHeartbeat();
          resolve(true);
        };

        this.ws.onclose = (event) => {
          clearTimeout(timeout);
          console.log('🔌 WebSocket disconnected:', event.code, event.reason);
          this.updateState({ 
            connected: false, 
            connecting: false 
          });
          this.stopHeartbeat();
          
          // Attempt reconnection if not a clean close
          if (event.code !== 1000 && this.state.reconnectAttempts < this.config.reconnectAttempts) {
            this.attemptReconnect();
          }
        };

        this.ws.onerror = (error) => {
          clearTimeout(timeout);
          console.error('❌ WebSocket error:', error);
          this.updateState({ 
            connected: false, 
            connecting: false, 
            error: 'Connection error' 
          });
          reject(new Error('WebSocket connection failed'));
        };

        this.ws.onmessage = (event) => {
          this.handleMessage(event);
        };
      });

    } catch (error) {
      console.error('❌ Failed to create WebSocket connection:', error);
      this.updateState({ 
        connecting: false, 
        error: error instanceof Error ? error.message : 'Unknown error' 
      });
      return false;
    }
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect() {
    this.stopHeartbeat();
    
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.ws) {
      this.ws.close(1000, 'Client disconnecting');
      this.ws = null;
    }

    this.updateState({ 
      connected: false, 
      connecting: false,
      reconnectAttempts: 0
    });
    
    console.log('🔌 WebSocket disconnected by client');
  }

  /**
   * Send audio data to server
   */
  async sendAudioData(audioData: ArrayBuffer | Blob): Promise<boolean> {
    if (!this.isConnected()) {
      console.warn('⚠️ Cannot send audio: WebSocket not connected');
      return false;
    }

    try {
      if (audioData instanceof Blob) {
        // Convert blob to ArrayBuffer and wait for it
        const buffer = await audioData.arrayBuffer();
        this.ws?.send(buffer);
      } else {
        this.ws?.send(audioData);
      }
      return true;
    } catch (error) {
      console.error('❌ Failed to send audio data:', error);
      return false;
    }
  }

  /**
   * Send control command to server
   */
  sendCommand(command: string, data?: any): boolean {
    if (!this.isConnected()) {
      console.warn('⚠️ Cannot send command: WebSocket not connected');
      return false;
    }

    try {
      const message = {
        command,
        ...data
      };
      this.ws?.send(JSON.stringify(message));
      return true;
    } catch (error) {
      console.error('❌ Failed to send command:', error);
      return false;
    }
  }

  /**
   * Check if WebSocket is connected
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN || false;
  }

  /**
   * Get current connection state
   */
  getState(): VoiceWebSocketState {
    return { ...this.state };
  }

  /**
   * Add message handler for specific message type
   */
  addMessageHandler(messageType: string, handler: MessageHandler) {
    if (!this.messageHandlers.has(messageType)) {
      this.messageHandlers.set(messageType, []);
    }
    this.messageHandlers.get(messageType)!.push(handler);
  }

  /**
   * Remove message handler
   */
  removeMessageHandler(messageType: string, handler: MessageHandler) {
    const handlers = this.messageHandlers.get(messageType);
    if (handlers) {
      const index = handlers.indexOf(handler);
      if (index > -1) {
        handlers.splice(index, 1);
      }
    }
  }

  /**
   * Add state change handler
   */
  addStateChangeHandler(handler: StateChangeHandler) {
    this.stateChangeHandlers.push(handler);
  }

  /**
   * Remove state change handler
   */
  removeStateChangeHandler(handler: StateChangeHandler) {
    const index = this.stateChangeHandlers.indexOf(handler);
    if (index > -1) {
      this.stateChangeHandlers.splice(index, 1);
    }
  }

  /**
   * Handle incoming WebSocket message
   */
  private handleMessage(event: MessageEvent) {
    try {
      const message: VoiceMessage = JSON.parse(event.data);
      
      // Update last heartbeat if this is a pong
      if (message.type === 'pong') {
        this.state.lastHeartbeat = Date.now();
      }

      // Call registered handlers for this message type
      const handlers = this.messageHandlers.get(message.type);
      if (handlers) {
        handlers.forEach(handler => {
          try {
            handler(message);
          } catch (error) {
            console.error(`❌ Message handler error for ${message.type}:`, error);
          }
        });
      }

      // Call handlers for 'all' message types
      const allHandlers = this.messageHandlers.get('all');
      if (allHandlers) {
        allHandlers.forEach(handler => {
          try {
            handler(message);
          } catch (error) {
            console.error('❌ Universal message handler error:', error);
          }
        });
      }

    } catch (error) {
      console.error('❌ Failed to parse WebSocket message:', error);
    }
  }

  /**
   * Start heartbeat to keep connection alive
   */
  private startHeartbeat() {
    this.stopHeartbeat();
    
    this.heartbeatInterval = setInterval(() => {
      if (this.isConnected()) {
        this.sendCommand('ping');
      }
    }, this.config.heartbeatInterval);
  }

  /**
   * Stop heartbeat
   */
  private stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  /**
   * Attempt to reconnect with exponential backoff
   */
  private attemptReconnect() {
    if (this.state.reconnectAttempts >= this.config.reconnectAttempts) {
      console.log('❌ Max reconnection attempts reached');
      this.updateState({ error: 'Max reconnection attempts reached' });
      return;
    }

    const delay = Math.min(
      this.config.reconnectDelay * Math.pow(2, this.state.reconnectAttempts),
      this.config.maxReconnectDelay
    );

    console.log(`🔄 Attempting reconnection in ${delay}ms (attempt ${this.state.reconnectAttempts + 1})`);
    
    this.updateState({ 
      reconnectAttempts: this.state.reconnectAttempts + 1 
    });

    this.reconnectTimeout = setTimeout(() => {
      this.connect().catch(error => {
        console.error('❌ Reconnection failed:', error);
      });
    }, delay);
  }

  /**
   * Update state and notify handlers
   */
  private updateState(partialState: Partial<VoiceWebSocketState>) {
    this.state = { ...this.state, ...partialState };
    
    this.stateChangeHandlers.forEach(handler => {
      try {
        handler(this.state);
      } catch (error) {
        console.error('❌ State change handler error:', error);
      }
    });
  }

  /**
   * Destroy client and clean up resources
   */
  destroy() {
    this.disconnect();
    this.messageHandlers.clear();
    this.stateChangeHandlers.length = 0;
    console.log('🗑️ VoiceWebSocketClient destroyed');
  }
}

/**
 * Factory function to create VoiceWebSocketClient
 */
export function createVoiceWebSocketClient(
  sessionId: string, 
  baseUrl?: string, 
  config?: VoiceWebSocketConfig
): VoiceWebSocketClient {
  return new VoiceWebSocketClient(sessionId, baseUrl, config);
}