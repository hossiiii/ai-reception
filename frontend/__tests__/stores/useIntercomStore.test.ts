/**
 * useIntercomStore Tests
 * Tests for stores/useIntercomStore.ts
 */

import { act, renderHook } from '@testing-library/react';
import { useIntercomStore } from '@/stores/useIntercomStore';
import { Room } from 'twilio-video';

// Mock Twilio Video Room
const createMockRoom = (): jest.Mocked<Room> => ({
  disconnect: jest.fn(),
  sid: 'RM123456789',
  name: 'test-room',
  state: 'connected',
  localParticipant: {} as any,
  participants: new Map(),
  on: jest.fn(),
  off: jest.fn(),
  removeAllListeners: jest.fn(),
} as any);

describe('useIntercomStore', () => {
  let mockRoom: jest.Mocked<Room>;

  beforeEach(() => {
    mockRoom = createMockRoom();
    
    // Reset store to initial state before each test
    // First clear any previous mocks that might throw
    if (mockRoom.disconnect) {
      mockRoom.disconnect.mockImplementation(() => {});
    }
    
    const { result } = renderHook(() => useIntercomStore());
    act(() => {
      result.current.reset();
    });
  });

  describe('Initial State', () => {
    it('should have correct initial state', () => {
      const { result } = renderHook(() => useIntercomStore());

      expect(result.current.callStatus).toBe('idle');
      expect(result.current.room).toBeNull();
      expect(result.current.localVideo).toBeNull();
      expect(result.current.remoteVideo).toBeNull();
      expect(result.current.isConnecting).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it('should have all required action methods', () => {
      const { result } = renderHook(() => useIntercomStore());

      expect(typeof result.current.startCall).toBe('function');
      expect(typeof result.current.endCall).toBe('function');
      expect(typeof result.current.setRoom).toBe('function');
      expect(typeof result.current.setLocalVideo).toBe('function');
      expect(typeof result.current.setRemoteVideo).toBe('function');
      expect(typeof result.current.setConnecting).toBe('function');
      expect(typeof result.current.setError).toBe('function');
      expect(typeof result.current.reset).toBe('function');
    });
  });

  describe('startCall Action', () => {
    it('should update state correctly when starting a call', () => {
      const { result } = renderHook(() => useIntercomStore());

      act(() => {
        result.current.startCall();
      });

      expect(result.current.callStatus).toBe('calling');
      expect(result.current.isConnecting).toBe(true);
      expect(result.current.error).toBeNull();
    });

    it('should clear existing error when starting a call', () => {
      const { result } = renderHook(() => useIntercomStore());

      // Set an error first
      act(() => {
        result.current.setError('Previous error');
      });

      expect(result.current.error).toBe('Previous error');

      // Start call should clear error
      act(() => {
        result.current.startCall();
      });

      expect(result.current.error).toBeNull();
    });
  });

  describe('endCall Action', () => {
    it('should reset state when ending a call without room', () => {
      const { result } = renderHook(() => useIntercomStore());

      // Set up some state first
      act(() => {
        result.current.startCall();
        result.current.setError('Some error');
      });

      // End the call
      act(() => {
        result.current.endCall();
      });

      expect(result.current.callStatus).toBe('idle');
      expect(result.current.room).toBeNull();
      expect(result.current.isConnecting).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it('should disconnect room when ending a call with room', () => {
      const { result } = renderHook(() => useIntercomStore());

      // Set up room first
      act(() => {
        result.current.setRoom(mockRoom);
      });

      expect(result.current.room).toBe(mockRoom);

      // End the call
      act(() => {
        result.current.endCall();
      });

      expect(mockRoom.disconnect).toHaveBeenCalledTimes(1);
      expect(result.current.callStatus).toBe('idle');
      expect(result.current.room).toBeNull();
      expect(result.current.isConnecting).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it('should handle room disconnect gracefully even if room.disconnect throws', () => {
      const { result } = renderHook(() => useIntercomStore());

      mockRoom.disconnect.mockImplementation(() => {
        throw new Error('Disconnect failed');
      });

      act(() => {
        result.current.setRoom(mockRoom);
      });

      // End call should not throw even if disconnect fails
      expect(() => {
        act(() => {
          result.current.endCall();
        });
      }).not.toThrow();

      // State should still be reset
      expect(result.current.callStatus).toBe('idle');
      expect(result.current.room).toBeNull();
    });
  });

  describe('setRoom Action', () => {
    it('should set room and update call status to connected', () => {
      const { result } = renderHook(() => useIntercomStore());

      act(() => {
        result.current.setRoom(mockRoom);
      });

      expect(result.current.room).toBe(mockRoom);
      expect(result.current.callStatus).toBe('connected');
      expect(result.current.isConnecting).toBe(false);
    });

    it('should set call status to idle when room is null', () => {
      const { result } = renderHook(() => useIntercomStore());

      // Set room first
      act(() => {
        result.current.setRoom(mockRoom);
      });

      expect(result.current.callStatus).toBe('connected');

      // Set room to null
      act(() => {
        result.current.setRoom(null);
      });

      expect(result.current.room).toBeNull();
      expect(result.current.callStatus).toBe('idle');
      expect(result.current.isConnecting).toBe(false);
    });

    it('should stop connecting state when room is set', () => {
      const { result } = renderHook(() => useIntercomStore());

      // Start connecting
      act(() => {
        result.current.setConnecting(true);
      });

      expect(result.current.isConnecting).toBe(true);

      // Set room should stop connecting
      act(() => {
        result.current.setRoom(mockRoom);
      });

      expect(result.current.isConnecting).toBe(false);
    });
  });

  describe('Video Element Setters', () => {
    it('should set local video element', () => {
      const { result } = renderHook(() => useIntercomStore());
      const mockVideoElement = document.createElement('video');

      act(() => {
        result.current.setLocalVideo(mockVideoElement);
      });

      expect(result.current.localVideo).toBe(mockVideoElement);
    });

    it('should set remote video element', () => {
      const { result } = renderHook(() => useIntercomStore());
      const mockVideoElement = document.createElement('video');

      act(() => {
        result.current.setRemoteVideo(mockVideoElement);
      });

      expect(result.current.remoteVideo).toBe(mockVideoElement);
    });

    it('should allow setting video elements to null', () => {
      const { result } = renderHook(() => useIntercomStore());
      const mockVideoElement = document.createElement('video');

      // Set video element first
      act(() => {
        result.current.setLocalVideo(mockVideoElement);
        result.current.setRemoteVideo(mockVideoElement);
      });

      expect(result.current.localVideo).toBe(mockVideoElement);
      expect(result.current.remoteVideo).toBe(mockVideoElement);

      // Set to null
      act(() => {
        result.current.setLocalVideo(null);
        result.current.setRemoteVideo(null);
      });

      expect(result.current.localVideo).toBeNull();
      expect(result.current.remoteVideo).toBeNull();
    });
  });

  describe('setConnecting Action', () => {
    it('should set connecting state to true', () => {
      const { result } = renderHook(() => useIntercomStore());

      act(() => {
        result.current.setConnecting(true);
      });

      expect(result.current.isConnecting).toBe(true);
    });

    it('should set connecting state to false', () => {
      const { result } = renderHook(() => useIntercomStore());

      // Set to true first
      act(() => {
        result.current.setConnecting(true);
      });

      expect(result.current.isConnecting).toBe(true);

      // Set to false
      act(() => {
        result.current.setConnecting(false);
      });

      expect(result.current.isConnecting).toBe(false);
    });
  });

  describe('setError Action', () => {
    it('should set error message', () => {
      const { result } = renderHook(() => useIntercomStore());
      const errorMessage = 'Connection failed';

      act(() => {
        result.current.setError(errorMessage);
      });

      expect(result.current.error).toBe(errorMessage);
    });

    it('should stop connecting when error is set', () => {
      const { result } = renderHook(() => useIntercomStore());

      // Start connecting first
      act(() => {
        result.current.setConnecting(true);
      });

      expect(result.current.isConnecting).toBe(true);

      // Set error should stop connecting
      act(() => {
        result.current.setError('Some error');
      });

      expect(result.current.isConnecting).toBe(false);
    });

    it('should set call status to idle when error is set', () => {
      const { result } = renderHook(() => useIntercomStore());

      // Set connected status first
      act(() => {
        result.current.setRoom(mockRoom);
      });

      expect(result.current.callStatus).toBe('connected');

      // Set error should change status to idle
      act(() => {
        result.current.setError('Some error');
      });

      expect(result.current.callStatus).toBe('idle');
    });

    it('should preserve existing call status when error is null', () => {
      const { result } = renderHook(() => useIntercomStore());

      // Set connected status first
      act(() => {
        result.current.setRoom(mockRoom);
      });

      expect(result.current.callStatus).toBe('connected');

      // Set error to null should preserve status
      act(() => {
        result.current.setError(null);
      });

      expect(result.current.callStatus).toBe('connected');
    });

    it('should clear error by setting to null', () => {
      const { result } = renderHook(() => useIntercomStore());

      // Set error first
      act(() => {
        result.current.setError('Some error');
      });

      expect(result.current.error).toBe('Some error');

      // Clear error
      act(() => {
        result.current.setError(null);
      });

      expect(result.current.error).toBeNull();
    });
  });

  describe('reset Action', () => {
    it('should reset all state to initial values', () => {
      const { result } = renderHook(() => useIntercomStore());
      const mockLocalVideo = document.createElement('video');
      const mockRemoteVideo = document.createElement('video');
      
      // Create a fresh mock room for this test
      const freshMockRoom = createMockRoom();

      // Set up some state
      act(() => {
        result.current.startCall();
        result.current.setRoom(freshMockRoom);
        result.current.setLocalVideo(mockLocalVideo);
        result.current.setRemoteVideo(mockRemoteVideo);
        // First set an error
        result.current.setError('Some error');
        // Then clear it to restore the connected status
        result.current.setError(null);
        // Manually restore the room to get back to connected state
        result.current.setRoom(freshMockRoom);
      });

      // Verify state was set
      expect(result.current.callStatus).toBe('connected');
      expect(result.current.room).toBe(freshMockRoom);
      expect(result.current.localVideo).toBe(mockLocalVideo);
      expect(result.current.remoteVideo).toBe(mockRemoteVideo);
      expect(result.current.error).toBeNull();

      // Reset
      act(() => {
        result.current.reset();
      });

      // Verify all state is back to initial
      expect(result.current.callStatus).toBe('idle');
      expect(result.current.room).toBeNull();
      expect(result.current.localVideo).toBeNull();
      expect(result.current.remoteVideo).toBeNull();
      expect(result.current.isConnecting).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it('should disconnect room during reset', () => {
      const { result } = renderHook(() => useIntercomStore());

      // Set room first
      act(() => {
        result.current.setRoom(mockRoom);
      });

      expect(result.current.room).toBe(mockRoom);

      // Reset should disconnect room
      act(() => {
        result.current.reset();
      });

      expect(mockRoom.disconnect).toHaveBeenCalledTimes(1);
      expect(result.current.room).toBeNull();
    });

    it('should handle reset gracefully when room.disconnect throws', () => {
      const { result } = renderHook(() => useIntercomStore());

      mockRoom.disconnect.mockImplementation(() => {
        throw new Error('Disconnect failed');
      });

      act(() => {
        result.current.setRoom(mockRoom);
      });

      // Reset should not throw even if disconnect fails
      expect(() => {
        act(() => {
          result.current.reset();
        });
      }).not.toThrow();

      // State should still be reset
      expect(result.current.callStatus).toBe('idle');
      expect(result.current.room).toBeNull();
    });

    it('should work when no room is present', () => {
      const { result } = renderHook(() => useIntercomStore());

      // Set some state but no room
      act(() => {
        result.current.startCall();
        result.current.setError('Some error');
      });

      // Reset should work without issues
      expect(() => {
        act(() => {
          result.current.reset();
        });
      }).not.toThrow();

      expect(result.current.callStatus).toBe('idle');
      expect(result.current.error).toBeNull();
    });
  });

  describe('State Transitions', () => {
    it('should handle typical call flow: idle -> calling -> connected -> idle', () => {
      const { result } = renderHook(() => useIntercomStore());

      // Start with idle
      expect(result.current.callStatus).toBe('idle');
      expect(result.current.isConnecting).toBe(false);

      // Start call (idle -> calling)
      act(() => {
        result.current.startCall();
      });

      expect(result.current.callStatus).toBe('calling');
      expect(result.current.isConnecting).toBe(true);

      // Connect to room (calling -> connected)
      act(() => {
        result.current.setRoom(mockRoom);
      });

      expect(result.current.callStatus).toBe('connected');
      expect(result.current.isConnecting).toBe(false);
      expect(result.current.room).toBe(mockRoom);

      // End call (connected -> idle)
      act(() => {
        result.current.endCall();
      });

      expect(result.current.callStatus).toBe('idle');
      expect(result.current.room).toBeNull();
      expect(result.current.isConnecting).toBe(false);
    });

    it('should handle error during call flow', () => {
      const { result } = renderHook(() => useIntercomStore());

      // Start call
      act(() => {
        result.current.startCall();
      });

      expect(result.current.callStatus).toBe('calling');
      expect(result.current.isConnecting).toBe(true);

      // Error occurs
      act(() => {
        result.current.setError('Connection failed');
      });

      expect(result.current.callStatus).toBe('idle');
      expect(result.current.isConnecting).toBe(false);
      expect(result.current.error).toBe('Connection failed');
    });
  });

  describe('Store Persistence', () => {
    it('should maintain state across multiple hook instances', () => {
      const { result: result1 } = renderHook(() => useIntercomStore());
      const { result: result2 } = renderHook(() => useIntercomStore());

      // Both hooks should reference the same store
      expect(result1.current.callStatus).toBe(result2.current.callStatus);

      // Update state through first hook
      act(() => {
        result1.current.startCall();
      });

      // Second hook should see the update
      expect(result2.current.callStatus).toBe('calling');
      expect(result2.current.isConnecting).toBe(true);
    });

    it('should share actions across hook instances', () => {
      const { result: result1 } = renderHook(() => useIntercomStore());
      const { result: result2 } = renderHook(() => useIntercomStore());

      // Update through first hook
      act(() => {
        result1.current.setRoom(mockRoom);
      });

      // Both hooks should see the change
      expect(result1.current.room).toBe(mockRoom);
      expect(result2.current.room).toBe(mockRoom);

      // Update through second hook
      act(() => {
        result2.current.endCall();
      });

      // Both hooks should see the change
      expect(result1.current.room).toBeNull();
      expect(result2.current.room).toBeNull();
    });
  });

  describe('Edge Cases', () => {
    it('should handle multiple startCall calls', () => {
      const { result } = renderHook(() => useIntercomStore());

      act(() => {
        result.current.startCall();
      });

      const firstState = { ...result.current };

      act(() => {
        result.current.startCall();
      });

      // Should maintain calling state
      expect(result.current.callStatus).toBe('calling');
      expect(result.current.isConnecting).toBe(true);
      expect(result.current.error).toBeNull();
    });

    it('should handle multiple endCall calls', () => {
      const { result } = renderHook(() => useIntercomStore());

      // End call multiple times should not cause issues
      act(() => {
        result.current.endCall();
        result.current.endCall();
      });

      expect(result.current.callStatus).toBe('idle');
      expect(result.current.room).toBeNull();
    });

    it('should handle setting the same room multiple times', () => {
      const { result } = renderHook(() => useIntercomStore());

      act(() => {
        result.current.setRoom(mockRoom);
      });

      expect(result.current.room).toBe(mockRoom);

      // Setting same room again should not cause issues
      act(() => {
        result.current.setRoom(mockRoom);
      });

      expect(result.current.room).toBe(mockRoom);
      expect(result.current.callStatus).toBe('connected');
    });

    it('should handle rapid state changes', () => {
      const { result } = renderHook(() => useIntercomStore());

      // Rapid state changes
      act(() => {
        result.current.startCall();
        result.current.setError('Error');
        result.current.setRoom(mockRoom);
        result.current.endCall();
        result.current.reset();
      });

      // Should end up in initial state
      expect(result.current.callStatus).toBe('idle');
      expect(result.current.room).toBeNull();
      expect(result.current.isConnecting).toBe(false);
      expect(result.current.error).toBeNull();
    });
  });
});