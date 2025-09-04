'use client';

import { useEffect, useRef, useState } from 'react';
import { connect } from 'twilio-video';
import { useIntercomStore } from '@/stores/useIntercomStore';

export interface VideoCallInterfaceProps {
  roomName: string;
  accessToken: string;
  onCallEnd?: () => void;
  onError?: (error: string) => void;
  // New props for intercom integration
  localVideoElement?: HTMLVideoElement | null;
  remoteVideoElement?: HTMLVideoElement | null;
  isStaffMode?: boolean; // For staff joining from Slack links
}

export default function VideoCallInterface({
  roomName,
  accessToken,
  onCallEnd,
  onError,
  localVideoElement,
  remoteVideoElement,
  isStaffMode = false
}: VideoCallInterfaceProps) {
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const localVideoRef = useRef<HTMLVideoElement>(null);
  const remoteVideoRef = useRef<HTMLVideoElement>(null);
  const roomRef = useRef<any>(null);
  
  // Use intercom store for state management
  const { setRoom, setConnecting, setError } = useIntercomStore();

  useEffect(() => {
    if (!accessToken || !roomName) {
      setIsLoading(false);
      return;
    }

    const connectToRoom = async () => {
      try {
        setIsLoading(true);
        setConnecting(true);
        
        console.log('Connecting to Twilio Video room:', roomName);
        
        // Validate token format
        if (!accessToken || typeof accessToken !== 'string') {
          throw new Error(`Invalid token format in VideoCallInterface: ${typeof accessToken} - ${accessToken}`);
        }
        
        const room = await connect(accessToken, {
          name: roomName,
          audio: true,
          video: true
        });
        
        roomRef.current = room;
        setRoom(room); // Update store with room reference
        setIsConnected(true);
        setIsLoading(false);
        setConnecting(false);

        console.log('Connected to room:', room.name);

        // Handle participant connections
        room.on('participantConnected', (participant: any) => {
          console.log('Participant connected:', participant.identity);
          handleRemoteParticipant(participant);
        });

        room.on('participantDisconnected', (participant: any) => {
          console.log('Participant disconnected:', participant.identity);
        });

        // Handle room disconnect
        room.on('disconnected', () => {
          console.log('Disconnected from room');
          setIsConnected(false);
          setRoom(null);
        });

        // Handle existing participants
        room.participants.forEach(handleRemoteParticipant);

        // Handle local tracks
        room.localParticipant.tracks.forEach((publication: any) => {
          if (publication.track) {
            handleLocalTrack(publication.track);
          }
        });

      } catch (error) {
        console.error('Failed to connect to video room:', error);
        setIsLoading(false);
        setConnecting(false);
        
        // Handle specific duplicate identity error
        let errorMessage = error instanceof Error ? error.message : 'Failed to connect to video call';
        if (errorMessage.includes('duplicate identity')) {
          errorMessage = 'Another session is already active. Please close other tabs or wait a moment before trying again.';
          console.warn('Duplicate identity detected - user may have multiple sessions open');
        }
        
        setError(errorMessage);
        onError?.(errorMessage);
      }
    };

    connectToRoom();

    return () => {
      if (roomRef.current) {
        roomRef.current.disconnect();
        setRoom(null);
      }
    };
  }, [accessToken, roomName, onError, setRoom, setConnecting, setError]);

  const handleLocalTrack = (track: any) => {
    if (track.kind === 'video') {
      // Use provided video element from VideoMonitor or fallback to local ref
      const localVideo = localVideoElement || localVideoRef.current;
      if (localVideo) {
        localVideo.srcObject = new MediaStream([track.mediaStreamTrack]);
        localVideo.play().catch(console.error);
      }
    }
  };

  const handleRemoteParticipant = (participant: any) => {
    participant.tracks.forEach((publication: any) => {
      if (publication.isSubscribed) {
        handleRemoteTrack(publication.track);
      }
    });

    participant.on('trackSubscribed', handleRemoteTrack);
  };

  const handleRemoteTrack = (track: any) => {
    if (track.kind === 'video') {
      // Use provided video element from VideoMonitor or fallback to local ref
      const remoteVideo = remoteVideoElement || remoteVideoRef.current;
      if (remoteVideo) {
        remoteVideo.srcObject = new MediaStream([track.mediaStreamTrack]);
        remoteVideo.play().catch(console.error);
      }
    }
  };

  const handleEndCall = () => {
    if (roomRef.current) {
      roomRef.current.disconnect();
      setIsConnected(false);
      setRoom(null);
    }
    onCallEnd?.();
  };

  // If using with VideoMonitor component, don't render the full UI
  if (localVideoElement && remoteVideoElement) {
    // This component is being used with VideoMonitor, so just handle the connection logic
    // The VideoMonitor handles the video display
    return null;
  }

  // Staff mode - simple interface for staff joining from Slack
  if (isStaffMode) {
    if (isLoading) {
      return (
        <div className="flex items-center justify-center min-h-screen bg-gray-100">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-700">接続中...</p>
          </div>
        </div>
      );
    }

    return (
      <div className="min-h-screen bg-gray-100 p-4">
        <div className="max-w-4xl mx-auto">
          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="flex justify-between items-center mb-6">
              <h1 className="text-xl font-semibold text-gray-800">
                受付対応 - {roomName}
              </h1>
              <div className="flex items-center space-x-2">
                <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
                <span className="text-sm text-gray-600">
                  {isConnected ? '接続中' : '切断中'}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              <div className="relative bg-gray-900 rounded-lg overflow-hidden">
                <video
                  ref={remoteVideoRef}
                  className="w-full h-64 object-cover"
                  playsInline
                />
                <div className="absolute bottom-2 left-2 bg-black bg-opacity-50 text-white text-sm px-2 py-1 rounded">
                  来客者
                </div>
              </div>
              
              <div className="relative bg-gray-900 rounded-lg overflow-hidden">
                <video
                  ref={localVideoRef}
                  className="w-full h-64 object-cover"
                  muted
                  playsInline
                />
                <div className="absolute bottom-2 left-2 bg-black bg-opacity-50 text-white text-sm px-2 py-1 rounded">
                  あなた
                </div>
              </div>
            </div>

            <div className="flex justify-center">
              <button
                onClick={handleEndCall}
                className="bg-red-600 hover:bg-red-700 text-white px-6 py-2 rounded-lg font-medium transition-colors"
              >
                通話を終了
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Original full-screen mode for backward compatibility
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center text-white">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-white mx-auto mb-4"></div>
          <p className="text-xl">ビデオ通話に接続中...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 p-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-white">
            ビデオ通話 - {roomName}
          </h1>
          <div className="flex items-center space-x-2">
            <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
            <span className="text-white">
              {isConnected ? '接続中' : '切断中'}
            </span>
          </div>
        </div>

        {/* Video Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Local Video */}
          <div className="relative">
            <video
              ref={localVideoRef}
              className="w-full h-64 lg:h-96 bg-gray-800 rounded-lg"
              muted
              playsInline
            />
            <div className="absolute bottom-4 left-4 bg-black bg-opacity-50 text-white px-3 py-1 rounded">
              あなた
            </div>
          </div>

          {/* Remote Video */}
          <div className="relative">
            <video
              ref={remoteVideoRef}
              className="w-full h-64 lg:h-96 bg-gray-800 rounded-lg"
              playsInline
            />
            <div className="absolute bottom-4 left-4 bg-black bg-opacity-50 text-white px-3 py-1 rounded">
              相手
            </div>
          </div>
        </div>

        {/* Controls */}
        <div className="flex justify-center space-x-4">
          <button
            onClick={handleEndCall}
            className="bg-red-600 hover:bg-red-700 text-white px-8 py-3 rounded-lg font-medium transition-colors"
          >
            通話を終了
          </button>
        </div>
      </div>
    </div>
  );
}