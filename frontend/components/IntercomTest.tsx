// Test component for the video intercom integration

'use client';

import React, { useState, useRef } from 'react';
import { VideoMonitor } from './VideoMonitor';
import VideoCallInterface from './VideoCallInterface';
import { useVideoIntercom } from '@/hooks/useVideoIntercom';

export const IntercomTest: React.FC = () => {
  const [visitorName, setVisitorName] = useState('');
  const [purpose, setPurpose] = useState('');
  const [staffName, setStaffName] = useState('');
  const [joinRoomName, setJoinRoomName] = useState('');
  const [testMode, setTestMode] = useState<'visitor' | 'staff'>('visitor');
  
  // Local refs for VideoMonitor integration
  const localVideoRef = useRef<HTMLVideoElement | null>(null);
  const remoteVideoRef = useRef<HTMLVideoElement | null>(null);

  const {
    isLoading,
    callStatus,
    currentRoomName,
    currentAccessToken,
    setVideoRefs,
    startVisitorCall,
    joinStaffCall,
    endCurrentCall,
  } = useVideoIntercom({
    onCallStarted: (roomName) => {
      console.log('Call started:', roomName);
    },
    onCallEnded: () => {
      console.log('Call ended');
    },
    onError: (error) => {
      console.error('Call error:', error);
      alert(`通話エラー: ${error}`);
    }
  });

  const handleStartVisitorCall = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!visitorName.trim()) {
      alert('お名前を入力してください');
      return;
    }
    await startVisitorCall(visitorName, purpose || undefined);
  };

  const handleJoinStaffCall = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!joinRoomName.trim()) {
      alert('ルーム名を入力してください');
      return;
    }
    await joinStaffCall(joinRoomName, staffName || undefined);
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-8">
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h1 className="text-2xl font-bold text-gray-800 mb-6">ビデオインターコムテスト</h1>
        
        {/* Mode selector */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            テストモード
          </label>
          <div className="flex space-x-4">
            <label className="flex items-center">
              <input
                type="radio"
                name="mode"
                value="visitor"
                checked={testMode === 'visitor'}
                onChange={(e) => setTestMode(e.target.value as 'visitor')}
                className="mr-2"
              />
              来客者 (新しい通話を開始)
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                name="mode"
                value="staff"
                checked={testMode === 'staff'}
                onChange={(e) => setTestMode(e.target.value as 'staff')}
                className="mr-2"
              />
              スタッフ (既存の通話に参加)
            </label>
          </div>
        </div>

        {testMode === 'visitor' ? (
          <form onSubmit={handleStartVisitorCall} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                お名前 *
              </label>
              <input
                type="text"
                value={visitorName}
                onChange={(e) => setVisitorName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="田中太郎"
                disabled={isLoading || callStatus !== 'idle'}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                用件
              </label>
              <input
                type="text"
                value={purpose}
                onChange={(e) => setPurpose(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="アポイントメント"
                disabled={isLoading || callStatus !== 'idle'}
              />
            </div>
            <button
              type="submit"
              disabled={isLoading || callStatus !== 'idle'}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white px-6 py-2 rounded-md font-medium transition-colors"
            >
              {isLoading ? '接続中...' : '通話を開始'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleJoinStaffCall} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                ルーム名 *
              </label>
              <input
                type="text"
                value={joinRoomName}
                onChange={(e) => setJoinRoomName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="reception-abc123"
                disabled={isLoading || callStatus !== 'idle'}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                スタッフ名
              </label>
              <input
                type="text"
                value={staffName}
                onChange={(e) => setStaffName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Staff"
                disabled={isLoading || callStatus !== 'idle'}
              />
            </div>
            <button
              type="submit"
              disabled={isLoading || callStatus !== 'idle'}
              className="bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white px-6 py-2 rounded-md font-medium transition-colors"
            >
              {isLoading ? '参加中...' : '通話に参加'}
            </button>
          </form>
        )}

        {/* Current call status */}
        {currentRoomName && (
          <div className="mt-6 p-4 bg-gray-100 rounded-md">
            <h3 className="font-medium text-gray-800 mb-2">現在の通話</h3>
            <p className="text-sm text-gray-600">ルーム: {currentRoomName}</p>
            <p className="text-sm text-gray-600">状態: {
              callStatus === 'idle' ? '待機中' : 
              callStatus === 'calling' ? '呼び出し中' : '接続中'
            }</p>
            <button
              onClick={endCurrentCall}
              className="mt-2 bg-red-600 hover:bg-red-700 text-white px-4 py-1 rounded text-sm font-medium transition-colors"
            >
              通話を終了
            </button>
          </div>
        )}
      </div>

      {/* Video Monitor */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">ビデオモニター</h2>
        <div className="flex justify-center">
          <VideoMonitor
            callStatus={callStatus}
            onLocalVideoRef={(ref) => {
              setVideoRefs(ref, remoteVideoRef.current);
              localVideoRef.current = ref;
            }}
            onRemoteVideoRef={(ref) => {
              setVideoRefs(localVideoRef.current, ref);
              remoteVideoRef.current = ref;
            }}
          />
        </div>
      </div>

      {/* Hidden VideoCallInterface for connection logic */}
      {currentRoomName && currentAccessToken && (
        <VideoCallInterface
          roomName={currentRoomName}
          accessToken={currentAccessToken}
          localVideoElement={localVideoRef.current}
          remoteVideoElement={remoteVideoRef.current}
          onCallEnd={endCurrentCall}
          onError={(error) => {
            console.error('VideoCallInterface error:', error);
            alert(`ビデオ通話エラー: ${error}`);
          }}
        />
      )}
    </div>
  );
};

export default IntercomTest;