// Hook for managing video intercom functionality

import { useState, useCallback } from 'react';
import { useIntercomStore } from '@/stores/useIntercomStore';
import { createIntercomCall, getStaffToken, endVideoRoom } from '@/lib/services/intercom-api';

interface UseVideoIntercomOptions {
  onCallStarted?: (roomName: string) => void;
  onCallEnded?: () => void;
  onError?: (error: string) => void;
}

export function useVideoIntercom(options: UseVideoIntercomOptions = {}) {
  const [isLoading, setIsLoading] = useState(false);
  const [currentRoomName, setCurrentRoomName] = useState<string | null>(null);
  const [currentAccessToken, setCurrentAccessToken] = useState<string | null>(null);
  
  const { 
    callStatus, 
    setLocalVideo, 
    setRemoteVideo, 
    startCall, 
    endCall,
    setError,
    reset 
  } = useIntercomStore();

  /**
   * Start an intercom call as a visitor
   */
  const startVisitorCall = useCallback(async (visitorName: string, purpose?: string) => {
    if (isLoading || callStatus === 'connected') return;

    setIsLoading(true);
    setError(null);
    
    try {
      startCall();
      
      const result = await createIntercomCall({
        visitorName,
        purpose: purpose || 'お客様対応',
      });

      if (!result.success || !result.video_room) {
        throw new Error(result.error || 'Failed to create video call');
      }

      setCurrentRoomName(result.video_room.room_name);
      setCurrentAccessToken(result.video_room.access_token);
      
      options.onCallStarted?.(result.video_room.room_name);
      console.log(`✅ Visitor call started: ${result.video_room.room_name}`, {
        slackNotificationSent: result.slack_notification_sent
      });
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to start call';
      setError(errorMessage);
      options.onError?.(errorMessage);
      console.error('❌ Failed to start visitor call:', error);
    } finally {
      setIsLoading(false);
    }
  }, [isLoading, callStatus, startCall, setError, options]);

  /**
   * Join an intercom call as staff
   */
  const joinStaffCall = useCallback(async (roomName: string, staffName?: string) => {
    if (isLoading || callStatus === 'connected') return;

    setIsLoading(true);
    setError(null);
    
    try {
      startCall();
      
      const result = await getStaffToken(roomName, staffName || 'Staff');

      if (!result.success || !result.access_token) {
        throw new Error(result.error || 'Failed to get staff access token');
      }

      setCurrentRoomName(roomName);
      setCurrentAccessToken(result.access_token);
      
      options.onCallStarted?.(roomName);
      console.log(`✅ Staff joined call: ${roomName}`);
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to join call';
      setError(errorMessage);
      options.onError?.(errorMessage);
      console.error('❌ Failed to join staff call:', error);
    } finally {
      setIsLoading(false);
    }
  }, [isLoading, callStatus, startCall, setError, options]);

  /**
   * End the current call
   */
  const endCurrentCall = useCallback(async () => {
    if (!currentRoomName) return;

    try {
      await endVideoRoom(currentRoomName);
      console.log(`✅ Call ended: ${currentRoomName}`);
    } catch (error) {
      console.warn('Failed to end room on server, but ending locally:', error);
    }

    setCurrentRoomName(null);
    setCurrentAccessToken(null);
    endCall();
    options.onCallEnded?.();
  }, [currentRoomName, endCall, options]);

  /**
   * Set video element refs for VideoMonitor integration
   */
  const setVideoRefs = useCallback((local: HTMLVideoElement | null, remote: HTMLVideoElement | null) => {
    setLocalVideo(local);
    setRemoteVideo(remote);
  }, [setLocalVideo, setRemoteVideo]);

  /**
   * Reset all state
   */
  const resetAll = useCallback(() => {
    setCurrentRoomName(null);
    setCurrentAccessToken(null);
    setIsLoading(false);
    reset();
  }, [reset]);

  return {
    // State
    isLoading,
    callStatus,
    currentRoomName,
    currentAccessToken,
    
    // Video refs for VideoMonitor
    setVideoRefs,
    
    // Actions
    startVisitorCall,
    joinStaffCall,
    endCurrentCall,
    resetAll,
    
    // Store access (for advanced use cases)
    intercomStore: useIntercomStore,
  };
}