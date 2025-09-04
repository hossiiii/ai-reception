/**
 * VideoMonitor Component Tests
 * Tests for components/VideoMonitor.tsx
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { VideoMonitor } from '@/components/VideoMonitor';

describe('VideoMonitor Component', () => {
  // Mock video element refs for callbacks
  const mockOnLocalVideoRef = jest.fn();
  const mockOnRemoteVideoRef = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Component Rendering', () => {
    it('should render the video monitor container', () => {
      const { container } = render(
        <VideoMonitor
          callStatus="idle"
          onLocalVideoRef={mockOnLocalVideoRef}
          onRemoteVideoRef={mockOnRemoteVideoRef}
        />
      );

      const videoContainer = container.firstChild;
      expect(videoContainer).toHaveClass('w-56', 'h-40', 'bg-gray-900', 'rounded-lg');
    });

    it('should call ref callbacks when video elements are created', () => {
      render(
        <VideoMonitor
          callStatus="connected"
          onLocalVideoRef={mockOnLocalVideoRef}
          onRemoteVideoRef={mockOnRemoteVideoRef}
        />
      );

      // For connected state, both video elements should be present
      expect(mockOnLocalVideoRef).toHaveBeenCalledWith(expect.any(HTMLVideoElement));
      expect(mockOnRemoteVideoRef).toHaveBeenCalledWith(expect.any(HTMLVideoElement));
    });

    it('should work without ref callbacks', () => {
      expect(() => {
        render(<VideoMonitor callStatus="idle" />);
      }).not.toThrow();
    });
  });

  describe('Idle State', () => {
    it('should display idle message for idle status', () => {
      render(<VideoMonitor callStatus="idle" />);
      
      expect(screen.getByText('待機中')).toBeInTheDocument();
      expect(screen.queryByText('呼び出し中...')).not.toBeInTheDocument();
      expect(screen.queryByRole('video')).not.toBeInTheDocument();
    });

    it('should display idle state with correct styling', () => {
      render(<VideoMonitor callStatus="idle" />);
      
      const idleText = screen.getByText('待機中');
      expect(idleText).toHaveClass('text-gray-400', 'text-lg');
    });
  });

  describe('Calling State', () => {
    it('should display calling status with spinner', () => {
      render(<VideoMonitor callStatus="calling" />);
      
      expect(screen.getByText('呼び出し中...')).toBeInTheDocument();
      expect(screen.queryByText('待機中')).not.toBeInTheDocument();
      expect(screen.queryByRole('video')).not.toBeInTheDocument();
    });

    it('should display calling state with correct styling', () => {
      render(<VideoMonitor callStatus="calling" />);
      
      const callingText = screen.getByText('呼び出し中...');
      expect(callingText).toHaveClass('text-blue-400', 'font-semibold', 'text-lg');
    });

    it('should have animated spinner during calling state', () => {
      render(<VideoMonitor callStatus="calling" />);
      
      // Check for spinner element with animation class
      const spinner = screen.getByText('呼び出し中...').previousSibling;
      expect(spinner).toHaveClass('animate-spin');
    });
  });

  describe('Connected State', () => {
    it('should render video elements when connected', () => {
      const { container } = render(<VideoMonitor callStatus="connected" />);
      
      const videos = container.querySelectorAll('video');
      expect(videos).toHaveLength(2);
      
      // Check for remote video (main) - should have rounded-lg class
      const remoteVideo = Array.from(videos).find(video => 
        video.classList.contains('rounded-lg')
      );
      expect(remoteVideo).toBeInTheDocument();
      
      // Check for local video (PiP) - should have muted attribute
      const localVideo = Array.from(videos).find(video => 
        video.hasAttribute('muted')
      );
      expect(localVideo).toBeInTheDocument();
    });

    it('should have correct video attributes', () => {
      const { container } = render(<VideoMonitor callStatus="connected" />);
      
      const videos = container.querySelectorAll('video');
      
      videos.forEach(video => {
        expect(video).toHaveAttribute('autoPlay');
        expect(video).toHaveAttribute('playsInline');
      });
      
      // Local video should be muted
      const localVideo = Array.from(videos).find(video => video.hasAttribute('muted'));
      expect(localVideo).toHaveAttribute('muted');
    });

    it('should position local video as picture-in-picture', () => {
      const { container } = render(<VideoMonitor callStatus="connected" />);
      
      // Check if it has PiP positioning classes
      const pipContainer = container.querySelector('.absolute.bottom-2.right-2');
      expect(pipContainer).toBeInTheDocument();
      expect(pipContainer).toHaveClass('w-16', 'h-12');
    });

    it('should style remote video for full coverage', () => {
      const { container } = render(<VideoMonitor callStatus="connected" />);
      
      const videos = container.querySelectorAll('video');
      const remoteVideo = Array.from(videos).find(video => 
        video.classList.contains('rounded-lg')
      );
      
      expect(remoteVideo).toHaveClass('object-cover', 'rounded-lg');
    });
  });

  describe('Video Element References', () => {
    it('should call onLocalVideoRef with correct element', () => {
      render(
        <VideoMonitor
          callStatus="connected"
          onLocalVideoRef={mockOnLocalVideoRef}
        />
      );

      expect(mockOnLocalVideoRef).toHaveBeenCalledTimes(1);
      const calledElement = mockOnLocalVideoRef.mock.calls[0][0];
      expect(calledElement).toBeInstanceOf(HTMLVideoElement);
    });

    it('should call onRemoteVideoRef with correct element', () => {
      render(
        <VideoMonitor
          callStatus="connected"
          onRemoteVideoRef={mockOnRemoteVideoRef}
        />
      );

      expect(mockOnRemoteVideoRef).toHaveBeenCalledTimes(1);
      const calledElement = mockOnRemoteVideoRef.mock.calls[0][0];
      expect(calledElement).toBeInstanceOf(HTMLVideoElement);
    });

    it('should call ref callbacks on state change to connected', () => {
      const { rerender } = render(
        <VideoMonitor
          callStatus="idle"
          onLocalVideoRef={mockOnLocalVideoRef}
          onRemoteVideoRef={mockOnRemoteVideoRef}
        />
      );

      // Initial state - no videos, no ref calls
      expect(mockOnLocalVideoRef).not.toHaveBeenCalled();
      expect(mockOnRemoteVideoRef).not.toHaveBeenCalled();

      // Change to connected state
      rerender(
        <VideoMonitor
          callStatus="connected"
          onLocalVideoRef={mockOnLocalVideoRef}
          onRemoteVideoRef={mockOnRemoteVideoRef}
        />
      );

      // Should call refs after rendering videos
      expect(mockOnLocalVideoRef).toHaveBeenCalledWith(expect.any(HTMLVideoElement));
      expect(mockOnRemoteVideoRef).toHaveBeenCalledWith(expect.any(HTMLVideoElement));
    });

    it('should only call ref callbacks when elements exist', () => {
      render(
        <VideoMonitor
          callStatus="idle"
          onLocalVideoRef={mockOnLocalVideoRef}
          onRemoteVideoRef={mockOnRemoteVideoRef}
        />
      );

      // No video elements in idle state, so no ref calls
      expect(mockOnLocalVideoRef).not.toHaveBeenCalled();
      expect(mockOnRemoteVideoRef).not.toHaveBeenCalled();
    });
  });

  describe('State Transitions', () => {
    it('should handle state transitions correctly', () => {
      const { rerender } = render(<VideoMonitor callStatus="idle" />);
      
      // Start with idle
      expect(screen.getByText('待機中')).toBeInTheDocument();

      // Transition to calling
      rerender(<VideoMonitor callStatus="calling" />);
      expect(screen.getByText('呼び出し中...')).toBeInTheDocument();
      expect(screen.queryByText('待機中')).not.toBeInTheDocument();

      // Transition to connected
      rerender(<VideoMonitor callStatus="connected" />);
      const connectedVideos = container.querySelectorAll('video');
      expect(connectedVideos).toHaveLength(2);
      expect(screen.queryByText('呼び出し中...')).not.toBeInTheDocument();

      // Back to idle
      rerender(<VideoMonitor callStatus="idle" />);
      expect(screen.getByText('待機中')).toBeInTheDocument();
      const idleVideos = container.querySelectorAll('video');
      expect(idleVideos).toHaveLength(0);
    });
  });

  describe('Responsive Behavior', () => {
    it('should have responsive container dimensions', () => {
      const { container } = render(<VideoMonitor callStatus="idle" />);
      
      const videoContainer = container.firstChild as HTMLElement;
      expect(videoContainer).toHaveClass('w-56', 'h-40');
    });

    it('should maintain aspect ratio in different states', () => {
      const { container, rerender } = render(<VideoMonitor callStatus="idle" />);
      
      const getContainerClasses = () => (container.firstChild as HTMLElement).className;
      
      const idleClasses = getContainerClasses();
      
      rerender(<VideoMonitor callStatus="calling" />);
      expect(getContainerClasses()).toBe(idleClasses);
      
      rerender(<VideoMonitor callStatus="connected" />);
      expect(getContainerClasses()).toBe(idleClasses);
    });
  });

  describe('Accessibility', () => {
    it('should have proper video elements', () => {
      const { container } = render(<VideoMonitor callStatus="connected" />);
      
      const videos = container.querySelectorAll('video');
      expect(videos).toHaveLength(2);
      
      videos.forEach(video => {
        expect(video.tagName).toBe('VIDEO');
      });
    });

    it('should have semantic content for screen readers in idle state', () => {
      render(<VideoMonitor callStatus="idle" />);
      
      expect(screen.getByText('待機中')).toBeInTheDocument();
    });

    it('should have semantic content for screen readers in calling state', () => {
      render(<VideoMonitor callStatus="calling" />);
      
      expect(screen.getByText('呼び出し中...')).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('should handle undefined status gracefully', () => {
      expect(() => {
        render(<VideoMonitor callStatus={undefined as any} />);
      }).not.toThrow();
    });

    it('should default to idle display for unknown status', () => {
      render(<VideoMonitor callStatus={'unknown' as any} />);
      
      // Should fall back to idle state display
      expect(screen.getByText('待機中')).toBeInTheDocument();
    });
  });
});