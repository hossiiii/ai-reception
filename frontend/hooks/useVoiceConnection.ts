/**
 * Voice WebSocket connection management hook
 * Handles connection state, reconnection, and message routing
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { 
  VoiceWebSocketClient, 
  VoiceMessage as WSVoiceMessage, 
  createVoiceWebSocketClient 
} from '@/lib/websocket';

export interface ConnectionState {
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;
}

export interface UseVoiceConnectionOptions {
  sessionId: string;
  autoConnect?: boolean;
}

export interface UseVoiceConnectionReturn {
  // State
  state: ConnectionState;
  
  // Actions
  connect: () => Promise<boolean>;
  disconnect: () => void;
  
  // WebSocket client access
  client: VoiceWebSocketClient | null;
  
  // Message handlers
  addMessageHandler: (type: string, handler: (message: WSVoiceMessage) => void) => void;
  removeMessageHandler: (type: string, handler: (message: WSVoiceMessage) => void) => void;
  addStateChangeHandler: (handler: (state: any) => void) => void;
  removeStateChangeHandler: (handler: (state: any) => void) => void;
}

export function useVoiceConnection(options: UseVoiceConnectionOptions): UseVoiceConnectionReturn {
  const { sessionId, autoConnect = false } = options;
  
  // WebSocket client instance
  const wsClient = useRef<VoiceWebSocketClient | null>(null);
  
  // Connection state
  const [state, setState] = useState<ConnectionState>({
    isConnected: false,
    isConnecting: false,
    error: null
  });
  
  // Update state helper
  const updateState = useCallback((updates: Partial<ConnectionState>) => {
    setState(prev => ({ ...prev, ...updates }));
  }, []);
  
  // Initialize WebSocket client
  useEffect(() => {
    console.log(`🔌 Initializing WebSocket client for session: ${sessionId}`);
    
    // Create WebSocket client
    wsClient.current = createVoiceWebSocketClient(sessionId);
    
    // Setup state change handler
    const handleStateChange = (wsState: any) => {
      updateState({
        isConnected: wsState.connected,
        isConnecting: wsState.connecting,
        error: wsState.error || null
      });
    };
    
    wsClient.current.addStateChangeHandler(handleStateChange);
    
    return () => {
      // Cleanup on unmount
      if (wsClient.current) {
        wsClient.current.removeStateChangeHandler(handleStateChange);
        wsClient.current.destroy();
        wsClient.current = null;
      }
    };
  }, [sessionId, updateState]);
  
  // Connect to WebSocket
  const connect = useCallback(async (): Promise<boolean> => {
    if (!wsClient.current) {
      updateState({ error: 'WebSocket client not initialized' });
      return false;
    }
    
    if (state.isConnected) {
      console.log('🔌 Already connected to WebSocket');
      return true;
    }
    
    try {
      updateState({ isConnecting: true, error: null });
      
      const connected = await wsClient.current.connect();
      if (connected) {
        console.log('✅ WebSocket connected successfully');
        return true;
      } else {
        updateState({ 
          error: 'Failed to connect to voice service',
          isConnecting: false
        });
        return false;
      }
    } catch (error) {
      console.error('❌ WebSocket connection error:', error);
      updateState({ 
        error: error instanceof Error ? error.message : 'Failed to connect to voice service',
        isConnecting: false
      });
      return false;
    }
  }, [state.isConnected, updateState]);
  
  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    if (wsClient.current) {
      wsClient.current.disconnect();
    }
    
    updateState({
      isConnected: false,
      isConnecting: false,
      error: null
    });
    
    console.log('🔌 WebSocket disconnected');
  }, [updateState]);
  
  // Add message handler
  const addMessageHandler = useCallback((type: string, handler: (message: WSVoiceMessage) => void) => {
    if (wsClient.current) {
      wsClient.current.addMessageHandler(type, handler);
    }
  }, []);
  
  // Remove message handler
  const removeMessageHandler = useCallback((type: string, handler: (message: WSVoiceMessage) => void) => {
    if (wsClient.current) {
      wsClient.current.removeMessageHandler(type, handler);
    }
  }, []);
  
  // Add state change handler
  const addStateChangeHandler = useCallback((handler: (state: any) => void) => {
    if (wsClient.current) {
      wsClient.current.addStateChangeHandler(handler);
    }
  }, []);
  
  // Remove state change handler
  const removeStateChangeHandler = useCallback((handler: (state: any) => void) => {
    if (wsClient.current) {
      wsClient.current.removeStateChangeHandler(handler);
    }
  }, []);
  
  // Auto-connect if requested
  useEffect(() => {
    if (autoConnect && !state.isConnected && !state.isConnecting) {
      connect();
    }
  }, [autoConnect, state.isConnected, state.isConnecting, connect]);
  
  return {
    state,
    connect,
    disconnect,
    client: wsClient.current,
    addMessageHandler,
    removeMessageHandler,
    addStateChangeHandler,
    removeStateChangeHandler
  };
}