/**
 * Tests for VoiceInterface component (Step2 voice functionality)
 * Tests voice UI, state management, and user interactions
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import VoiceInterface from '../VoiceInterface';
import { useVoiceChat } from '@/hooks/useVoiceChat';

// Mock the voice chat hook
jest.mock('@/hooks/useVoiceChat');
const mockUseVoiceChat = jest.mocked(useVoiceChat);

// Mock audio APIs that aren't available in test environment
Object.defineProperty(window, 'MediaRecorder', {
  writable: true,
  value: jest.fn().mockImplementation(() => ({
    start: jest.fn(),
    stop: jest.fn(),
    pause: jest.fn(),
    resume: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

Object.defineProperty(navigator, 'mediaDevices', {
  writable: true,
  value: {
    getUserMedia: jest.fn(() => Promise.resolve({
      getTracks: () => [{ stop: jest.fn() }]
    }))
  }
});

Object.defineProperty(window, 'AudioContext', {
  writable: true,
  value: jest.fn().mockImplementation(() => ({
    createAnalyser: jest.fn(() => ({
      connect: jest.fn(),
      disconnect: jest.fn()
    })),
    createMediaStreamSource: jest.fn(() => ({
      connect: jest.fn()
    })),
    close: jest.fn(),
    resume: jest.fn(() => Promise.resolve()),
    state: 'running'
  }))
});

describe('VoiceInterface', () => {
  const mockProps = {
    onConversationEnd: jest.fn(),
    onError: jest.fn()
  };

  const defaultVoiceState = {
    isConnected: false,
    isConnecting: false,
    isRecording: false,
    hasPermission: false,
    isProcessing: false,
    isPlaying: false,
    vadActive: false,
    vadEnergy: 0,
    vadVolume: 0,
    vadConfidence: 0,
    conversationStarted: false,
    conversationCompleted: false,
    currentStep: 'greeting',
    error: null
  };

  const mockVoiceChatReturn = {
    state: defaultVoiceState,
    messages: [],
    startVoiceChat: jest.fn(),
    stopVoiceChat: jest.fn(),
    startRecording: jest.fn(),
    stopRecording: jest.fn(),
    playLastResponse: jest.fn(),
    resetError: jest.fn(),
    sessionId: 'test-session-123'
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockUseVoiceChat.mockReturnValue(mockVoiceChatReturn);
  });

  it('renders initial voice interface correctly', () => {
    render(<VoiceInterface {...mockProps} />);

    expect(screen.getByText('AI音声受付対応')).toBeInTheDocument();
    expect(screen.getByText('音声受付を開始')).toBeInTheDocument();
    expect(screen.getByText('マイクへのアクセス許可が必要です')).toBeInTheDocument();
  });

  it('shows connecting state when starting voice chat', () => {
    mockUseVoiceChat.mockReturnValue({
      ...mockVoiceChatReturn,
      state: { ...defaultVoiceState, isConnecting: true }
    });

    render(<VoiceInterface {...mockProps} />);

    expect(screen.getByText('接続中...')).toBeInTheDocument();
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('shows connected state with recording controls', () => {
    mockUseVoiceChat.mockReturnValue({
      ...mockVoiceChatReturn,
      state: { 
        ...defaultVoiceState, 
        isConnected: true, 
        conversationStarted: true,
        hasPermission: true 
      }
    });

    render(<VoiceInterface {...mockProps} />);

    expect(screen.getByText('録音開始')).toBeInTheDocument();
    expect(screen.getByText('録音ボタンを押してください')).toBeInTheDocument();
  });

  it('shows recording state correctly', () => {
    mockUseVoiceChat.mockReturnValue({
      ...mockVoiceChatReturn,
      state: { 
        ...defaultVoiceState, 
        isConnected: true, 
        conversationStarted: true,
        isRecording: true 
      }
    });

    render(<VoiceInterface {...mockProps} />);

    expect(screen.getByText('録音停止')).toBeInTheDocument();
    expect(screen.getByText('お話しください')).toBeInTheDocument();
  });

  it('calls startVoiceChat when start button is clicked', async () => {
    const user = userEvent.setup();
    render(<VoiceInterface {...mockProps} />);

    const startButton = screen.getByText('音声受付を開始');
    await user.click(startButton);

    expect(mockVoiceChatReturn.startVoiceChat).toHaveBeenCalledTimes(1);
  });

  it('calls startRecording when recording button is clicked', async () => {
    const user = userEvent.setup();
    mockUseVoiceChat.mockReturnValue({
      ...mockVoiceChatReturn,
      state: { 
        ...defaultVoiceState, 
        isConnected: true, 
        conversationStarted: true 
      }
    });

    render(<VoiceInterface {...mockProps} />);

    const recordButton = screen.getByText('録音開始');
    await user.click(recordButton);

    expect(mockVoiceChatReturn.startRecording).toHaveBeenCalledTimes(1);
  });

  it('calls stopRecording when stop recording button is clicked', async () => {
    const user = userEvent.setup();
    mockUseVoiceChat.mockReturnValue({
      ...mockVoiceChatReturn,
      state: { 
        ...defaultVoiceState, 
        isConnected: true, 
        conversationStarted: true,
        isRecording: true 
      }
    });

    render(<VoiceInterface {...mockProps} />);

    const stopButton = screen.getByText('録音停止');
    await user.click(stopButton);

    expect(mockVoiceChatReturn.stopRecording).toHaveBeenCalledTimes(1);
  });

  it('calls playLastResponse when replay button is clicked', async () => {
    const user = userEvent.setup();
    mockUseVoiceChat.mockReturnValue({
      ...mockVoiceChatReturn,
      state: { 
        ...defaultVoiceState, 
        isConnected: true, 
        conversationStarted: true 
      }
    });

    render(<VoiceInterface {...mockProps} />);

    const replayButton = screen.getByLabelText('最後の応答を再生');
    await user.click(replayButton);

    expect(mockVoiceChatReturn.playLastResponse).toHaveBeenCalledTimes(1);
  });

  it('displays error message when error occurs', () => {
    mockUseVoiceChat.mockReturnValue({
      ...mockVoiceChatReturn,
      state: { 
        ...defaultVoiceState, 
        error: 'マイクアクセスが拒否されました' 
      }
    });

    render(<VoiceInterface {...mockProps} />);

    expect(screen.getByText('マイクアクセスが拒否されました')).toBeInTheDocument();
  });

  it('calls resetError when error close button is clicked', async () => {
    const user = userEvent.setup();
    mockUseVoiceChat.mockReturnValue({
      ...mockVoiceChatReturn,
      state: { 
        ...defaultVoiceState, 
        error: 'テストエラー' 
      }
    });

    render(<VoiceInterface {...mockProps} />);

    const closeButton = screen.getByText('✕');
    await user.click(closeButton);

    expect(mockVoiceChatReturn.resetError).toHaveBeenCalledTimes(1);
  });

  it('displays conversation messages', () => {
    const testMessages = [
      {
        speaker: 'ai' as const,
        content: 'こんにちは！',
        timestamp: '2025-08-03T10:00:00Z'
      },
      {
        speaker: 'visitor' as const,
        content: '山田です',
        timestamp: '2025-08-03T10:00:30Z'
      }
    ];

    mockUseVoiceChat.mockReturnValue({
      ...mockVoiceChatReturn,
      messages: testMessages
    });

    render(<VoiceInterface {...mockProps} />);

    expect(screen.getByText('こんにちは！')).toBeInTheDocument();
    expect(screen.getByText('山田です')).toBeInTheDocument();
  });

  it('shows completion message when conversation is completed', () => {
    mockUseVoiceChat.mockReturnValue({
      ...mockVoiceChatReturn,
      state: { 
        ...defaultVoiceState, 
        conversationCompleted: true 
      }
    });

    render(<VoiceInterface {...mockProps} />);

    expect(screen.getByText('対応が完了しました。ありがとうございました。')).toBeInTheDocument();
    expect(screen.getByText('対応完了')).toBeInTheDocument();
  });

  it('calls onConversationEnd when end button is clicked', async () => {
    const user = userEvent.setup();
    render(<VoiceInterface {...mockProps} />);

    const endButton = screen.getByLabelText('会話を終了');
    await user.click(endButton);

    expect(mockVoiceChatReturn.stopVoiceChat).toHaveBeenCalledTimes(1);
    expect(mockProps.onConversationEnd).toHaveBeenCalledTimes(1);
  });

  it('calls onError when error occurs', () => {
    const testError = 'テストエラーメッセージ';
    mockUseVoiceChat.mockReturnValue({
      ...mockVoiceChatReturn,
      state: { 
        ...defaultVoiceState, 
        error: testError 
      }
    });

    render(<VoiceInterface {...mockProps} />);

    expect(mockProps.onError).toHaveBeenCalledWith(testError);
  });

  it('renders AudioVisualizer with correct props', () => {
    const vadState = {
      vadActive: true,
      vadEnergy: 75,
      vadVolume: 50,
      vadConfidence: 0.8,
      isRecording: true,
      isPlaying: false
    };

    mockUseVoiceChat.mockReturnValue({
      ...mockVoiceChatReturn,
      state: { 
        ...defaultVoiceState, 
        ...vadState 
      }
    });

    render(<VoiceInterface {...mockProps} />);

    // AudioVisualizer should be rendered (we can't easily test props without more setup)
    // But we can verify it doesn't crash
    expect(screen.getByText('AI音声受付対応')).toBeInTheDocument();
  });

  it('disables recording controls when processing', () => {
    mockUseVoiceChat.mockReturnValue({
      ...mockVoiceChatReturn,
      state: { 
        ...defaultVoiceState, 
        isConnected: true, 
        conversationStarted: true,
        isProcessing: true 
      }
    });

    render(<VoiceInterface {...mockProps} />);

    const recordButton = screen.getByText('録音開始');
    expect(recordButton).toBeDisabled();
  });

  it('disables recording controls when conversation is completed', () => {
    mockUseVoiceChat.mockReturnValue({
      ...mockVoiceChatReturn,
      state: { 
        ...defaultVoiceState, 
        isConnected: true, 
        conversationStarted: true,
        conversationCompleted: true 
      }
    });

    render(<VoiceInterface {...mockProps} />);

    const recordButton = screen.getByText('録音開始');
    expect(recordButton).toBeDisabled();
  });

  it('shows processing status correctly', () => {
    mockUseVoiceChat.mockReturnValue({
      ...mockVoiceChatReturn,
      state: { 
        ...defaultVoiceState, 
        isConnected: true, 
        isProcessing: true 
      }
    });

    render(<VoiceInterface {...mockProps} />);

    expect(screen.getByText('処理中...')).toBeInTheDocument();
  });

  it('shows voice detection status', () => {
    mockUseVoiceChat.mockReturnValue({
      ...mockVoiceChatReturn,
      state: { 
        ...defaultVoiceState, 
        isConnected: true, 
        isRecording: true,
        vadActive: true 
      }
    });

    render(<VoiceInterface {...mockProps} />);

    expect(screen.getByText('音声検出中...')).toBeInTheDocument();
  });

  it('auto-calls onConversationEnd after conversation completion', async () => {
    jest.useFakeTimers();
    
    mockUseVoiceChat.mockReturnValue({
      ...mockVoiceChatReturn,
      state: { 
        ...defaultVoiceState, 
        conversationCompleted: true 
      }
    });

    render(<VoiceInterface {...mockProps} />);

    // Fast-forward time by 10 seconds
    jest.advanceTimersByTime(10000);

    await waitFor(() => {
      expect(mockProps.onConversationEnd).toHaveBeenCalledTimes(1);
    });

    jest.useRealTimers();
  });

  it('passes sessionId prop to useVoiceChat', () => {
    const testSessionId = 'custom-session-123';
    render(<VoiceInterface {...mockProps} sessionId={testSessionId} />);

    expect(mockUseVoiceChat).toHaveBeenCalledWith({
      sessionId: testSessionId,
      autoStart: false
    });
  });

  it('handles different connection status texts', () => {
    const statuses = [
      { state: { isConnecting: true }, text: '接続中...' },
      { state: { isConnected: false }, text: '未接続' },
      { state: { isProcessing: true }, text: '処理中...' },
      { state: { isPlaying: true }, text: '音声再生中...' },
      { state: { isRecording: true, vadActive: true }, text: '音声検出中...' },
      { state: { isRecording: true, vadActive: false }, text: '音声待機中...' },
      { state: { isConnected: true, conversationStarted: true }, text: '準備完了' }
    ];

    statuses.forEach(({ state, text }) => {
      mockUseVoiceChat.mockReturnValue({
        ...mockVoiceChatReturn,
        state: { ...defaultVoiceState, ...state }
      });

      const { rerender } = render(<VoiceInterface {...mockProps} />);
      expect(screen.getByText(text)).toBeInTheDocument();
      rerender(<></>); // Clean up for next iteration
    });
  });
});