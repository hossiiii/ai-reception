'use client';

import React, { useEffect, useCallback } from 'react';
import { connect } from 'twilio-video';
import { Card, CardContent } from '@/components/ui';
import { VideoMonitor } from './VideoMonitor';
import { CallButton } from './CallButton';
import { useIntercomStore } from '@/stores/useIntercomStore';

interface IntercomDeviceProps {
  roomName?: string;
  className?: string;
}

export const IntercomDevice: React.FC<IntercomDeviceProps> = ({
  roomName = 'intercom-room',
  className = '',
}) => {
  const {
    callStatus,
    room,
    localVideo,
    remoteVideo,
    isConnecting,
    error,
    startCall,
    endCall,
    setRoom,
    setLocalVideo,
    setRemoteVideo,
    setConnecting,
    setError,
  } = useIntercomStore();

  // Handle Twilio connection
  const handleConnect = useCallback(async () => {
    startCall();
    
    // Debug: Check if video elements are available
    console.log('🎥 Video elements before connection:', {
      hasLocalVideo: !!localVideo,
      hasRemoteVideo: !!remoteVideo,
      localVideoElement: localVideo,
      remoteVideoElement: remoteVideo
    });
    
    try {
      // Create video room AND send Slack notification
      const { createIntercomCall } = await import('@/lib/services/intercom-api');
      
      const result = await createIntercomCall({
        visitorName: 'Visitor',
        purpose: 'お客様対応'
      });
      
      if (!result.success || !result.video_room) {
        throw new Error(result.error || 'Failed to create video room');
      }
      
      const token = result.video_room.access_token;
      const actualRoomName = result.video_room.room_name;
      
      // Log Slack notification status
      if (result.slack_notification_sent) {
        console.log('✅ Slack notification sent successfully');
      } else {
        console.warn('⚠️ Video room created but Slack notification failed');
      }

      // Validate token format
      if (!token || typeof token !== 'string') {
        throw new Error(`Invalid token format: ${typeof token} - ${token}`);
      }

      // Connect to Twilio Video room with pre-flight media checks
      const twilioRoom = await connect(token, {
        name: actualRoomName,
        audio: true,
        video: { width: 640, height: 480 }
      });

      console.log('✅ Connected to Twilio room:', actualRoomName);
      setRoom(twilioRoom);

      // Wait a moment for VideoMonitor to re-render and set refs
      await new Promise(resolve => setTimeout(resolve, 100));

      // Debug: Re-check video elements after room connection and delay
      console.log('🎥 Video elements after room connection and delay:', {
        hasLocalVideo: !!localVideo,
        hasRemoteVideo: !!remoteVideo,
        storeLocalVideo: useIntercomStore.getState().localVideo,
        storeRemoteVideo: useIntercomStore.getState().remoteVideo
      });

      // Function to attach video track to element
      const attachVideoTrack = (track: any, videoElement: HTMLVideoElement, label: string) => {
        try {
          if (track && track.mediaStreamTrack && videoElement) {
            const mediaStream = new MediaStream([track.mediaStreamTrack]);
            videoElement.srcObject = mediaStream;
            videoElement.play().catch((e) => {
              console.warn(`Video play failed for ${label}:`, e);
            });
            console.log(`✅ ${label} video track attached successfully`);
          }
        } catch (error) {
          console.error(`Failed to attach ${label} video:`, error);
        }
      };

      // Function to attach audio track to element
      const attachAudioTrack = (track: any, videoElement: HTMLVideoElement, label: string) => {
        try {
          if (track && track.mediaStreamTrack && videoElement) {
            // Get existing media stream or create new one
            const existingStream = videoElement.srcObject as MediaStream;
            let mediaStream: MediaStream;
            
            if (existingStream) {
              // Add audio track to existing stream
              existingStream.addTrack(track.mediaStreamTrack);
              mediaStream = existingStream;
            } else {
              // Create new stream with audio track
              mediaStream = new MediaStream([track.mediaStreamTrack]);
              videoElement.srcObject = mediaStream;
            }
            
            videoElement.play().catch((e) => {
              console.warn(`Audio play failed for ${label}:`, e);
            });
            console.log(`🔊 ${label} audio track attached successfully`);
          }
        } catch (error) {
          console.error(`Failed to attach ${label} audio:`, error);
        }
      };

      // Handle local tracks (for visitor's own video and audio)
      const attachLocalTracks = () => {
        const videoTracks = twilioRoom.localParticipant.videoTracks;
        const audioTracks = twilioRoom.localParticipant.audioTracks;
        console.log(`Found ${videoTracks.size} local video tracks and ${audioTracks.size} local audio tracks`);
        
        // Get the latest localVideo element from store
        const currentLocalVideo = useIntercomStore.getState().localVideo || localVideo;
        
        // Attach video tracks
        videoTracks.forEach((publication) => {
          if (publication.track && currentLocalVideo) {
            attachVideoTrack(publication.track, currentLocalVideo, 'Local');
          } else {
            console.log('Video publication track or localVideo element missing:', {
              hasTrack: !!publication.track,
              hasLocalVideo: !!currentLocalVideo,
              storeLocalVideo: !!useIntercomStore.getState().localVideo,
              propsLocalVideo: !!localVideo
            });
          }
        });

        // Attach audio tracks to local video element (for local monitoring if needed)
        audioTracks.forEach((publication) => {
          if (publication.track && currentLocalVideo) {
            attachAudioTrack(publication.track, currentLocalVideo, 'Local');
          } else {
            console.log('Audio publication track or localVideo element missing:', {
              hasTrack: !!publication.track,
              hasLocalVideo: !!currentLocalVideo
            });
          }
        });
      };

      // Wait for local tracks to be published, then attach
      const attachLocalTracksWithDelay = () => {
        // Try immediately
        attachLocalTracks();
        
        // Also try after a short delay to catch tracks that are published slightly later
        setTimeout(() => {
          console.log('Retrying local tracks attachment after delay...');
          attachLocalTracks();
        }, 1000);
      };

      // Attach existing local tracks
      attachLocalTracksWithDelay();

      // Listen for new local tracks being published
      twilioRoom.localParticipant.on('trackPublished', (publication) => {
        const currentLocalVideo = useIntercomStore.getState().localVideo || localVideo;
        if (currentLocalVideo && publication.track) {
          if (publication.track.kind === 'video') {
            attachVideoTrack(publication.track, currentLocalVideo, 'Local (new video)');
          } else if (publication.track.kind === 'audio') {
            attachAudioTrack(publication.track, currentLocalVideo, 'Local (new audio)');
          }
        }
      });

      // Handle remote participant events
      twilioRoom.on('participantConnected', (participant) => {
        console.log(`参加者が接続しました: ${participant.identity}`);
        
        // Attach existing remote video tracks
        participant.videoTracks.forEach((publication) => {
          if (publication.track && remoteVideo) {
            attachVideoTrack(publication.track, remoteVideo, 'Remote');
          }
        });

        // Attach existing remote audio tracks
        participant.audioTracks.forEach((publication) => {
          if (publication.track && remoteVideo) {
            attachAudioTrack(publication.track, remoteVideo, 'Remote');
          }
        });

        // Listen for new remote tracks
        participant.on('trackSubscribed', (track) => {
          if (track.kind === 'video' && remoteVideo) {
            attachVideoTrack(track, remoteVideo, 'Remote (subscribed video)');
          } else if (track.kind === 'audio' && remoteVideo) {
            attachAudioTrack(track, remoteVideo, 'Remote (subscribed audio)');
          }
        });

        participant.on('trackUnsubscribed', (track) => {
          console.log('Remote track unsubscribed:', track.kind);
        });
      });

      twilioRoom.on('participantDisconnected', (participant) => {
        console.log(`参加者が切断しました: ${participant.identity}`);
        // Clear remote video when participant leaves
        if (remoteVideo) {
          remoteVideo.srcObject = null;
        }
      });

      twilioRoom.on('disconnected', () => {
        console.log('Twilioルームから切断されました');
        setRoom(null);
        // Clear video elements
        if (localVideo) localVideo.srcObject = null;
        if (remoteVideo) remoteVideo.srcObject = null;
      });

    } catch (error) {
      console.error('接続エラー:', error);
      setError(error instanceof Error ? error.message : '接続に失敗しました');
    } finally {
      setConnecting(false);
    }
  }, [roomName, localVideo, remoteVideo, startCall, setRoom, setConnecting, setError]);

  // Handle disconnect
  const handleDisconnect = useCallback(() => {
    endCall();
  }, [endCall]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (room) {
        room.disconnect();
      }
    };
  }, [room]);

  return (
    <div className={`h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 via-gray-800 to-black p-4 ${className}`}>
      <Card className="w-full h-full rounded-2xl shadow-2xl flex flex-col items-center justify-between bg-gray-100 border border-gray-300 relative overflow-hidden
        /* Mobile design (default) */
        max-w-md max-h-[90vh] p-4 space-y-2
        /* Tablet design (md: 768px and up) - Full screen optimized */
        md:max-w-none md:max-h-none md:w-full md:h-full md:p-8 md:space-y-6
        /* PC design (lg: 1024px and up) - Contained design */
        lg:max-w-2xl lg:max-h-[85vh] lg:p-6 lg:space-y-4">
        <CardContent className="flex flex-col items-center justify-between h-full w-full
          /* Mobile spacing */
          space-y-2
          /* Tablet spacing - more generous */
          md:space-y-8
          /* PC spacing - balanced */
          lg:space-y-3">
          {/* Camera部分 */}
          <div className="bg-black rounded-full border-4 border-gray-600 shadow-md flex-shrink-0
            /* Mobile: small camera */
            w-12 h-12
            /* Tablet: medium camera */
            md:w-16 md:h-16
            /* PC: small camera to save space */
            lg:w-14 lg:h-14" />

          {/* Video Monitor */}
          <div className="flex-1 w-full flex items-center justify-center min-h-0
            /* Mobile: constrained height */
            max-h-[40vh]
            /* Tablet: more generous height for full-screen experience */
            md:max-h-[60vh]
            /* PC: balanced height for contained design */
            lg:max-h-[35vh]">
            <VideoMonitor
              callStatus={callStatus}
              onLocalVideoRef={setLocalVideo}
              onRemoteVideoRef={setRemoteVideo}
            />
          </div>

          {/* Speaker holes */}
          <div className="grid grid-cols-8 justify-center flex-shrink-0
            /* Mobile: small speaker */
            gap-1 w-36
            /* Tablet: large speaker */
            md:gap-2 md:w-60
            /* PC: compact speaker to save space */
            lg:gap-1 lg:w-44">
            {Array.from({ length: 24 }).map((_, i) => (
              <div key={i} className="bg-gray-500 rounded-full opacity-70
                /* Mobile: tiny holes */
                w-1 h-1
                /* Tablet: larger holes */
                md:w-2 md:h-2
                /* PC: small holes to save space */
                lg:w-1.5 lg:h-1.5" />
            ))}
          </div>

          {/* Error display */}
          {error && (
            <div className="text-red-600 text-sm md:text-base text-center px-3 py-2 bg-red-50 rounded border border-red-200 w-full max-w-sm">
              {error}
            </div>
          )}

          {/* Call Button */}
          <div className="flex flex-col items-center space-y-2 flex-shrink-0">
            <CallButton
              isConnected={callStatus === 'connected'}
              isConnecting={isConnecting}
              onCall={handleConnect}
              onHangup={handleDisconnect}
              disabled={isConnecting}
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
};