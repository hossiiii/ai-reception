/**
 * IntercomDevice Component Tests
 * Tests for components/IntercomDevice.tsx
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { IntercomDevice } from '@/components/IntercomDevice';
import { useIntercomStore } from '@/stores/useIntercomStore';
import { connect } from 'twilio-video';

// Mock dependencies
jest.mock('twilio-video');
jest.mock('@/stores/useIntercomStore');

const mockConnect = connect as jest.MockedFunction<typeof connect>;
const mockUseIntercomStore = useIntercomStore as jest.MockedFunction<typeof useIntercomStore>;

// Mock fetch globally
global.fetch = jest.fn();
const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;

describe('IntercomDevice Component', () => {
  // Mock store state and actions
  const mockStoreActions = {
    startCall: jest.fn(),
    endCall: jest.fn(),
    setRoom: jest.fn(),
    setLocalVideo: jest.fn(),
    setRemoteVideo: jest.fn(),
    setConnecting: jest.fn(),
    setError: jest.fn(),
    reset: jest.fn(),
  };

  const defaultStoreState = {
    callStatus: 'idle' as const,
    room: null,
    localVideo: null,
    remoteVideo: null,
    isConnecting: false,
    error: null,
    ...mockStoreActions,
  };

  // Mock Twilio room
  const mockTwilioRoom = {
    disconnect: jest.fn(),
    on: jest.fn(),
    localParticipant: {
      videoTracks: new Map([
        ['track1', {
          track: {
            attach: jest.fn(),
          },
        }],
      ]),
    },
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockUseIntercomStore.mockReturnValue(defaultStoreState);
    
    // Mock successful API response
    mockFetch.mockResolvedValue({
      ok: true,
      json: jest.fn().mockResolvedValue({
        video_room: {
          access_token: 'test-token',
          room_name: 'test-room-name',
        },
      }),
    } as any);
  });

  describe('Component Rendering', () => {
    it('should render the intercom device interface', () => {
      render(<IntercomDevice />);
      
      // Check basic structural elements
      expect(screen.getByRole('button')).toBeInTheDocument();
      expect(screen.getByText('呼出')).toBeInTheDocument();
      expect(screen.getByText('待機中')).toBeInTheDocument();
    });

    it('should apply custom className', () => {
      const customClass = 'custom-intercom-class';
      const { container } = render(<IntercomDevice className={customClass} />);
      
      expect(container.firstChild).toHaveClass(customClass);
    });

    it('should use provided roomName prop', () => {
      render(<IntercomDevice roomName="custom-room" />);
      
      // Room name is used internally, so we verify by checking if component renders without error
      expect(screen.getByText('呼出')).toBeInTheDocument();
    });
  });

  describe('Call Status States', () => {
    it('should display idle state correctly', () => {
      mockUseIntercomStore.mockReturnValue({
        ...defaultStoreState,
        callStatus: 'idle',
      });

      render(<IntercomDevice />);
      
      expect(screen.getByText('待機中')).toBeInTheDocument();
      expect(screen.getByText('呼出')).toBeInTheDocument();
      expect(screen.queryByText('接続中...')).not.toBeInTheDocument();
    });

    it('should display calling state correctly', () => {
      mockUseIntercomStore.mockReturnValue({
        ...defaultStoreState,
        callStatus: 'calling',
        isConnecting: true,
      });

      render(<IntercomDevice />);
      
      expect(screen.getByText('呼び出し中...')).toBeInTheDocument();
      expect(screen.getByText('接続中...')).toBeInTheDocument();
    });

    it('should display connected state correctly', () => {
      mockUseIntercomStore.mockReturnValue({
        ...defaultStoreState,
        callStatus: 'connected',
      });

      render(<IntercomDevice />);
      
      expect(screen.getByText('終了')).toBeInTheDocument();
      expect(screen.queryByText('呼出')).not.toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    it('should display error message when error exists', () => {
      const errorMessage = 'Connection failed';
      mockUseIntercomStore.mockReturnValue({
        ...defaultStoreState,
        error: errorMessage,
      });

      render(<IntercomDevice />);
      
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });

    it('should not display error section when no error', () => {
      render(<IntercomDevice />);
      
      // Error section should not be rendered
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });
  });

  describe('Call Initiation', () => {
    it('should handle successful call connection', async () => {
      mockConnect.mockResolvedValue(mockTwilioRoom as any);
      
      render(<IntercomDevice />);
      
      const callButton = screen.getByRole('button');
      
      await act(async () => {
        fireEvent.click(callButton);
      });

      // Verify API call was made
      expect(mockFetch).toHaveBeenCalledWith('/api/video/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          visitorName: 'Visitor',
          purpose: 'intercom'
        }),
      });

      // Verify store actions were called
      expect(mockStoreActions.startCall).toHaveBeenCalled();
      
      await waitFor(() => {
        expect(mockConnect).toHaveBeenCalledWith('test-token', {
          name: 'test-room-name',
          audio: true,
          video: { width: 640, height: 480 }
        });
        expect(mockStoreActions.setRoom).toHaveBeenCalledWith(mockTwilioRoom);
        expect(mockStoreActions.setConnecting).toHaveBeenCalledWith(false);
      });
    });

    it('should handle API error during call initiation', async () => {
      const errorMessage = 'Failed to create video room';
      mockFetch.mockResolvedValue({
        ok: false,
        status: 500,
      } as any);
      
      render(<IntercomDevice />);
      
      const callButton = screen.getByRole('button');
      
      await act(async () => {
        fireEvent.click(callButton);
      });

      await waitFor(() => {
        expect(mockStoreActions.setError).toHaveBeenCalledWith(errorMessage);
        expect(mockStoreActions.setConnecting).toHaveBeenCalledWith(false);
        expect(mockConnect).not.toHaveBeenCalled();
      });
    });

    it('should handle Twilio connection error', async () => {
      const twilioError = new Error('Twilio connection failed');
      mockConnect.mockRejectedValue(twilioError);
      
      render(<IntercomDevice />);
      
      const callButton = screen.getByRole('button');
      
      await act(async () => {
        fireEvent.click(callButton);
      });

      await waitFor(() => {
        expect(mockStoreActions.setError).toHaveBeenCalledWith('Twilio connection failed');
        expect(mockStoreActions.setConnecting).toHaveBeenCalledWith(false);
      });
    });

    it('should handle generic error during connection', async () => {
      // Mock a non-Error object being thrown
      mockConnect.mockRejectedValue('String error');
      
      render(<IntercomDevice />);
      
      const callButton = screen.getByRole('button');
      
      await act(async () => {
        fireEvent.click(callButton);
      });

      await waitFor(() => {
        expect(mockStoreActions.setError).toHaveBeenCalledWith('接続に失敗しました');
        expect(mockStoreActions.setConnecting).toHaveBeenCalledWith(false);
      });
    });
  });

  describe('Call Termination', () => {
    it('should handle call disconnection', () => {
      mockUseIntercomStore.mockReturnValue({
        ...defaultStoreState,
        callStatus: 'connected',
      });

      render(<IntercomDevice />);
      
      const hangupButton = screen.getByRole('button');
      fireEvent.click(hangupButton);

      expect(mockStoreActions.endCall).toHaveBeenCalled();
    });
  });

  describe('Twilio Room Event Handling', () => {
    it('should setup room event listeners after successful connection', async () => {
      mockConnect.mockResolvedValue(mockTwilioRoom as any);
      
      render(<IntercomDevice />);
      
      const callButton = screen.getByRole('button');
      
      await act(async () => {
        fireEvent.click(callButton);
      });

      await waitFor(() => {
        expect(mockTwilioRoom.on).toHaveBeenCalledWith('participantConnected', expect.any(Function));
        expect(mockTwilioRoom.on).toHaveBeenCalledWith('participantDisconnected', expect.any(Function));
        expect(mockTwilioRoom.on).toHaveBeenCalledWith('disconnected', expect.any(Function));
      });
    });

    it('should handle participant connection event', async () => {
      let participantConnectedHandler: any;
      
      mockTwilioRoom.on.mockImplementation((event, handler) => {
        if (event === 'participantConnected') {
          participantConnectedHandler = handler;
        }
      });
      
      mockConnect.mockResolvedValue(mockTwilioRoom as any);
      
      const mockRemoteVideo = document.createElement('video');
      mockUseIntercomStore.mockReturnValue({
        ...defaultStoreState,
        remoteVideo: mockRemoteVideo,
      });
      
      render(<IntercomDevice />);
      
      const callButton = screen.getByRole('button');
      
      await act(async () => {
        fireEvent.click(callButton);
      });

      // Simulate participant connected
      if (participantConnectedHandler) {
        const mockParticipant = {
          identity: 'test-participant',
          videoTracks: new Map([
            ['track1', {
              track: {
                attach: jest.fn(),
              },
            }],
          ]),
          on: jest.fn(),
        };

        participantConnectedHandler(mockParticipant);
        
        expect(mockParticipant.on).toHaveBeenCalledWith('trackSubscribed', expect.any(Function));
      }
    });

    it('should handle room disconnection event', async () => {
      let disconnectedHandler: any;
      
      mockTwilioRoom.on.mockImplementation((event, handler) => {
        if (event === 'disconnected') {
          disconnectedHandler = handler;
        }
      });
      
      mockConnect.mockResolvedValue(mockTwilioRoom as any);
      
      render(<IntercomDevice />);
      
      const callButton = screen.getByRole('button');
      
      await act(async () => {
        fireEvent.click(callButton);
      });

      // Simulate room disconnection
      if (disconnectedHandler) {
        disconnectedHandler();
        expect(mockStoreActions.setRoom).toHaveBeenCalledWith(null);
      }
    });
  });

  describe('Component Cleanup', () => {
    it('should disconnect from room on unmount', () => {
      const mockRoom = {
        disconnect: jest.fn(),
      };
      
      mockUseIntercomStore.mockReturnValue({
        ...defaultStoreState,
        room: mockRoom as any,
      });

      const { unmount } = render(<IntercomDevice />);
      
      unmount();
      
      expect(mockRoom.disconnect).toHaveBeenCalled();
    });

    it('should not error on unmount when no room exists', () => {
      const { unmount } = render(<IntercomDevice />);
      
      // Should not throw error
      expect(() => unmount()).not.toThrow();
    });
  });

  describe('Video Element Setup', () => {
    it('should call setLocalVideo with video element reference', () => {
      render(<IntercomDevice />);
      
      // Verify setLocalVideo is called for video element setup
      expect(mockStoreActions.setLocalVideo).toHaveBeenCalled();
    });

    it('should call setRemoteVideo with video element reference', () => {
      render(<IntercomDevice />);
      
      // Verify setRemoteVideo is called for video element setup
      expect(mockStoreActions.setRemoteVideo).toHaveBeenCalled();
    });
  });

  describe('Button State Handling', () => {
    it('should disable button when connecting', () => {
      mockUseIntercomStore.mockReturnValue({
        ...defaultStoreState,
        isConnecting: true,
      });

      render(<IntercomDevice />);
      
      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
    });

    it('should enable button when not connecting', () => {
      render(<IntercomDevice />);
      
      const button = screen.getByRole('button');
      expect(button).toBeEnabled();
    });
  });
});