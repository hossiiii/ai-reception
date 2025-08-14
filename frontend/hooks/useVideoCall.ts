'use client';

/**
 * Video call management hook using Twilio Video SDK
 * Handles room connection, participant management, and track handling
 */

import { useState, useEffect, useRef, useCallback } from 'react';

// Type definitions for Twilio Video (to avoid SSR issues)
export interface TwilioRoom {
  disconnect: () => void;
  on: (event: string, handler: (...args: any[]) => void) => void;
  off: (event: string, handler: (...args: any[]) => void) => void;
  localParticipant: TwilioParticipant;
  participants: Map<string, TwilioParticipant>;
  sid: string;
  name: string;
}

export interface TwilioParticipant {
  sid: string;
  identity: string;
  tracks: Map<string, TwilioTrack>;
  videoTracks: Map<string, TwilioVideoTrack>;
  audioTracks: Map<string, TwilioAudioTrack>;
  on: (event: string, handler: (...args: any[]) => void) => void;
  off: (event: string, handler: (...args: any[]) => void) => void;
}

export interface TwilioTrack {
  sid: string;
  kind: 'audio' | 'video';
  isEnabled: boolean;
  attach: (element?: HTMLElement) => HTMLElement;
  detach: (element?: HTMLElement) => HTMLElement[];
}

export interface TwilioVideoTrack extends TwilioTrack {
  kind: 'video';
}

export interface TwilioAudioTrack extends TwilioTrack {
  kind: 'audio';
}

export interface UseVideoCallOptions {
  roomName: string;
  accessToken: string;
  autoConnect?: boolean;
}

export interface VideoCallState {
  status: 'disconnected' | 'connecting' | 'connected' | 'error';
  room: TwilioRoom | null;
  localParticipant: TwilioParticipant | null;
  remoteParticipants: Map<string, TwilioParticipant>;
  isAudioMuted: boolean;
  isVideoMuted: boolean;
  error: string | null;
  participantCount: number;
}

export interface UseVideoCallReturn {
  // State
  state: VideoCallState;
  
  // Actions
  connect: () => Promise<boolean>;
  disconnect: () => void;
  toggleAudio: () => void;
  toggleVideo: () => void;
  
  // Video element attachment helpers
  attachLocalVideo: (element: HTMLVideoElement) => void;
  detachLocalVideo: (element: HTMLVideoElement) => void;
  attachRemoteVideo: (participantSid: string, element: HTMLVideoElement) => void;
  detachRemoteVideo: (participantSid: string, element: HTMLVideoElement) => void;
}

export function useVideoCall(options: UseVideoCallOptions): UseVideoCallReturn {
  const { roomName, accessToken, autoConnect = false } = options;
  
  // Refs
  const twilioVideoRef = useRef<any>(null);
  const roomRef = useRef<TwilioRoom | null>(null);
  const cleanupFunctionsRef = useRef<(() => void)[]>([]);
  
  // State
  const [state, setState] = useState<VideoCallState>({
    status: 'disconnected',
    room: null,
    localParticipant: null,
    remoteParticipants: new Map(),
    isAudioMuted: false,
    isVideoMuted: false,
    error: null,
    participantCount: 0
  });
  
  // Update state helper
  const updateState = useCallback((updates: Partial<VideoCallState>) => {
    setState(prev => ({ ...prev, ...updates }));
  }, []);
  
  // Dynamic import of Twilio Video to avoid SSR issues
  const loadTwilioVideo = useCallback(async () => {
    if (twilioVideoRef.current) {
      return twilioVideoRef.current;
    }
    
    try {
      const Video = await import('twilio-video');
      twilioVideoRef.current = Video;
      return Video;
    } catch (error) {
      console.error('Failed to load Twilio Video SDK:', error);
      throw new Error('Video SDK not available');
    }
  }, []);
  
  // Connect to video room
  const connect = useCallback(async (): Promise<boolean> => {
    try {
      updateState({ status: 'connecting', error: null });
      
      // Check if this is a mock token (development mode)
      if (accessToken.includes('mock') || accessToken.startsWith('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJtb2NrIi')) {
        console.log('🔧 Development mode: Mock token detected, simulating video connection');
        
        // Simulate a successful connection in development mode
        setTimeout(() => {
          const mockRoom = {
            disconnect: () => console.log('Mock room disconnected'),
            on: (event: string, _handler: any) => console.log(`Mock room event: ${event}`),
            off: (event: string, _handler: any) => console.log(`Mock room event removed: ${event}`),
            localParticipant: {
              sid: 'mock-local-participant',
              identity: 'mock-user',
              tracks: new Map(),
              videoTracks: new Map(),
              audioTracks: new Map(),
              on: (event: string, _handler: any) => console.log(`Mock participant event: ${event}`),
              off: (event: string, _handler: any) => console.log(`Mock participant event removed: ${event}`)
            },
            participants: new Map(),
            sid: 'mock-room-sid',
            name: roomName
          };
          
          roomRef.current = mockRoom as any;
          
          updateState({
            status: 'connected',
            room: mockRoom as any,
            localParticipant: mockRoom.localParticipant as any,
            remoteParticipants: new Map(),
            participantCount: 1,
            error: null
          });
          
          console.log('✅ Mock video connection established successfully');
        }, 1500); // Simulate connection delay
        
        return true;
      }
      
      // Load Twilio Video SDK
      const Video = await loadTwilioVideo();
      
      // Connect to room
      const room = await Video.connect(accessToken, {
        name: roomName,
        audio: true,
        video: { width: 640, height: 480 },
        bandwidthProfile: {
          video: {
            mode: 'collaboration',
            maxTracks: 2  // Free trial limit
          }
        },
        maxAudioBitrate: 16000,  // Reduce bandwidth for free trial
        maxVideoBitrate: 100000,  // Reduce bandwidth for free trial
        preferredVideoCodecs: ['VP8', 'H264'],
        networkQuality: {
          local: 1,
          remote: 1
        }
      });
      
      roomRef.current = room;
      
      // Setup event handlers
      setupRoomEventHandlers(room);
      
      // Update state with successful connection
      const remoteParticipants = new Map();
      console.log(`🏠 Room connected. Initial participants: ${room.participants.size}`);
      
      room.participants.forEach((participant: TwilioParticipant) => {
        console.log(`👥 Found existing participant: ${participant.identity} (${participant.sid})`);
        remoteParticipants.set(participant.sid, participant);
        setupParticipantEventHandlers(participant);
      });
      
      // Also setup event handlers for local participant
      console.log(`👤 Local participant: ${room.localParticipant.identity} (${room.localParticipant.sid})`);
      console.log(`  📹 Local video tracks: ${room.localParticipant.videoTracks.size}`);
      console.log(`  🎵 Local audio tracks: ${room.localParticipant.audioTracks.size}`);
      
      updateState({
        status: 'connected',
        room,
        localParticipant: room.localParticipant,
        remoteParticipants,
        participantCount: remoteParticipants.size + 1,
        error: null
      });
      
      console.log(`✅ Connected to video room: ${roomName} with ${remoteParticipants.size + 1} total participants`);
      return true;
      
    } catch (error) {
      console.error('Failed to connect to video room:', error);
      
      // Provide specific error messages for common Twilio errors
      let errorMessage = 'Connection failed';
      if (error instanceof Error) {
        const message = error.message;
        if (message.includes('Invalid Access Token')) {
          errorMessage = 'Invalid access token. Please refresh and try again.';
        } else if (message.includes('Token expired')) {
          errorMessage = 'Access token expired. Please refresh and try again.';
        } else if (message.includes('Room not found')) {
          errorMessage = 'Video room not found. Please contact support.';
        } else if (message.includes('Room is full')) {
          errorMessage = 'Video room is full. Please try again later.';
        } else if (message.includes('Permission denied')) {
          errorMessage = 'Camera/microphone permission denied. Please enable and try again.';
        } else {
          errorMessage = message;
        }
      }
      
      updateState({ 
        status: 'error', 
        error: errorMessage
      });
      return false;
    }
  }, [roomName, accessToken, loadTwilioVideo, updateState]);
  
  // Disconnect from video room
  const disconnect = useCallback(() => {
    if (roomRef.current) {
      console.log('Disconnecting from video room');
      roomRef.current.disconnect();
      roomRef.current = null;
    }
    
    // Run cleanup functions
    cleanupFunctionsRef.current.forEach(cleanup => cleanup());
    cleanupFunctionsRef.current = [];
    
    updateState({
      status: 'disconnected',
      room: null,
      localParticipant: null,
      remoteParticipants: new Map(),
      participantCount: 0,
      error: null
    });
  }, [updateState]);
  
  // Setup room event handlers
  const setupRoomEventHandlers = useCallback((room: TwilioRoom) => {
    const handleParticipantConnected = (participant: TwilioParticipant) => {
      console.log(`Participant connected: ${participant.identity}`);
      setupParticipantEventHandlers(participant);
      
      setState(prev => {
        const newRemoteParticipants = new Map(prev.remoteParticipants);
        newRemoteParticipants.set(participant.sid, participant);
        return {
          ...prev,
          remoteParticipants: newRemoteParticipants,
          participantCount: newRemoteParticipants.size + 1
        };
      });
    };
    
    const handleParticipantDisconnected = (participant: TwilioParticipant) => {
      console.log(`Participant disconnected: ${participant.identity}`);
      
      setState(prev => {
        const newRemoteParticipants = new Map(prev.remoteParticipants);
        newRemoteParticipants.delete(participant.sid);
        return {
          ...prev,
          remoteParticipants: newRemoteParticipants,
          participantCount: newRemoteParticipants.size + 1
        };
      });
    };
    
    const handleDisconnected = (_room: TwilioRoom, error?: Error) => {
      console.log('Disconnected from room', error ? `due to error: ${error.message}` : '');
      updateState({
        status: 'disconnected',
        room: null,
        localParticipant: null,
        remoteParticipants: new Map(),
        participantCount: 0,
        error: error ? error.message : null
      });
    };
    
    // Add event listeners
    room.on('participantConnected', handleParticipantConnected);
    room.on('participantDisconnected', handleParticipantDisconnected);
    room.on('disconnected', handleDisconnected);
    
    // Store cleanup functions
    cleanupFunctionsRef.current.push(() => {
      room.off('participantConnected', handleParticipantConnected);
      room.off('participantDisconnected', handleParticipantDisconnected);
      room.off('disconnected', handleDisconnected);
    });
  }, [updateState]);
  
  // Setup participant event handlers
  const setupParticipantEventHandlers = useCallback((participant: TwilioParticipant) => {
    console.log(`🎯 Setting up event handlers for participant: ${participant.identity} (${participant.sid})`);
    
    const handleTrackSubscribed = (track: TwilioTrack) => {
      console.log(`📹 Track subscribed: ${track.kind} from ${participant.identity}`, track);
      
      // Force re-render to trigger attachment in component
      setState(prev => ({ ...prev, remoteParticipants: new Map(prev.remoteParticipants) }));
    };
    
    const handleTrackUnsubscribed = (track: TwilioTrack) => {
      console.log(`📹 Track unsubscribed: ${track.kind} from ${participant.identity}`);
      
      // Force re-render to trigger detachment in component
      setState(prev => ({ ...prev, remoteParticipants: new Map(prev.remoteParticipants) }));
    };
    
    const handleTrackPublished = (publication: any) => {
      console.log(`📤 Track published: ${publication.kind} from ${participant.identity}`, publication);
    };
    
    const handleTrackUnpublished = (publication: any) => {
      console.log(`📤 Track unpublished: ${publication.kind} from ${participant.identity}`, publication);
    };
    
    participant.on('trackSubscribed', handleTrackSubscribed);
    participant.on('trackUnsubscribed', handleTrackUnsubscribed);
    participant.on('trackPublished', handleTrackPublished);
    participant.on('trackUnpublished', handleTrackUnpublished);
    
    // Also check if participant already has tracks (they might have been published before we connected)
    console.log(`🔍 Checking existing tracks for ${participant.identity}:`);
    console.log(`  Video tracks: ${participant.videoTracks.size}`);
    console.log(`  Audio tracks: ${participant.audioTracks.size}`);
    
    // Log track details
    participant.videoTracks.forEach((track: any, sid: string) => {
      console.log(`  📹 Video track ${sid}:`, track);
      if (track.track) {
        console.log(`    - Track object:`, track.track);
        console.log(`    - Is enabled:`, track.track.isEnabled);
        console.log(`    - Kind:`, track.track.kind);
        console.log(`    - Name:`, track.track.name);
      }
    });
    
    participant.audioTracks.forEach((track: any, sid: string) => {
      console.log(`  🎵 Audio track ${sid}:`, track);
      if (track.track) {
        console.log(`    - Track object:`, track.track);
        console.log(`    - Is enabled:`, track.track.isEnabled);
        console.log(`    - Kind:`, track.track.kind);
        console.log(`    - Name:`, track.track.name);
      }
    });
    
    // If participant has tracks already, trigger a re-render to attach them
    if (participant.videoTracks.size > 0 || participant.audioTracks.size > 0) {
      console.log(`🔄 Participant already has tracks, triggering re-render for attachment`);
      setTimeout(() => {
        setState(prev => ({ ...prev, remoteParticipants: new Map(prev.remoteParticipants) }));
      }, 100);
    }
    
    // Store cleanup functions
    cleanupFunctionsRef.current.push(() => {
      participant.off('trackSubscribed', handleTrackSubscribed);
      participant.off('trackUnsubscribed', handleTrackUnsubscribed);
      participant.off('trackPublished', handleTrackPublished);
      participant.off('trackUnpublished', handleTrackUnpublished);
    });
  }, []);
  
  // Toggle audio mute
  const toggleAudio = useCallback(() => {
    if (!state.localParticipant) return;
    
    state.localParticipant.audioTracks.forEach((audioTrack: any) => {
      if (audioTrack.track) {
        audioTrack.track.isEnabled ? audioTrack.track.disable() : audioTrack.track.enable();
      }
    });
    
    updateState({ isAudioMuted: !state.isAudioMuted });
  }, [state.localParticipant, state.isAudioMuted, updateState]);
  
  // Toggle video mute
  const toggleVideo = useCallback(() => {
    if (!state.localParticipant) return;
    
    state.localParticipant.videoTracks.forEach((videoTrack: any) => {
      if (videoTrack.track) {
        videoTrack.track.isEnabled ? videoTrack.track.disable() : videoTrack.track.enable();
      }
    });
    
    updateState({ isVideoMuted: !state.isVideoMuted });
  }, [state.localParticipant, state.isVideoMuted, updateState]);
  
  // Video element attachment helpers
  const attachLocalVideo = useCallback((element: HTMLVideoElement) => {
    if (!state.localParticipant) return;
    
    // Handle mock mode
    if (state.localParticipant.sid === 'mock-local-participant') {
      console.log('🔧 Mock mode: Simulating local video attachment');
      // In mock mode, try to get user media for local preview
      navigator.mediaDevices.getUserMedia({ video: true, audio: false })
        .then(stream => {
          element.srcObject = stream;
          element.play();
        })
        .catch(err => console.log('Mock mode: Could not access camera for preview:', err));
      return;
    }
    
    state.localParticipant.videoTracks.forEach((videoTrack: any) => {
      if (videoTrack.track) {
        videoTrack.track.attach(element);
      }
    });
  }, [state.localParticipant]);
  
  const detachLocalVideo = useCallback((element: HTMLVideoElement) => {
    if (!state.localParticipant) return;
    
    // Handle mock mode
    if (state.localParticipant.sid === 'mock-local-participant') {
      console.log('🔧 Mock mode: Simulating local video detachment');
      if (element.srcObject) {
        const stream = element.srcObject as MediaStream;
        stream.getTracks().forEach(track => track.stop());
        element.srcObject = null;
      }
      return;
    }
    
    state.localParticipant.videoTracks.forEach((videoTrack: any) => {
      if (videoTrack.track) {
        videoTrack.track.detach(element);
      }
    });
  }, [state.localParticipant]);
  
  const attachRemoteVideo = useCallback((participantSid: string, element: HTMLVideoElement) => {
    const participant = state.remoteParticipants.get(participantSid);
    if (!participant) {
      console.log(`❌ No participant found for SID: ${participantSid}`);
      return;
    }
    
    console.log(`🔗 Attempting to attach remote video for ${participant.identity} (${participantSid})`);
    console.log(`  Video tracks available: ${participant.videoTracks.size}`);
    console.log(`  Audio tracks available: ${participant.audioTracks.size}`);
    
    // Handle mock mode - no remote participants in mock mode
    if (participantSid.startsWith('mock-')) {
      console.log('🔧 Mock mode: No remote video to attach');
      return;
    }
    
    // Attach video tracks
    let videoAttached = false;
    participant.videoTracks.forEach((videoTrack: any, trackSid: string) => {
      console.log(`🎥 Processing video track ${trackSid}:`, videoTrack);
      if (videoTrack.track) {
        console.log(`  ✅ Attaching video track to element`);
        const attachedElements = videoTrack.track.attach(element);
        console.log(`  📺 Video track attached, elements:`, attachedElements);
        videoAttached = true;
      } else {
        console.log(`  ❌ Video track has no track object`);
      }
    });
    
    // Attach audio tracks (they'll automatically play through the browser's audio system)
    let audioAttached = false;
    participant.audioTracks.forEach((audioTrack: any, trackSid: string) => {
      console.log(`🎵 Processing audio track ${trackSid}:`, audioTrack);
      if (audioTrack.track) {
        console.log(`  ✅ Attaching audio track to audio element`);
        try {
          // Create or find an audio element for this track
          let audioElement = document.getElementById(`audio-${participantSid}`) as HTMLAudioElement;
          if (!audioElement) {
            audioElement = document.createElement('audio');
            audioElement.id = `audio-${participantSid}`;
            audioElement.autoplay = true;
            audioElement.style.display = 'none'; // Hidden audio element
            document.body.appendChild(audioElement);
            console.log(`  📻 Created audio element: audio-${participantSid}`);
          }
          
          const attachedElements = audioTrack.track.attach(audioElement);
          console.log(`  🔊 Audio track attached to element:`, attachedElements);
          audioAttached = true;
        } catch (error) {
          console.log(`  ❌ Failed to attach audio track:`, error);
          // Fallback: try to attach without element (auto-play)
          try {
            audioTrack.track.attach();
            console.log(`  🔊 Audio track attached with auto-play fallback`);
            audioAttached = true;
          } catch (fallbackError) {
            console.log(`  ❌ Audio fallback also failed:`, fallbackError);
          }
        }
      } else {
        console.log(`  ❌ Audio track has no track object`);
      }
    });
    
    console.log(`📊 Attachment summary: Video=${videoAttached}, Audio=${audioAttached}`);
  }, [state.remoteParticipants]);
  
  const detachRemoteVideo = useCallback((participantSid: string, element: HTMLVideoElement) => {
    const participant = state.remoteParticipants.get(participantSid);
    if (!participant) return;
    
    console.log(`🔌 Detaching tracks for ${participantSid}`);
    
    // Handle mock mode
    if (participantSid.startsWith('mock-')) {
      console.log('🔧 Mock mode: No remote video to detach');
      return;
    }
    
    // Detach video tracks
    participant.videoTracks.forEach((videoTrack: any) => {
      if (videoTrack.track) {
        console.log(`  📺 Detaching video track`);
        videoTrack.track.detach(element);
      }
    });
    
    // Detach and cleanup audio tracks
    participant.audioTracks.forEach((audioTrack: any) => {
      if (audioTrack.track) {
        console.log(`  🎵 Detaching audio track`);
        audioTrack.track.detach();
      }
    });
    
    // Remove audio element if it exists
    const audioElement = document.getElementById(`audio-${participantSid}`);
    if (audioElement) {
      console.log(`  🗑️ Removing audio element: audio-${participantSid}`);
      audioElement.remove();
    }
  }, [state.remoteParticipants]);
  
  // Auto-connect if enabled
  useEffect(() => {
    if (autoConnect && roomName && accessToken) {
      connect();
    }
  }, [autoConnect, roomName, accessToken, connect]);
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);
  
  return {
    state,
    connect,
    disconnect,
    toggleAudio,
    toggleVideo,
    attachLocalVideo,
    detachLocalVideo,
    attachRemoteVideo,
    detachRemoteVideo
  };
}