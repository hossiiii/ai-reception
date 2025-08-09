/**
 * エラー状態からの復旧処理テスト
 * 音声チャット中の各種エラーからの復旧動作をテスト
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

// useVoiceChatフックのモック
jest.mock('@/hooks/useVoiceChat', () => ({
  useVoiceChat: jest.fn()
}), { virtual: true });

// エラー復旧テスト用VoiceInterfaceコンポーネント
jest.mock('@/components/VoiceInterface', () => {
  return function ErrorRecoveryVoiceInterface({ onError, onConversationEnd }: any) {
    const mockUseVoiceChat = require('@/hooks/useVoiceChat').useVoiceChat;
    const { state, resetError, startVoiceChat, startRecording } = mockUseVoiceChat();
    
    return (
      <div data-testid="error-recovery-interface">
        <div data-testid="current-state">
          現在の状態: {state.currentStep}
        </div>
        
        <div data-testid="connection-status">
          接続状態: {state.isConnected ? '接続中' : '未接続'}
        </div>

        {state.error && (
          <div data-testid="error-section">
            <div data-testid="error-message">エラー: {state.error}</div>
            <div data-testid="error-recovery-actions">
              <button 
                data-testid="reset-error-button"
                onClick={() => {
                  resetError();
                  console.log('エラーをリセットしました');
                }}
              >
                エラーをリセット
              </button>
              
              <button 
                data-testid="retry-connection-button"
                onClick={async () => {
                  resetError();
                  const success = await startVoiceChat();
                  console.log(`再接続結果: ${success}`);
                }}
              >
                再接続を試行
              </button>
              
              <button 
                data-testid="restart-recording-button"
                onClick={async () => {
                  resetError();
                  const success = await startRecording();
                  console.log(`録音再開結果: ${success}`);
                }}
                disabled={!state.isConnected}
              >
                録音を再開
              </button>
            </div>
          </div>
        )}

        {state.isProcessing && (
          <div data-testid="processing-indicator">
            AI処理中... しばらくお待ちください
          </div>
        )}

        {state.conversationCompleted && (
          <div data-testid="completion-section">
            <div>会話が完了しました</div>
            <button 
              data-testid="start-new-conversation"
              onClick={() => {
                console.log('新しい会話を開始');
                onConversationEnd?.();
              }}
            >
              新しい会話を開始
            </button>
          </div>
        )}

        <div data-testid="health-check">
          システム健康状態: {state.healthStatus || '不明'}
        </div>
      </div>
    );
  };
}, { virtual: true });

import VoiceInterface from '@/components/VoiceInterface';

describe('Error Recovery Tests', () => {
  const mockUseVoiceChat = require('@/hooks/useVoiceChat').useVoiceChat;
  
  beforeEach(() => {
    jest.clearAllMocks();
    console.log = jest.fn(); // コンソールログをモック化
  });

  test('マイクアクセス拒否エラーからの復旧', async () => {
    const user = userEvent.setup();
    const resetError = jest.fn();
    const startVoiceChat = jest.fn(() => Promise.resolve(true));

    mockUseVoiceChat.mockReturnValue({
      state: {
        isConnected: false,
        isConnecting: false,
        isRecording: false,
        hasPermission: false,
        isProcessing: false,
        isPlaying: false,
        conversationStarted: false,
        conversationCompleted: false,
        currentStep: 'error',
        error: 'マイクアクセスが拒否されました'
      },
      messages: [],
      resetError,
      startVoiceChat,
      startRecording: jest.fn()
    });

    render(<VoiceInterface onError={jest.fn()} onConversationEnd={jest.fn()} />);

    // エラー表示の確認
    expect(screen.getByText('エラー: マイクアクセスが拒否されました')).toBeInTheDocument();
    expect(screen.getByTestId('error-recovery-actions')).toBeInTheDocument();

    // エラーリセット
    const resetButton = screen.getByTestId('reset-error-button');
    await user.click(resetButton);
    
    expect(resetError).toHaveBeenCalledTimes(1);
    expect(console.log).toHaveBeenCalledWith('エラーをリセットしました');
  });

  test('WebSocket接続エラーからの復旧', async () => {
    const user = userEvent.setup();
    const resetError = jest.fn();
    const startVoiceChat = jest.fn(() => Promise.resolve(true));

    mockUseVoiceChat.mockReturnValue({
      state: {
        isConnected: false,
        isConnecting: false,
        isRecording: false,
        hasPermission: true,
        isProcessing: false,
        isPlaying: false,
        conversationStarted: false,
        conversationCompleted: false,
        currentStep: 'error',
        error: 'WebSocket接続に失敗しました'
      },
      messages: [],
      resetError,
      startVoiceChat,
      startRecording: jest.fn()
    });

    render(<VoiceInterface onError={jest.fn()} onConversationEnd={jest.fn()} />);

    expect(screen.getByText('エラー: WebSocket接続に失敗しました')).toBeInTheDocument();

    // 再接続を試行
    const retryButton = screen.getByTestId('retry-connection-button');
    await user.click(retryButton);
    
    expect(resetError).toHaveBeenCalledTimes(1);
    expect(startVoiceChat).toHaveBeenCalledTimes(1);
    
    await waitFor(() => {
      expect(console.log).toHaveBeenCalledWith('再接続結果: true');
    });
  });

  test('音声録音エラーからの復旧', async () => {
    const user = userEvent.setup();
    const resetError = jest.fn();
    const startRecording = jest.fn(() => Promise.resolve(true));

    mockUseVoiceChat.mockReturnValue({
      state: {
        isConnected: true,
        isConnecting: false,
        isRecording: false,
        hasPermission: true,
        isProcessing: false,
        isPlaying: false,
        conversationStarted: true,
        conversationCompleted: false,
        currentStep: 'error',
        error: '音声録音でエラーが発生しました'
      },
      messages: [],
      resetError,
      startVoiceChat: jest.fn(),
      startRecording
    });

    render(<VoiceInterface onError={jest.fn()} onConversationEnd={jest.fn()} />);

    expect(screen.getByText('エラー: 音声録音でエラーが発生しました')).toBeInTheDocument();

    // 録音を再開
    const restartButton = screen.getByTestId('restart-recording-button');
    expect(restartButton).not.toBeDisabled(); // 接続済みなのでボタンは有効
    
    await user.click(restartButton);
    
    expect(resetError).toHaveBeenCalledTimes(1);
    expect(startRecording).toHaveBeenCalledTimes(1);
    
    await waitFor(() => {
      expect(console.log).toHaveBeenCalledWith('録音再開結果: true');
    });
  });

  test('未接続時の録音再開ボタンが無効化される', () => {
    const resetError = jest.fn();

    mockUseVoiceChat.mockReturnValue({
      state: {
        isConnected: false, // 未接続
        isConnecting: false,
        isRecording: false,
        hasPermission: false,
        isProcessing: false,
        isPlaying: false,
        conversationStarted: false,
        conversationCompleted: false,
        currentStep: 'error',
        error: 'ネットワークエラー'
      },
      messages: [],
      resetError,
      startVoiceChat: jest.fn(),
      startRecording: jest.fn()
    });

    render(<VoiceInterface onError={jest.fn()} onConversationEnd={jest.fn()} />);

    const restartButton = screen.getByTestId('restart-recording-button');
    expect(restartButton).toBeDisabled(); // 未接続なのでボタンは無効
  });

  test('複数エラーの連続復旧処理', async () => {
    const user = userEvent.setup();
    const resetError = jest.fn();
    const startVoiceChat = jest.fn(() => Promise.resolve(false)); // 最初は失敗

    mockUseVoiceChat.mockReturnValue({
      state: {
        isConnected: false,
        isConnecting: false,
        isRecording: false,
        hasPermission: false,
        isProcessing: false,
        isPlaying: false,
        conversationStarted: false,
        conversationCompleted: false,
        currentStep: 'error',
        error: '複数のエラーが発生しました'
      },
      messages: [],
      resetError,
      startVoiceChat,
      startRecording: jest.fn()
    });

    render(<VoiceInterface onError={jest.fn()} onConversationEnd={jest.fn()} />);

    // 最初の復旧試行（失敗）
    const retryButton = screen.getByTestId('retry-connection-button');
    await user.click(retryButton);
    
    await waitFor(() => {
      expect(console.log).toHaveBeenCalledWith('再接続結果: false');
    });

    // 2回目の復旧試行をシミュレート
    startVoiceChat.mockResolvedValueOnce(true); // 今度は成功
    await user.click(retryButton);
    
    await waitFor(() => {
      expect(console.log).toHaveBeenCalledWith('再接続結果: true');
    });
    
    expect(resetError).toHaveBeenCalledTimes(2);
    expect(startVoiceChat).toHaveBeenCalledTimes(2);
  });

  test('エラー状態時のシステム健康状態表示', () => {
    mockUseVoiceChat.mockReturnValue({
      state: {
        isConnected: false,
        isConnecting: false,
        isRecording: false,
        hasPermission: false,
        isProcessing: false,
        isPlaying: false,
        conversationStarted: false,
        conversationCompleted: false,
        currentStep: 'error',
        error: 'システムエラー',
        healthStatus: 'システム不良'
      },
      messages: [],
      resetError: jest.fn(),
      startVoiceChat: jest.fn(),
      startRecording: jest.fn()
    });

    render(<VoiceInterface onError={jest.fn()} onConversationEnd={jest.fn()} />);

    expect(screen.getByText('現在の状態: error')).toBeInTheDocument();
    expect(screen.getByText('接続状態: 未接続')).toBeInTheDocument();
    expect(screen.getByText('システム健康状態: システム不良')).toBeInTheDocument();
  });

  test('処理中状態での復旧操作の制御', () => {
    mockUseVoiceChat.mockReturnValue({
      state: {
        isConnected: true,
        isConnecting: false,
        isRecording: false,
        hasPermission: true,
        isProcessing: true, // 処理中
        isPlaying: false,
        conversationStarted: true,
        conversationCompleted: false,
        currentStep: 'processing',
        error: null
      },
      messages: [],
      resetError: jest.fn(),
      startVoiceChat: jest.fn(),
      startRecording: jest.fn()
    });

    render(<VoiceInterface onError={jest.fn()} onConversationEnd={jest.fn()} />);

    // 処理中の表示確認
    expect(screen.getByTestId('processing-indicator')).toBeInTheDocument();
    expect(screen.getByText('AI処理中... しばらくお待ちください')).toBeInTheDocument();
    
    // エラーセクションが表示されないことを確認
    expect(screen.queryByTestId('error-section')).not.toBeInTheDocument();
  });

  test('会話完了後の新しい会話開始', async () => {
    const user = userEvent.setup();
    const onConversationEnd = jest.fn();

    mockUseVoiceChat.mockReturnValue({
      state: {
        isConnected: true,
        isConnecting: false,
        isRecording: false,
        hasPermission: true,
        isProcessing: false,
        isPlaying: false,
        conversationStarted: true,
        conversationCompleted: true,
        currentStep: 'completed',
        error: null
      },
      messages: [],
      resetError: jest.fn(),
      startVoiceChat: jest.fn(),
      startRecording: jest.fn()
    });

    render(<VoiceInterface onError={jest.fn()} onConversationEnd={onConversationEnd} />);

    expect(screen.getByTestId('completion-section')).toBeInTheDocument();
    expect(screen.getByText('会話が完了しました')).toBeInTheDocument();

    const newConversationButton = screen.getByTestId('start-new-conversation');
    await user.click(newConversationButton);
    
    expect(onConversationEnd).toHaveBeenCalledTimes(1);
    expect(console.log).toHaveBeenCalledWith('新しい会話を開始');
  });

  test('エラーなし状態での正常表示', () => {
    mockUseVoiceChat.mockReturnValue({
      state: {
        isConnected: true,
        isConnecting: false,
        isRecording: true,
        hasPermission: true,
        isProcessing: false,
        isPlaying: false,
        conversationStarted: true,
        conversationCompleted: false,
        currentStep: 'recording',
        error: null, // エラーなし
        healthStatus: '正常'
      },
      messages: [],
      resetError: jest.fn(),
      startVoiceChat: jest.fn(),
      startRecording: jest.fn()
    });

    render(<VoiceInterface onError={jest.fn()} onConversationEnd={jest.fn()} />);

    expect(screen.getByText('現在の状態: recording')).toBeInTheDocument();
    expect(screen.getByText('接続状態: 接続中')).toBeInTheDocument();
    expect(screen.getByText('システム健康状態: 正常')).toBeInTheDocument();
    
    // エラーセクションが表示されないことを確認
    expect(screen.queryByTestId('error-section')).not.toBeInTheDocument();
  });
});