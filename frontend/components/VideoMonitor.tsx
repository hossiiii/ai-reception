'use client';

import React, { useEffect, useRef } from 'react';

interface VideoMonitorProps {
  callStatus: 'idle' | 'calling' | 'connected';
  onLocalVideoRef?: (ref: HTMLVideoElement | null) => void;
  onRemoteVideoRef?: (ref: HTMLVideoElement | null) => void;
}

export const VideoMonitor: React.FC<VideoMonitorProps> = ({
  callStatus,
  onLocalVideoRef,
  onRemoteVideoRef,
}) => {
  const localRef = useRef<HTMLVideoElement>(null);
  const remoteRef = useRef<HTMLVideoElement>(null);

  // Set refs immediately when they become available
  useEffect(() => {
    if (onLocalVideoRef && localRef.current) {
      console.log('Setting local video ref:', localRef.current);
      onLocalVideoRef(localRef.current);
    }
  }, [onLocalVideoRef]);

  useEffect(() => {
    if (onRemoteVideoRef && remoteRef.current) {
      console.log('Setting remote video ref:', remoteRef.current);
      onRemoteVideoRef(remoteRef.current);
    }
  }, [onRemoteVideoRef]);

  const getDisplayContent = () => {
    switch (callStatus) {
      case 'calling':
        return (
          <div className="flex items-center justify-center h-full">
            <div className="text-center space-y-2">
              <div className="w-8 h-8 border-2 border-blue-400 border-t-transparent rounded-full animate-spin mx-auto" />
              <span className="text-blue-400 font-semibold text-lg">
                呼び出し中...
              </span>
            </div>
          </div>
        );
        
      case 'idle':
        return (
          <div className="flex items-center justify-center h-full">
            <span className="text-gray-400 text-lg">
              待機中
            </span>
          </div>
        );
        
      default:
        return null;
    }
  };

  return (
    <div className="w-56 h-40 bg-gray-900 rounded-lg flex items-center justify-center text-white shadow-inner border border-gray-700 relative overflow-hidden">
      {/* Always render video elements so refs are available, but show/hide based on call status */}
      
      {/* Remote video (main display) - visible only when connected */}
      <video
        ref={remoteRef}
        autoPlay
        playsInline
        className={`w-full h-full object-cover rounded-lg ${callStatus === 'connected' ? 'block' : 'hidden'}`}
      />
      
      {/* Local video (picture-in-picture overlay) - visible only when connected */}
      <div className={`absolute bottom-2 right-2 w-16 h-12 bg-gray-800 rounded border-2 border-white shadow-lg overflow-hidden ${callStatus === 'connected' ? 'block' : 'hidden'}`}>
        <video
          ref={localRef}
          autoPlay
          playsInline
          muted
          className="w-full h-full object-cover"
        />
      </div>

      {/* Status overlays */}
      {getDisplayContent()}
    </div>
  );
};