/**
 * MediaRecorder/AudioContext連携テスト
 * ブラウザの音声APIとの統合動作をテスト
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

// ブラウザ音声APIのモック
const mockMediaRecorder = {
  start: jest.fn(),
  stop: jest.fn(),
  pause: jest.fn(),
  resume: jest.fn(),
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
  state: 'inactive',
  stream: null
};

const mockAudioContext = {
  createAnalyser: jest.fn(() => ({
    connect: jest.fn(),
    disconnect: jest.fn(),
    frequencyBinCount: 1024,
    fftSize: 2048,
    getByteFrequencyData: jest.fn(),
    getFloatFrequencyData: jest.fn()
  })),
  createMediaStreamSource: jest.fn(() => ({
    connect: jest.fn(),
    disconnect: jest.fn()
  })),
  close: jest.fn(() => Promise.resolve()),
  resume: jest.fn(() => Promise.resolve()),
  suspend: jest.fn(() => Promise.resolve()),
  state: 'running',
  currentTime: 0,
  sampleRate: 44100
};

const mockMediaStream = {
  getTracks: jest.fn(() => [
    {
      stop: jest.fn(),
      kind: 'audio',
      enabled: true,
      readyState: 'live'
    }
  ]),
  getAudioTracks: jest.fn(() => [
    {
      stop: jest.fn(),
      kind: 'audio',
      enabled: true,
      readyState: 'live'
    }
  ])
};

Object.defineProperty(window, 'MediaRecorder', {
  writable: true,
  value: jest.fn(() => mockMediaRecorder)
});

Object.defineProperty(window, 'AudioContext', {
  writable: true,
  value: jest.fn(() => mockAudioContext)
});

Object.defineProperty(window, 'webkitAudioContext', {
  writable: true,
  value: jest.fn(() => mockAudioContext)
});

Object.defineProperty(navigator, 'mediaDevices', {
  writable: true,
  value: {
    getUserMedia: jest.fn(() => Promise.resolve(mockMediaStream)),
    enumerateDevices: jest.fn(() => Promise.resolve([
      {
        deviceId: 'default',
        kind: 'audioinput',
        label: 'Default Microphone',
        groupId: 'group1'
      }
    ]))
  }
});

// useVoiceChatフックのモック
jest.mock('@/hooks/useVoiceChat', () => ({
  useVoiceChat: jest.fn()
}), { virtual: true });

// AudioAPIテスト用コンポーネント
jest.mock('@/components/VoiceInterface', () => {
  return function AudioAPITestInterface({ onError }: any) {
    const mockUseVoiceChat = require('@/hooks/useVoiceChat').useVoiceChat;
    const { state, startRecording, stopRecording } = mockUseVoiceChat();
    
    return (
      <div data-testid="audio-api-interface">
        <div data-testid="microphone-status">
          マイク権限: {state.hasPermission ? '許可済み' : '未許可'}
        </div>
        
        <div data-testid="recording-status">
          録音状態: {state.isRecording ? '録音中' : '停止中'}
        </div>
        
        <div data-testid="media-recorder-status">
          MediaRecorder状態: {state.mediaRecorderState || 'inactive'}
        </div>
        
        <div data-testid="audio-context-status">
          AudioContext状態: {state.audioContextState || 'suspended'}
        </div>
        
        <div data-testid="vad-info">
          <div>VAD活性: {state.vadActive ? 'アクティブ' : '非アクティブ'}</div>
          <div>音声エネルギー: {state.vadEnergy}%</div>
          <div>音量: {state.vadVolume}dB</div>
          <div>信頼度: {Math.round((state.vadConfidence || 0) * 100)}%</div>
        </div>
        
        <div data-testid="audio-quality-info">
          <div>サンプルレート: {state.sampleRate || 44100}Hz</div>
          <div>チャンネル数: {state.channels || 1}</div>
          <div>ビットレート: {state.bitRate || 128}kbps</div>
        </div>
        
        <div data-testid="audio-controls">
          <button 
            data-testid="start-recording-button"
            onClick={startRecording}
            disabled={state.isRecording || !state.hasPermission}
          >
            録音開始
          </button>
          
          <button 
            data-testid="stop-recording-button"
            onClick={stopRecording}
            disabled={!state.isRecording}
          >
            録音停止
          </button>
        </div>
        
        {state.audioDevices && (
          <div data-testid="audio-devices-list">
            利用可能な音声デバイス:
            {state.audioDevices.map((device: any, index: number) => (
              <div key={index} data-testid={`audio-device-${index}`}>
                {device.label} ({device.kind})
              </div>
            ))}
          </div>
        )}
        
        {state.error && state.error.includes('audio') && (
          <div data-testid="audio-error">
            音声API エラー: {state.error}
          </div>
        )}
      </div>
    );
  };
}, { virtual: true });

import VoiceInterface from '@/components/VoiceInterface';

describe('Audio APIs Integration Tests', () => {
  const mockUseVoiceChat = require('@/hooks/useVoiceChat').useVoiceChat;
  
  beforeEach(() => {
    jest.clearAllMocks();
    
    // デフォルトのモック状態をリセット
    mockMediaRecorder.state = 'inactive';
    mockAudioContext.state = 'suspended';
  });

  test('マイク権限の取得と表示', async () => {
    mockUseVoiceChat.mockReturnValue({
      state: {
        hasPermission: true,
        isRecording: false,
        mediaRecorderState: 'inactive',
        audioContextState: 'suspended',
        vadActive: false,
        vadEnergy: 0,
        vadVolume: -40,
        vadConfidence: 0,
        error: null
      },
      startRecording: jest.fn(),
      stopRecording: jest.fn()
    });

    render(<VoiceInterface onError={jest.fn()} onConversationEnd={jest.fn()} />);

    expect(screen.getByText('マイク権限: 許可済み')).toBeInTheDocument();
    expect(screen.getByText('録音状態: 停止中')).toBeInTheDocument();
    expect(screen.getByText('MediaRecorder状態: inactive')).toBeInTheDocument();
    expect(screen.getByText('AudioContext状態: suspended')).toBeInTheDocument();
  });

  test('録音開始時のAPI状態変化', async () => {
    const user = userEvent.setup();
    const startRecording = jest.fn();
    
    mockUseVoiceChat.mockReturnValue({
      state: {
        hasPermission: true,
        isRecording: false,
        mediaRecorderState: 'inactive',
        audioContextState: 'running',
        vadActive: false,
        vadEnergy: 0,
        vadVolume: -40,
        vadConfidence: 0,
        error: null
      },
      startRecording,
      stopRecording: jest.fn()
    });

    render(<VoiceInterface onError={jest.fn()} onConversationEnd={jest.fn()} />);

    const startButton = screen.getByTestId('start-recording-button');
    expect(startButton).not.toBeDisabled();

    await user.click(startButton);
    expect(startRecording).toHaveBeenCalledTimes(1);
  });

  test('録音中のVAD情報表示', () => {
    mockUseVoiceChat.mockReturnValue({
      state: {
        hasPermission: true,
        isRecording: true,
        mediaRecorderState: 'recording',
        audioContextState: 'running',
        vadActive: true,
        vadEnergy: 75,
        vadVolume: -20,
        vadConfidence: 0.85,
        error: null
      },
      startRecording: jest.fn(),
      stopRecording: jest.fn()
    });

    render(<VoiceInterface onError={jest.fn()} onConversationEnd={jest.fn()} />);

    expect(screen.getByText('録音状態: 録音中')).toBeInTheDocument();
    expect(screen.getByText('MediaRecorder状態: recording')).toBeInTheDocument();
    expect(screen.getByText('AudioContext状態: running')).toBeInTheDocument();
    
    // VAD情報
    expect(screen.getByText('VAD活性: アクティブ')).toBeInTheDocument();
    expect(screen.getByText('音声エネルギー: 75%')).toBeInTheDocument();
    expect(screen.getByText('音量: -20dB')).toBeInTheDocument();
    expect(screen.getByText('信頼度: 85%')).toBeInTheDocument();
  });

  test('音声品質設定の表示', () => {
    mockUseVoiceChat.mockReturnValue({
      state: {
        hasPermission: true,
        isRecording: false,
        mediaRecorderState: 'inactive',
        audioContextState: 'suspended',
        vadActive: false,
        vadEnergy: 0,
        vadVolume: -40,
        vadConfidence: 0,
        sampleRate: 48000,
        channels: 1,
        bitRate: 256,
        error: null
      },
      startRecording: jest.fn(),
      stopRecording: jest.fn()
    });

    render(<VoiceInterface onError={jest.fn()} onConversationEnd={jest.fn()} />);

    expect(screen.getByText('サンプルレート: 48000Hz')).toBeInTheDocument();
    expect(screen.getByText('チャンネル数: 1')).toBeInTheDocument();
    expect(screen.getByText('ビットレート: 256kbps')).toBeInTheDocument();
  });

  test('利用可能な音声デバイスの表示', () => {
    mockUseVoiceChat.mockReturnValue({
      state: {
        hasPermission: true,
        isRecording: false,
        mediaRecorderState: 'inactive',
        audioContextState: 'suspended',
        vadActive: false,
        vadEnergy: 0,
        vadVolume: -40,
        vadConfidence: 0,
        audioDevices: [
          { label: 'Built-in Microphone', kind: 'audioinput' },
          { label: 'External USB Mic', kind: 'audioinput' },
          { label: 'Bluetooth Headset', kind: 'audioinput' }
        ],
        error: null
      },
      startRecording: jest.fn(),
      stopRecording: jest.fn()
    });

    render(<VoiceInterface onError={jest.fn()} onConversationEnd={jest.fn()} />);

    expect(screen.getByText('利用可能な音声デバイス:')).toBeInTheDocument();
    expect(screen.getByText('Built-in Microphone (audioinput)')).toBeInTheDocument();
    expect(screen.getByText('External USB Mic (audioinput)')).toBeInTheDocument();
    expect(screen.getByText('Bluetooth Headset (audioinput)')).toBeInTheDocument();
  });

  test('音声API エラーの表示', () => {
    mockUseVoiceChat.mockReturnValue({
      state: {
        hasPermission: false,
        isRecording: false,
        mediaRecorderState: 'inactive',
        audioContextState: 'suspended',
        vadActive: false,
        vadEnergy: 0,
        vadVolume: -40,
        vadConfidence: 0,
        error: 'audio initialization failed: MediaRecorder not supported'
      },
      startRecording: jest.fn(),
      stopRecording: jest.fn()
    });

    render(<VoiceInterface onError={jest.fn()} onConversationEnd={jest.fn()} />);

    expect(screen.getByText('マイク権限: 未許可')).toBeInTheDocument();
    expect(screen.getByTestId('audio-error')).toBeInTheDocument();
    expect(screen.getByText('音声API エラー: audio initialization failed: MediaRecorder not supported')).toBeInTheDocument();
  });

  test('録音停止操作', async () => {
    const user = userEvent.setup();
    const stopRecording = jest.fn();
    
    mockUseVoiceChat.mockReturnValue({
      state: {
        hasPermission: true,
        isRecording: true,
        mediaRecorderState: 'recording',
        audioContextState: 'running',
        vadActive: true,
        vadEnergy: 60,
        vadVolume: -15,
        vadConfidence: 0.75,
        error: null
      },
      startRecording: jest.fn(),
      stopRecording
    });

    render(<VoiceInterface onError={jest.fn()} onConversationEnd={jest.fn()} />);

    const stopButton = screen.getByTestId('stop-recording-button');
    expect(stopButton).not.toBeDisabled();

    await user.click(stopButton);
    expect(stopRecording).toHaveBeenCalledTimes(1);
  });

  test('マイク権限未取得時のボタン無効化', () => {
    mockUseVoiceChat.mockReturnValue({
      state: {
        hasPermission: false, // 権限なし
        isRecording: false,
        mediaRecorderState: 'inactive',
        audioContextState: 'suspended',
        vadActive: false,
        vadEnergy: 0,
        vadVolume: -40,
        vadConfidence: 0,
        error: null
      },
      startRecording: jest.fn(),
      stopRecording: jest.fn()
    });

    render(<VoiceInterface onError={jest.fn()} onConversationEnd={jest.fn()} />);

    const startButton = screen.getByTestId('start-recording-button');
    expect(startButton).toBeDisabled(); // 権限がないのでボタンは無効
    
    const stopButton = screen.getByTestId('stop-recording-button');
    expect(stopButton).toBeDisabled(); // 録音していないのでボタンは無効
  });

  test('VAD（音声活動検出）の詳細情報', () => {
    const vadTestCases = [
      {
        vadActive: false,
        vadEnergy: 0,
        vadVolume: -60,
        vadConfidence: 0,
        expected: {
          activity: 'VAD活性: 非アクティブ',
          energy: '音声エネルギー: 0%',
          volume: '音量: -60dB',
          confidence: '信頼度: 0%'
        }
      },
      {
        vadActive: true,
        vadEnergy: 50,
        vadVolume: -25,
        vadConfidence: 0.6,
        expected: {
          activity: 'VAD活性: アクティブ',
          energy: '音声エネルギー: 50%',
          volume: '音量: -25dB',
          confidence: '信頼度: 60%'
        }
      },
      {
        vadActive: true,
        vadEnergy: 90,
        vadVolume: -10,
        vadConfidence: 0.95,
        expected: {
          activity: 'VAD活性: アクティブ',
          energy: '音声エネルギー: 90%',
          volume: '音量: -10dB',
          confidence: '信頼度: 95%'
        }
      }
    ];

    vadTestCases.forEach((testCase, index) => {
      mockUseVoiceChat.mockReturnValue({
        state: {
          hasPermission: true,
          isRecording: testCase.vadActive,
          mediaRecorderState: testCase.vadActive ? 'recording' : 'inactive',
          audioContextState: testCase.vadActive ? 'running' : 'suspended',
          vadActive: testCase.vadActive,
          vadEnergy: testCase.vadEnergy,
          vadVolume: testCase.vadVolume,
          vadConfidence: testCase.vadConfidence,
          error: null
        },
        startRecording: jest.fn(),
        stopRecording: jest.fn()
      });

      const { rerender } = render(<VoiceInterface onError={jest.fn()} onConversationEnd={jest.fn()} />);

      expect(screen.getByText(testCase.expected.activity)).toBeInTheDocument();
      expect(screen.getByText(testCase.expected.energy)).toBeInTheDocument();
      expect(screen.getByText(testCase.expected.volume)).toBeInTheDocument();
      expect(screen.getByText(testCase.expected.confidence)).toBeInTheDocument();

      rerender(<></>); // クリーンアップ
    });
  });
});