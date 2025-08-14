'use client';

import { useEffect, useRef, useState } from 'react';
import { useVideoCall } from '@/hooks/useVideoCall';

export interface VideoCallInterfaceProps {
  roomName: string;
  accessToken: string;
  onCallEnd?: () => void;
  onError?: (error: string) => void;
  autoConnect?: boolean;
}

export default function VideoCallInterface({
  roomName,
  accessToken,
  onCallEnd,
  onError,
  autoConnect = true
}: VideoCallInterfaceProps) {
  // Refs for video elements
  const localVideoRef = useRef<HTMLVideoElement>(null);
  const remoteVideoRef = useRef<HTMLVideoElement>(null);
  
  // Component state
  const [showEndCallConfirm, setShowEndCallConfirm] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [permissionGranted, setPermissionGranted] = useState(false);
  const [permissionError, setPermissionError] = useState<string | null>(null);
  
  // Video call hook
  const {
    state,
    connect,
    disconnect,
    toggleAudio,
    toggleVideo,
    attachLocalVideo,
    detachLocalVideo,
    attachRemoteVideo,
    detachRemoteVideo
  } = useVideoCall({
    roomName,
    accessToken,
    autoConnect: false  // We'll handle connection manually after permissions
  });
  
  // Request camera and microphone permissions
  useEffect(() => {
    const requestPermissions = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: true
        });
        
        // Stop the stream immediately as we just need permissions
        stream.getTracks().forEach(track => track.stop());
        
        setPermissionGranted(true);
        setPermissionError(null);
      } catch (error) {
        console.error('Permission denied:', error);
        setPermissionError('カメラとマイクの許可が必要です。ブラウザの設定を確認してください。');
        setPermissionGranted(false);
        
        if (onError) {
          onError('カメラとマイクの許可が必要です');
        }
      }
    };
    
    requestPermissions();
  }, [onError]);
  
  // Auto-connect when permissions are granted
  useEffect(() => {
    if (permissionGranted && autoConnect && state.status === 'disconnected') {
      connect();
    }
  }, [permissionGranted, autoConnect, state.status, connect]);
  
  // Handle video attachment when participants change
  useEffect(() => {
    if (state.status === 'connected' && localVideoRef.current) {
      attachLocalVideo(localVideoRef.current);
    }
    
    return () => {
      if (localVideoRef.current) {
        detachLocalVideo(localVideoRef.current);
      }
    };
  }, [state.status, state.localParticipant, attachLocalVideo, detachLocalVideo]);
  
  // Handle remote video attachment
  useEffect(() => {
    console.log(`🔄 Remote participants changed: ${state.remoteParticipants.size} participants`);
    
    if (state.remoteParticipants.size > 0 && remoteVideoRef.current) {
      const firstRemoteParticipant = Array.from(state.remoteParticipants.values())[0];
      console.log(`🎬 Attaching video for first remote participant: ${firstRemoteParticipant.identity}`);
      attachRemoteVideo(firstRemoteParticipant.sid, remoteVideoRef.current);
    } else if (state.remoteParticipants.size === 0) {
      console.log(`👻 No remote participants to attach`);
    } else if (!remoteVideoRef.current) {
      console.log(`❌ Remote video element not available`);
    }
    
    return () => {
      if (state.remoteParticipants.size > 0 && remoteVideoRef.current) {
        const firstRemoteParticipant = Array.from(state.remoteParticipants.values())[0];
        console.log(`🔌 Detaching video for: ${firstRemoteParticipant.identity}`);
        detachRemoteVideo(firstRemoteParticipant.sid, remoteVideoRef.current);
      }
    };
  }, [state.remoteParticipants, attachRemoteVideo, detachRemoteVideo]);
  
  // Additional effect to try attachment after a delay (for race conditions)
  useEffect(() => {
    if (state.remoteParticipants.size > 0 && remoteVideoRef.current) {
      const timer = setTimeout(() => {
        const firstRemoteParticipant = Array.from(state.remoteParticipants.values())[0];
        console.log(`⏰ Delayed attachment attempt for: ${firstRemoteParticipant.identity}`);
        attachRemoteVideo(firstRemoteParticipant.sid, remoteVideoRef.current!);
      }, 1000); // Wait 1 second for tracks to be fully ready
      
      return () => clearTimeout(timer);
    }
    return undefined;
  }, [state.remoteParticipants, attachRemoteVideo]);
  
  // Handle errors
  useEffect(() => {
    if (state.error && onError) {
      onError(state.error);
    }
  }, [state.error, onError]);
  
  // Handle call end with countdown
  const handleEndCall = () => {
    setShowEndCallConfirm(true);
    setCountdown(5);
    
    const countdownInterval = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          clearInterval(countdownInterval);
          disconnect();
          if (onCallEnd) {
            onCallEnd();
          }
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };
  
  // Cancel end call
  const cancelEndCall = () => {
    setShowEndCallConfirm(false);
    setCountdown(0);
  };
  
  // Force end call immediately
  const forceEndCall = () => {
    disconnect();
    if (onCallEnd) {
      onCallEnd();
    }
  };
  
  // Render permission request screen
  if (!permissionGranted) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-6 text-center">
          <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
          </div>
          
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            カメラとマイクの許可が必要です
          </h2>
          
          {permissionError ? (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
              <p className="text-red-700 text-sm">{permissionError}</p>
            </div>
          ) : (
            <p className="text-gray-600 mb-4">
              ビデオ通話を開始するために、カメラとマイクへのアクセスを許可してください。
            </p>
          )}
          
          <button
            onClick={() => window.location.reload()}
            className="w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 transition-colors"
          >
            再試行
          </button>
        </div>
      </div>
    );
  }
  
  // Render connecting screen
  if (state.status === 'connecting') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-6 text-center">
          <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4 animate-pulse">
            <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
          </div>
          
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            ビデオ通話に接続中...
          </h2>
          
          <p className="text-gray-600">
            しばらくお待ちください
          </p>
        </div>
      </div>
    );
  }
  
  // Render error screen
  if (state.status === 'error') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-6 text-center">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            接続エラー
          </h2>
          
          <p className="text-gray-600 mb-4">
            {state.error || 'ビデオ通話の接続に失敗しました'}
          </p>
          
          <div className="space-y-2">
            <button
              onClick={connect}
              className="w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 transition-colors"
            >
              再接続
            </button>
            
            <button
              onClick={onCallEnd}
              className="w-full bg-gray-600 text-white py-2 px-4 rounded-lg hover:bg-gray-700 transition-colors"
            >
              戻る
            </button>
          </div>
        </div>
      </div>
    );
  }
  
  // Render main video call interface
  return (
    <div className="min-h-screen bg-gray-900 relative">
      {/* Video Grid */}
      <div className="absolute inset-0 grid grid-cols-1 lg:grid-cols-2 gap-4 p-4">
        {/* Local Video */}
        <div className="relative bg-gray-800 rounded-lg overflow-hidden">
          <video
            ref={localVideoRef}
            autoPlay
            muted
            playsInline
            className="w-full h-full object-cover"
          />
          
          <div className="absolute top-4 left-4 bg-black bg-opacity-50 rounded-lg px-3 py-1">
            <span className="text-white text-sm">あなた</span>
          </div>
          
          {state.isVideoMuted && (
            <div className="absolute inset-0 bg-gray-800 flex items-center justify-center">
              <div className="text-white text-center">
                <svg className="w-12 h-12 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                <p className="text-sm">カメラがオフです</p>
              </div>
            </div>
          )}
        </div>
        
        {/* Remote Video */}
        <div className="relative bg-gray-800 rounded-lg overflow-hidden">
          {state.participantCount > 1 ? (
            <>
              <video
                ref={remoteVideoRef}
                autoPlay
                playsInline
                className="w-full h-full object-cover"
              />
              
              <div className="absolute top-4 left-4 bg-black bg-opacity-50 rounded-lg px-3 py-1">
                <span className="text-white text-sm">
                  {Array.from(state.remoteParticipants.values())[0]?.identity || 'スタッフ'}
                </span>
              </div>
            </>
          ) : (
            <div className="flex items-center justify-center h-full text-white text-center">
              <div>
                <svg className="w-16 h-16 mx-auto mb-4 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                <p className="text-lg font-medium mb-2">スタッフの参加をお待ちしています</p>
                {state.localParticipant?.sid === 'mock-local-participant' ? (
                  <p className="text-sm text-gray-400">開発モード: Slackで通知済みです</p>
                ) : (
                  <p className="text-sm text-gray-400">Slackで通知済みです</p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
      
      {/* Controls */}
      <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2">
        <div className="flex items-center space-x-4 bg-black bg-opacity-50 rounded-full px-6 py-4">
          {/* Mute Audio */}
          <button
            onClick={toggleAudio}
            className={`p-3 rounded-full transition-colors ${
              state.isAudioMuted
                ? 'bg-red-600 hover:bg-red-700 text-white'
                : 'bg-gray-600 hover:bg-gray-700 text-white'
            }`}
            title={state.isAudioMuted ? 'マイクをオンにする' : 'マイクをオフにする'}
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {state.isAudioMuted ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
              )}
            </svg>
          </button>
          
          {/* Mute Video */}
          <button
            onClick={toggleVideo}
            className={`p-3 rounded-full transition-colors ${
              state.isVideoMuted
                ? 'bg-red-600 hover:bg-red-700 text-white'
                : 'bg-gray-600 hover:bg-gray-700 text-white'
            }`}
            title={state.isVideoMuted ? 'カメラをオンにする' : 'カメラをオフにする'}
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {state.isVideoMuted ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728L5.636 5.636m12.728 12.728L18.364 5.636M5.636 18.364l12.728-12.728" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
              )}
            </svg>
          </button>
          
          {/* End Call */}
          <button
            onClick={handleEndCall}
            className="p-3 rounded-full bg-red-600 hover:bg-red-700 text-white transition-colors"
            title="通話を終了"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 8l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2M3 3l1.5 1.5M3 3l1.5 1.5M3 3l18 18" />
            </svg>
          </button>
        </div>
      </div>
      
      {/* Participant Count */}
      <div className="absolute top-4 right-4 bg-black bg-opacity-50 rounded-lg px-3 py-1">
        <span className="text-white text-sm">
          参加者: {state.participantCount}/2
        </span>
      </div>
      
      {/* End Call Confirmation Modal */}
      {showEndCallConfirm && (
        <div className="absolute inset-0 bg-black bg-opacity-75 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg p-6 max-w-sm w-full text-center">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              通話を終了しますか？
            </h3>
            
            <p className="text-gray-600 mb-6">
              {countdown > 0 ? (
                <>あと {countdown} 秒でホーム画面に戻ります</>
              ) : (
                'ホーム画面に戻ります'
              )}
            </p>
            
            <div className="flex space-x-4">
              <button
                onClick={cancelEndCall}
                className="flex-1 bg-gray-600 text-white py-2 px-4 rounded-lg hover:bg-gray-700 transition-colors"
                disabled={countdown === 0}
              >
                キャンセル
              </button>
              
              <button
                onClick={forceEndCall}
                className="flex-1 bg-red-600 text-white py-2 px-4 rounded-lg hover:bg-red-700 transition-colors"
              >
                終了
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}