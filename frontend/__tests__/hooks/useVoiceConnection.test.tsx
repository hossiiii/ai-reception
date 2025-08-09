/**
 * Unit tests for useVoiceConnection hook
 */

import { renderHook, act } from '@testing-library/react';
import { useVoiceConnection } from '@/hooks/useVoiceConnection';
import { EnhancedMockWebSocket, setupWebSocketMock } from '../mocks/websocket';

describe('useVoiceConnection', () => {
  const { getWebSocketInstance } = setupWebSocketMock();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('初期状態', () => {
    it('初期状態が正しく設定される', () => {
      const { result } = renderHook(() => 
        useVoiceConnection({ sessionId: 'test-session' })
      );

      expect(result.current.state).toEqual({
        state: 'disconnected',
        error: null,
        sessionId: 'test-session',
        isReconnecting: false,
        reconnectAttempts: 0
      });
      expect(result.current.client).toBeNull();
    });

    it('autoConnectがtrueの場合、自動接続を試みる', async () => {
      renderHook(() => 
        useVoiceConnection({ 
          sessionId: 'test-session',
          autoConnect: true 
        })
      );

      // WebSocketインスタンスが作成される
      const ws = getWebSocketInstance();
      expect(ws).toBeDefined();
      expect(ws?.url).toContain('test-session');
    });
  });

  describe('接続管理', () => {
    it('connect()でWebSocket接続を開始する', async () => {
      const { result } = renderHook(() => 
        useVoiceConnection({ sessionId: 'test-session' })
      );

      let connectResult: boolean = false;
      await act(async () => {
        connectResult = await result.current.connect();
      });

      const ws = getWebSocketInstance();
      expect(ws).toBeDefined();
      expect(ws?.readyState).toBe(EnhancedMockWebSocket.OPEN);
      expect(connectResult).toBe(true);
    });

    it('disconnect()で接続を切断する', async () => {
      const { result } = renderHook(() => 
        useVoiceConnection({ sessionId: 'test-session' })
      );

      // 接続
      await act(async () => {
        await result.current.connect();
      });

      const ws = getWebSocketInstance();
      
      // 切断
      act(() => {
        result.current.disconnect();
      });

      expect(ws?.readyState).toBe(EnhancedMockWebSocket.CLOSED);
      expect(result.current.state.state).toBe('disconnected');
    });

    it('接続エラーを適切にハンドリングする', async () => {
      const { result } = renderHook(() => 
        useVoiceConnection({ sessionId: 'test-session' })
      );

      await act(async () => {
        await result.current.connect();
      });

      const ws = getWebSocketInstance() as EnhancedMockWebSocket;
      
      // エラーをシミュレート
      act(() => {
        ws.mockError('Connection failed');
      });

      // エラー発生時は 'error' 状態になる
      expect(result.current.state.state).toBe('error');
      expect(result.current.state.error).toBeDefined();
    });
  });

  describe('再接続ロジック', () => {
    it.skip('接続が切れた場合、自動的に再接続を試みる', async () => {
      // TODO: 再接続ロジックのテストを実装
    });

    it.skip('最大再接続回数に達したらエラー状態になる', async () => {
      // TODO: 最大再接続回数のテストを実装
    });
  });

  describe('クリーンアップ', () => {
    it('アンマウント時にWebSocket接続をクリーンアップする', async () => {
      const { result, unmount } = renderHook(() => 
        useVoiceConnection({ sessionId: 'test-session' })
      );

      await act(async () => {
        await result.current.connect();
      });

      const ws = getWebSocketInstance() as EnhancedMockWebSocket;
      
      unmount();

      expect(ws.readyState).toBe(EnhancedMockWebSocket.CLOSED);
    });
  });
});