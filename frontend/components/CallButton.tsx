'use client';

import React from 'react';
import { Bell, PhoneOff } from 'lucide-react';
import { Button } from '@/components/ui';

interface CallButtonProps {
  isConnected: boolean;
  isConnecting: boolean;
  onCall: () => void;
  onHangup: () => void;
  disabled?: boolean;
}

export const CallButton: React.FC<CallButtonProps> = ({
  isConnected,
  isConnecting,
  onCall,
  onHangup,
  disabled = false,
}) => {
  if (isConnected) {
    return (
      <div className="flex flex-col items-center space-y-2">
        <Button
          onClick={onHangup}
          disabled={disabled}
          className="w-24 h-24 rounded-full bg-red-500 hover:bg-red-600 text-white text-2xl flex items-center justify-center shadow-lg transition-transform transform hover:scale-105 disabled:transform-none disabled:hover:bg-red-500"
        >
          <PhoneOff size={36} />
        </Button>
        <div className="text-gray-700 font-semibold tracking-wide text-sm">
          終了
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center space-y-2">
      <Button
        onClick={onCall}
        disabled={disabled || isConnecting}
        className="w-24 h-24 rounded-full bg-green-500 hover:bg-green-600 text-white text-2xl flex items-center justify-center shadow-lg transition-transform transform hover:scale-105 disabled:transform-none disabled:hover:bg-green-500"
      >
        {isConnecting ? (
          <div className="w-8 h-8 border-3 border-white border-t-transparent rounded-full animate-spin" />
        ) : (
          <Bell size={36} />
        )}
      </Button>
      <div className="text-gray-700 font-semibold tracking-wide text-sm">
        {isConnecting ? '接続中...' : '呼出'}
      </div>
    </div>
  );
};