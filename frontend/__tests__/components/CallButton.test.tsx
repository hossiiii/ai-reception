/**
 * CallButton Component Tests
 * Tests for components/CallButton.tsx
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { CallButton } from '@/components/CallButton';

describe('CallButton Component', () => {
  const mockOnCall = jest.fn();
  const mockOnHangup = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Call Button (Not Connected)', () => {
    it('should render call button when not connected', () => {
      render(
        <CallButton
          isConnected={false}
          isConnecting={false}
          onCall={mockOnCall}
          onHangup={mockOnHangup}
        />
      );

      const button = screen.getByRole('button');
      expect(button).toBeInTheDocument();
      expect(screen.getByText('呼出')).toBeInTheDocument();
    });

    it('should have correct styling for call button', () => {
      render(
        <CallButton
          isConnected={false}
          isConnecting={false}
          onCall={mockOnCall}
          onHangup={mockOnHangup}
        />
      );

      const button = screen.getByRole('button');
      expect(button).toHaveClass(
        'w-24', 'h-24', 'rounded-full', 'bg-green-500', 'hover:bg-green-600'
      );
    });

    it('should display bell icon when not connecting', () => {
      render(
        <CallButton
          isConnected={false}
          isConnecting={false}
          onCall={mockOnCall}
          onHangup={mockOnHangup}
        />
      );

      // Check for Bell icon (lucide-react icons have data-testid)
      const bellIcon = screen.getByRole('button').querySelector('svg');
      expect(bellIcon).toBeInTheDocument();
    });

    it('should call onCall when clicked', () => {
      render(
        <CallButton
          isConnected={false}
          isConnecting={false}
          onCall={mockOnCall}
          onHangup={mockOnHangup}
        />
      );

      const button = screen.getByRole('button');
      fireEvent.click(button);

      expect(mockOnCall).toHaveBeenCalledTimes(1);
      expect(mockOnHangup).not.toHaveBeenCalled();
    });

    it('should be enabled when not connecting or disabled', () => {
      render(
        <CallButton
          isConnected={false}
          isConnecting={false}
          onCall={mockOnCall}
          onHangup={mockOnHangup}
        />
      );

      const button = screen.getByRole('button');
      expect(button).toBeEnabled();
    });
  });

  describe('Call Button (Connecting State)', () => {
    it('should display connecting text when connecting', () => {
      render(
        <CallButton
          isConnected={false}
          isConnecting={true}
          onCall={mockOnCall}
          onHangup={mockOnHangup}
        />
      );

      expect(screen.getByText('接続中...')).toBeInTheDocument();
      expect(screen.queryByText('呼出')).not.toBeInTheDocument();
    });

    it('should display spinner when connecting', () => {
      render(
        <CallButton
          isConnected={false}
          isConnecting={true}
          onCall={mockOnCall}
          onHangup={mockOnHangup}
        />
      );

      // Check for spinner with animation
      const spinner = screen.getByRole('button').querySelector('.animate-spin');
      expect(spinner).toBeInTheDocument();
      expect(spinner).toHaveClass('border-3', 'border-white', 'border-t-transparent', 'rounded-full');
    });

    it('should be disabled when connecting', () => {
      render(
        <CallButton
          isConnected={false}
          isConnecting={true}
          onCall={mockOnCall}
          onHangup={mockOnHangup}
        />
      );

      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
    });

    it('should not call onCall when clicked while connecting', () => {
      render(
        <CallButton
          isConnected={false}
          isConnecting={true}
          onCall={mockOnCall}
          onHangup={mockOnHangup}
        />
      );

      const button = screen.getByRole('button');
      fireEvent.click(button);

      expect(mockOnCall).not.toHaveBeenCalled();
    });

    it('should maintain green styling when connecting', () => {
      render(
        <CallButton
          isConnected={false}
          isConnecting={true}
          onCall={mockOnCall}
          onHangup={mockOnHangup}
        />
      );

      const button = screen.getByRole('button');
      expect(button).toHaveClass('bg-green-500');
    });
  });

  describe('Hangup Button (Connected State)', () => {
    it('should render hangup button when connected', () => {
      render(
        <CallButton
          isConnected={true}
          isConnecting={false}
          onCall={mockOnCall}
          onHangup={mockOnHangup}
        />
      );

      const button = screen.getByRole('button');
      expect(button).toBeInTheDocument();
      expect(screen.getByText('終了')).toBeInTheDocument();
      expect(screen.queryByText('呼出')).not.toBeInTheDocument();
    });

    it('should have correct styling for hangup button', () => {
      render(
        <CallButton
          isConnected={true}
          isConnecting={false}
          onCall={mockOnCall}
          onHangup={mockOnHangup}
        />
      );

      const button = screen.getByRole('button');
      expect(button).toHaveClass(
        'w-24', 'h-24', 'rounded-full', 'bg-red-500', 'hover:bg-red-600'
      );
    });

    it('should display phone-off icon when connected', () => {
      render(
        <CallButton
          isConnected={true}
          isConnecting={false}
          onCall={mockOnCall}
          onHangup={mockOnHangup}
        />
      );

      // Check for PhoneOff icon
      const phoneOffIcon = screen.getByRole('button').querySelector('svg');
      expect(phoneOffIcon).toBeInTheDocument();
    });

    it('should call onHangup when clicked', () => {
      render(
        <CallButton
          isConnected={true}
          isConnecting={false}
          onCall={mockOnCall}
          onHangup={mockOnHangup}
        />
      );

      const button = screen.getByRole('button');
      fireEvent.click(button);

      expect(mockOnHangup).toHaveBeenCalledTimes(1);
      expect(mockOnCall).not.toHaveBeenCalled();
    });

    it('should be enabled when connected and not disabled', () => {
      render(
        <CallButton
          isConnected={true}
          isConnecting={false}
          onCall={mockOnCall}
          onHangup={mockOnHangup}
        />
      );

      const button = screen.getByRole('button');
      expect(button).toBeEnabled();
    });
  });

  describe('Disabled State', () => {
    it('should be disabled when disabled prop is true (not connected)', () => {
      render(
        <CallButton
          isConnected={false}
          isConnecting={false}
          onCall={mockOnCall}
          onHangup={mockOnHangup}
          disabled={true}
        />
      );

      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
    });

    it('should be disabled when disabled prop is true (connected)', () => {
      render(
        <CallButton
          isConnected={true}
          isConnecting={false}
          onCall={mockOnCall}
          onHangup={mockOnHangup}
          disabled={true}
        />
      );

      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
    });

    it('should not call handlers when disabled and clicked (not connected)', () => {
      render(
        <CallButton
          isConnected={false}
          isConnecting={false}
          onCall={mockOnCall}
          onHangup={mockOnHangup}
          disabled={true}
        />
      );

      const button = screen.getByRole('button');
      fireEvent.click(button);

      expect(mockOnCall).not.toHaveBeenCalled();
    });

    it('should not call handlers when disabled and clicked (connected)', () => {
      render(
        <CallButton
          isConnected={true}
          isConnecting={false}
          onCall={mockOnCall}
          onHangup={mockOnHangup}
          disabled={true}
        />
      );

      const button = screen.getByRole('button');
      fireEvent.click(button);

      expect(mockOnHangup).not.toHaveBeenCalled();
    });
  });

  describe('Combined State Logic', () => {
    it('should be disabled when both connecting and disabled prop are true', () => {
      render(
        <CallButton
          isConnected={false}
          isConnecting={true}
          onCall={mockOnCall}
          onHangup={mockOnHangup}
          disabled={true}
        />
      );

      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
    });

    it('should be disabled when only connecting is true', () => {
      render(
        <CallButton
          isConnected={false}
          isConnecting={true}
          onCall={mockOnCall}
          onHangup={mockOnHangup}
          disabled={false}
        />
      );

      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
    });

    it('should be disabled when only disabled prop is true', () => {
      render(
        <CallButton
          isConnected={false}
          isConnecting={false}
          onCall={mockOnCall}
          onHangup={mockOnHangup}
          disabled={true}
        />
      );

      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
    });
  });

  describe('Visual States and Transitions', () => {
    it('should have hover effects when enabled (not connected)', () => {
      render(
        <CallButton
          isConnected={false}
          isConnecting={false}
          onCall={mockOnCall}
          onHangup={mockOnHangup}
        />
      );

      const button = screen.getByRole('button');
      expect(button).toHaveClass('hover:bg-green-600', 'transform', 'hover:scale-105');
    });

    it('should have hover effects when enabled (connected)', () => {
      render(
        <CallButton
          isConnected={true}
          isConnecting={false}
          onCall={mockOnCall}
          onHangup={mockOnHangup}
        />
      );

      const button = screen.getByRole('button');
      expect(button).toHaveClass('hover:bg-red-600', 'transform', 'hover:scale-105');
    });

    it('should disable hover effects when disabled', () => {
      render(
        <CallButton
          isConnected={false}
          isConnecting={false}
          onCall={mockOnCall}
          onHangup={mockOnHangup}
          disabled={true}
        />
      );

      const button = screen.getByRole('button');
      expect(button).toHaveClass('disabled:transform-none');
    });
  });

  describe('Layout and Structure', () => {
    it('should have consistent layout structure for call state', () => {
      const { container } = render(
        <CallButton
          isConnected={false}
          isConnecting={false}
          onCall={mockOnCall}
          onHangup={mockOnHangup}
        />
      );

      const wrapper = container.firstChild;
      expect(wrapper).toHaveClass('flex', 'flex-col', 'items-center', 'space-y-2');
    });

    it('should have consistent layout structure for hangup state', () => {
      const { container } = render(
        <CallButton
          isConnected={true}
          isConnecting={false}
          onCall={mockOnCall}
          onHangup={mockOnHangup}
        />
      );

      const wrapper = container.firstChild;
      expect(wrapper).toHaveClass('flex', 'flex-col', 'items-center', 'space-y-2');
    });

    it('should maintain consistent button sizing across states', () => {
      const { rerender } = render(
        <CallButton
          isConnected={false}
          isConnecting={false}
          onCall={mockOnCall}
          onHangup={mockOnHangup}
        />
      );

      let button = screen.getByRole('button');
      const callButtonClasses = button.className;
      expect(button).toHaveClass('w-24', 'h-24', 'rounded-full');

      rerender(
        <CallButton
          isConnected={true}
          isConnecting={false}
          onCall={mockOnCall}
          onHangup={mockOnHangup}
        />
      );

      button = screen.getByRole('button');
      expect(button).toHaveClass('w-24', 'h-24', 'rounded-full');
    });
  });

  describe('Accessibility', () => {
    it('should have button role for call state', () => {
      render(
        <CallButton
          isConnected={false}
          isConnecting={false}
          onCall={mockOnCall}
          onHangup={mockOnHangup}
        />
      );

      expect(screen.getByRole('button')).toBeInTheDocument();
    });

    it('should have button role for hangup state', () => {
      render(
        <CallButton
          isConnected={true}
          isConnecting={false}
          onCall={mockOnCall}
          onHangup={mockOnHangup}
        />
      );

      expect(screen.getByRole('button')).toBeInTheDocument();
    });

    it('should have descriptive text for screen readers', () => {
      render(
        <CallButton
          isConnected={false}
          isConnecting={false}
          onCall={mockOnCall}
          onHangup={mockOnHangup}
        />
      );

      expect(screen.getByText('呼出')).toBeInTheDocument();
    });

    it('should update descriptive text based on state', () => {
      const { rerender } = render(
        <CallButton
          isConnected={false}
          isConnecting={false}
          onCall={mockOnCall}
          onHangup={mockOnHangup}
        />
      );

      expect(screen.getByText('呼出')).toBeInTheDocument();

      rerender(
        <CallButton
          isConnected={false}
          isConnecting={true}
          onCall={mockOnCall}
          onHangup={mockOnHangup}
        />
      );

      expect(screen.getByText('接続中...')).toBeInTheDocument();

      rerender(
        <CallButton
          isConnected={true}
          isConnecting={false}
          onCall={mockOnCall}
          onHangup={mockOnHangup}
        />
      );

      expect(screen.getByText('終了')).toBeInTheDocument();
    });
  });

  describe('Default Props', () => {
    it('should use default disabled value of false', () => {
      render(
        <CallButton
          isConnected={false}
          isConnecting={false}
          onCall={mockOnCall}
          onHangup={mockOnHangup}
        />
      );

      const button = screen.getByRole('button');
      expect(button).toBeEnabled();
    });
  });
});