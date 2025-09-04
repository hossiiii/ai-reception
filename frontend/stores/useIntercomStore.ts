'use client';

import { create } from 'zustand';
import { Room } from 'twilio-video';

type CallStatus = 'idle' | 'calling' | 'connected';

interface IntercomState {
  // Call state
  callStatus: CallStatus;
  
  // Twilio video references
  room: Room | null;
  localVideo: HTMLVideoElement | null;
  remoteVideo: HTMLVideoElement | null;
  
  // Connection state
  isConnecting: boolean;
  error: string | null;
}

interface IntercomActions {
  // Call actions
  startCall: () => void;
  endCall: () => void;
  
  // Video element setters
  setRoom: (room: Room | null) => void;
  setLocalVideo: (element: HTMLVideoElement | null) => void;
  setRemoteVideo: (element: HTMLVideoElement | null) => void;
  
  // Connection state setters
  setConnecting: (connecting: boolean) => void;
  setError: (error: string | null) => void;
  
  // Reset state
  reset: () => void;
}

const initialState: IntercomState = {
  callStatus: 'idle',
  room: null,
  localVideo: null,
  remoteVideo: null,
  isConnecting: false,
  error: null,
};

export const useIntercomStore = create<IntercomState & IntercomActions>()((set, get) => ({
  ...initialState,
  
  startCall: () => {
    set({ 
      callStatus: 'calling', 
      isConnecting: true,
      error: null 
    });
  },
  
  endCall: () => {
    const { room } = get();
    
    // Disconnect from Twilio room if connected
    if (room) {
      try {
        room.disconnect();
      } catch (error) {
        console.warn('Failed to disconnect room:', error);
      }
    }
    
    set({ 
      callStatus: 'idle',
      room: null,
      isConnecting: false,
      error: null
    });
  },
  
  setRoom: (room: Room | null) => {
    set({ 
      room,
      callStatus: room ? 'connected' : 'idle',
      isConnecting: false
    });
  },
  
  setLocalVideo: (element: HTMLVideoElement | null) => {
    set({ localVideo: element });
  },
  
  setRemoteVideo: (element: HTMLVideoElement | null) => {
    set({ remoteVideo: element });
  },
  
  setConnecting: (isConnecting: boolean) => {
    set({ isConnecting });
  },
  
  setError: (error: string | null) => {
    set({ 
      error, 
      isConnecting: false,
      callStatus: error ? 'idle' : get().callStatus
    });
  },
  
  reset: () => {
    const { room } = get();
    
    // Clean up room connection
    if (room) {
      try {
        room.disconnect();
      } catch (error) {
        console.warn('Failed to disconnect room during reset:', error);
      }
    }
    
    set(initialState);
  },
}));