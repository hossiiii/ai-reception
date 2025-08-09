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
import { 
  ConnectionState,
  ConnectionStateInfo, 
  createConnectionError 
} from '@/types/voice';

export interface UseVoiceConnectionOptions {
  sessionId: string;
  autoConnect?: boolean;
}

export interface UseVoiceConnectionReturn {
  // State
  state: ConnectionStateInfo;
  
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
  const [state, setState] = useState<ConnectionStateInfo>({
    state: 'disconnected',
    error: null,
    sessionId,
    isReconnecting: false,
    reconnectAttempts: 0
  });
  
  // Update state helper
  const updateState = useCallback((updates: Partial<ConnectionStateInfo>) => {
    setState(prev => ({ ...prev, ...updates }));
  }, []);
  
  // Initialize WebSocket client
  useEffect(() => {
    console.log(`🔌 Initializing WebSocket client for session: ${sessionId}`);
    
    // Create WebSocket client
    wsClient.current = createVoiceWebSocketClient(sessionId);
    
    // Setup state change handler
    const handleStateChange = (wsState: any) => {
      let newState: ConnectionState;
      if (wsState.connected) {
        newState = 'connected';
      } else if (wsState.connecting) {
        newState = 'connecting';
      } else if (wsState.error) {
        newState = 'error';
      } else {
        newState = 'disconnected';
      }
      
      const error = wsState.error ? createConnectionError(wsState.error, 'WEBSOCKET_FAILED') : null;
      
      updateState({
        state: newState,
        error
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
      const error = createConnectionError('WebSocket client not initialized', 'WEBSOCKET_FAILED');
      updateState({ error });
      return false;
    }
    
    if (state.state === 'connected') {
      console.log('🔌 Already connected to WebSocket');
      return true;
    }
    
    try {
      updateState({ 
        state: 'connecting', 
        error: null,
        reconnectAttempts: (state.reconnectAttempts || 0) + 1
      });
      
      const connected = await wsClient.current.connect();
      if (connected) {
        console.log('✅ WebSocket connected successfully');
        return true;
      } else {
        const error = createConnectionError('Failed to connect to voice service', 'WEBSOCKET_FAILED');
        updateState({ 
          state: 'error',
          error
        });
        return false;
      }
    } catch (error) {
      console.error('❌ WebSocket connection error:', error);
      const voiceError = createConnectionError(
        error instanceof Error ? error.message : 'Failed to connect to voice service',
        'NETWORK_ERROR'
      );
      updateState({ 
        state: 'error',
        error: voiceError
      });
      return false;
    }
  }, [state.state, state.reconnectAttempts, updateState]);
  
  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    if (wsClient.current) {
      wsClient.current.disconnect();
    }
    
    updateState({
      state: 'disconnected',
      error: null,
      isReconnecting: false
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
    if (autoConnect && state.state === 'disconnected') {
      connect();
    }
  }, [autoConnect, state.state, connect]);
  
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