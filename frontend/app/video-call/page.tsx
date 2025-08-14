'use client';

import { useEffect, useState, useRef, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import VideoCallInterface from '@/components/VideoCallInterface';

interface VideoRoomData {
  room_name: string;
  access_token: string;
  room_url: string;
  visitor_identity: string;
  expires_at: string;
}

function VideoCallContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  
  // State
  const [roomData, setRoomData] = useState<VideoRoomData | null>(null);
  // Fixed names for visitor and staff
  const VISITOR_NAME = 'ゲスト';
  const STAFF_NAME = 'スタッフ';
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stage, setStage] = useState<'form' | 'creating' | 'connected' | 'ending'>('form');
  const [countdown, setCountdown] = useState(5);
  const [isStaffJoining, setIsStaffJoining] = useState(false);
  const [existingRoomName, setExistingRoomName] = useState<string | null>(null);
  
  // Refs for cleanup
  const countdownIntervalRef = useRef<NodeJS.Timeout | null>(null);
  
  // Get room parameter from URL
  const getRoomFromURL = (): string | null => {
    const roomParam = searchParams.get('room');
    return roomParam && roomParam.trim() ? roomParam.trim() : null;
  };

  // Check if we already have a room from URL params (staff joining existing room)
  useEffect(() => {
    const roomName = getRoomFromURL();
    
    if (roomName) {
      // Staff member clicking Slack link to join existing room
      setIsStaffJoining(true);
      setExistingRoomName(roomName);
      setStage('form'); // Show form for staff to enter their name
    } else {
      setIsStaffJoining(false);
      setExistingRoomName(null);
    }
  }, [searchParams]);
  
  // Cleanup countdown on unmount
  useEffect(() => {
    return () => {
      if (countdownIntervalRef.current) {
        clearInterval(countdownIntervalRef.current);
      }
    };
  }, []);
  
  // Handle button click to create video room or join existing room as staff
  const handleJoinRoom = async () => {
    
    const roomFromURL = getRoomFromURL();
    const shouldJoinExisting = Boolean(roomFromURL);
    
    // Defensive state correction
    if (shouldJoinExisting !== isStaffJoining) {
      setIsStaffJoining(shouldJoinExisting);
      setExistingRoomName(roomFromURL);
    }
    
    setIsLoading(true);
    setError(null);
    setStage('creating');
    
    try {
      if (shouldJoinExisting && roomFromURL) {
        // Staff joining existing room
        const response = await fetch('/api/video/staff-token', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            room_name: roomFromURL,  // Use room from URL directly
            staff_name: STAFF_NAME
          }),
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'スタッフトークンの生成に失敗しました');
        }
        
        const staffTokenData = await response.json();
        
        // Create room data structure for staff joining existing room
        const currentUrl = typeof window !== 'undefined' 
          ? window.location.href 
          : `/video-call?room=${roomFromURL}`;
          
        const data: VideoRoomData = {
          room_name: roomFromURL,  // Use room from URL directly
          access_token: staffTokenData.access_token,
          room_url: currentUrl,
          visitor_identity: staffTokenData.identity,
          expires_at: new Date(Date.now() + 3600000).toISOString() // 1 hour from now
        };
        
        setRoomData(data);
        setStage('connected');
        
      } else {
        // Visitor creating new room
        const response = await fetch('/api/video/create-room', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            visitor_name: VISITOR_NAME,
            purpose: 'video_reception'
          }),
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'ビデオルームの作成に失敗しました');
        }
        
        const data: VideoRoomData = await response.json();
        setRoomData(data);
        setStage('connected');
      }
      
    } catch (err) {
      console.error('Error creating/joining video room:', err);
      const errorMessage = err instanceof Error ? err.message : 
        (isStaffJoining ? 'ビデオルームへの参加に失敗しました' : 'ビデオルームの作成に失敗しました');
      setError(errorMessage);
      setStage('form');
    } finally {
      setIsLoading(false);
    }
  };
  
  // Handle call end
  const handleCallEnd = () => {
    setStage('ending');
    setCountdown(5);
    
    // Start countdown
    countdownIntervalRef.current = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          if (countdownIntervalRef.current) {
            clearInterval(countdownIntervalRef.current);
          }
          router.push('/');
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };
  
  // Handle error from video component
  const handleVideoError = (errorMessage: string) => {
    setError(errorMessage);
  };
  
  // Render join screen
  const renderJoinScreen = () => (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-6">
        {/* Header */}
        <div className="text-center mb-6">
          <div className={`w-16 h-16 ${isStaffJoining ? 'bg-green-100' : 'bg-blue-100'} rounded-full flex items-center justify-center mx-auto mb-4`}>
            <svg className={`w-8 h-8 ${isStaffJoining ? 'text-green-600' : 'text-blue-600'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {isStaffJoining ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
              )}
            </svg>
          </div>
          
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            {isStaffJoining ? 'ビデオ通話に参加' : 'ビデオ通話で受付'}
          </h1>
          
          <p className="text-gray-600">
            {isStaffJoining 
              ? `ルーム「${existingRoomName}」に${STAFF_NAME}として参加します` 
              : `${VISITOR_NAME}としてビデオ通話を開始します`
            }
          </p>
        </div>
        
        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
            <p className="text-red-700 text-sm">{error}</p>
          </div>
        )}
        
        {/* Join Button */}
        <div className="space-y-3">
          <button
            onClick={handleJoinRoom}
            disabled={isLoading}
            className={`w-full ${isStaffJoining ? 'bg-green-600 hover:bg-green-700' : 'bg-blue-600 hover:bg-blue-700'} text-white py-4 px-6 rounded-lg disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors font-medium text-lg`}
          >
            {isLoading 
              ? (isStaffJoining ? 'ビデオルーム参加中...' : 'ビデオルーム作成中...') 
              : (isStaffJoining ? 'ビデオ通話に参加' : 'ビデオ通話を開始')
            }
          </button>
          
          <button
            onClick={() => router.push('/')}
            disabled={isLoading}
            className="w-full bg-gray-600 text-white py-3 px-4 rounded-lg hover:bg-gray-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            戻る
          </button>
        </div>
        
        {/* Info */}
        <div className={`mt-6 p-4 ${isStaffJoining ? 'bg-green-50' : 'bg-blue-50'} rounded-lg`}>
          <div className="flex items-start space-x-3">
            <svg className={`w-5 h-5 ${isStaffJoining ? 'text-green-600' : 'text-blue-600'} mt-0.5`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <h3 className={`text-sm font-medium ${isStaffJoining ? 'text-green-900' : 'text-blue-900'} mb-1`}>
                {isStaffJoining ? 'スタッフの方へ' : 'ご利用にあたって'}
              </h3>
              <ul className={`text-xs ${isStaffJoining ? 'text-green-800' : 'text-blue-800'} space-y-1`}>
                <li>• カメラとマイクの許可が必要です</li>
                {isStaffJoining ? (
                  <>
                    <li>• 来訪者が既に待機している可能性があります</li>
                    <li>• 参加後、適切に対応をお願いします</li>
                  </>
                ) : (
                  <>
                    <li>• スタッフが参加するまでお待ちください</li>
                    <li>• 最大2名まで参加可能です</li>
                  </>
                )}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
  
  // Render creating room screen
  const renderCreating = () => (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-6 text-center">
        <div className={`w-16 h-16 ${isStaffJoining ? 'bg-green-100' : 'bg-blue-100'} rounded-full flex items-center justify-center mx-auto mb-4 animate-pulse`}>
          <svg className={`w-8 h-8 ${isStaffJoining ? 'text-green-600' : 'text-blue-600'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            {isStaffJoining ? (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            )}
          </svg>
        </div>
        
        <h2 className="text-xl font-semibold text-gray-900 mb-2">
          {isStaffJoining ? 'ビデオルームに参加中...' : 'ビデオルームを作成中...'}
        </h2>
        
        <p className="text-gray-600 mb-4">
          {isStaffJoining 
            ? `ルーム「${existingRoomName}」に接続しています` 
            : 'Slackでスタッフに通知しています'
          }
        </p>
        
        <div className={`animate-spin rounded-full h-8 w-8 border-b-2 ${isStaffJoining ? 'border-green-600' : 'border-blue-600'} mx-auto`}></div>
      </div>
    </div>
  );
  
  // Render ending screen with countdown
  const renderEnding = () => (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-6 text-center">
        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        
        <h2 className="text-xl font-semibold text-gray-900 mb-2">
          ビデオ通話を終了しました
        </h2>
        
        <p className="text-gray-600 mb-4">
          ご利用ありがとうございました
        </p>
        
        <div className="text-3xl font-bold text-blue-600 mb-4">
          {countdown}
        </div>
        
        <p className="text-sm text-gray-500">
          {countdown}秒後にホーム画面に戻ります
        </p>
        
        <button
          onClick={() => router.push('/')}
          className="mt-4 w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 transition-colors"
        >
          今すぐ戻る
        </button>
      </div>
    </div>
  );
  
  // Main render
  switch (stage) {
    case 'form':
      return renderJoinScreen();
      
    case 'creating':
      return renderCreating();
      
    case 'connected':
      if (!roomData) {
        return renderJoinScreen();
      }
      return (
        <VideoCallInterface
          roomName={roomData.room_name}
          accessToken={roomData.access_token}
          onCallEnd={handleCallEnd}
          onError={handleVideoError}
          autoConnect={true}
        />
      );
      
    case 'ending':
      return renderEnding();
      
    default:
      return renderJoinScreen();
  }
}

export default function VideoCallPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-6 text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">読み込み中...</p>
        </div>
      </div>
    }>
      <VideoCallContent />
    </Suspense>
  );
}