/**
 * Basic Reception Test
 * 最もシンプルなReceptionテスト
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

// 必要最小限のモック
jest.mock('@/lib/api', () => ({
  apiClient: {
    healthCheck: jest.fn(() => Promise.resolve({ status: 'ok' })),
    startConversation: jest.fn(() => Promise.resolve({ 
      success: true, 
      session_id: 'test-123' 
    }))
  }
}), { virtual: true });

jest.mock('@/hooks/useVoiceChat', () => ({
  useVoiceChat: jest.fn(() => ({
    state: {
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
      error: null,
      visitorInfo: null,
      calendarResult: null,
      isListening: false
    },
    messages: [],
    startVoiceChat: jest.fn(),
    stopVoiceChat: jest.fn(),
    startRecording: jest.fn(),
    forceStopRecording: jest.fn(),
    resetError: jest.fn(),
    sendTextInput: jest.fn()
  }))
}), { virtual: true });

jest.mock('@/components/VoiceInterface', () => {
  return function MockVoiceInterface() {
    return <div data-testid="voice-interface">Mock Voice Interface</div>;
  };
}, { virtual: true });

import ReceptionPage from '@/app/reception/page';

describe('Basic Reception Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('初期画面が表示される', () => {
    render(<ReceptionPage />);
    
    // 基本的な要素が表示されることを確認
    expect(screen.getByText('いらっしゃいませ')).toBeInTheDocument();
    expect(screen.getByText('受付開始')).toBeInTheDocument();
  });

  test('システム説明が表示される', () => {
    render(<ReceptionPage />);
    
    // 説明文の確認
    expect(screen.getByText(/こちらは音声対話受付システムです/)).toBeInTheDocument();
    expect(screen.getByText(/下のボタンを押して音声受付を開始してください/)).toBeInTheDocument();
  });

  test('利用方法の説明が表示される', () => {
    render(<ReceptionPage />);
    
    // ご利用方法セクションの確認
    expect(screen.getByText('ご利用方法')).toBeInTheDocument();
    expect(screen.getByText(/「受付開始」ボタンを押す/)).toBeInTheDocument();
    expect(screen.getByText(/お名前と会社名を音声で話す/)).toBeInTheDocument();
    expect(screen.getByText(/AIが音声で適切にご案内/)).toBeInTheDocument();
  });
});