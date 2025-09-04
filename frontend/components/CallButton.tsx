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
      <div className="flex flex-col items-center space-y-2 md:space-y-4">
        <Button
          onClick={onHangup}
          disabled={disabled}
          className="rounded-full bg-red-500 hover:bg-red-600 text-white text-2xl flex items-center justify-center shadow-lg transition-transform transform hover:scale-105 disabled:transform-none disabled:hover:bg-red-500
            /* Mobile: small button */
            w-20 h-20
            /* Tablet: large button for touch */
            md:w-40 md:h-40
            /* PC: smaller button to save space */
            lg:w-28 lg:h-28"
        >
          <PhoneOff className="
            /* Mobile: small icon */
            w-8 h-8
            /* Tablet: large icon */
            md:w-16 md:h-16
            /* PC: smaller icon */
            lg:w-10 lg:h-10" />
        </Button>
        <div className="text-gray-700 font-semibold tracking-wide text-sm md:text-base lg:text-lg">
          終了
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center space-y-2 md:space-y-4">
      <Button
        onClick={onCall}
        disabled={disabled || isConnecting}
        className="rounded-full bg-green-500 hover:bg-green-600 text-white text-2xl flex items-center justify-center shadow-lg transition-transform transform hover:scale-105 disabled:transform-none disabled:hover:bg-green-500
          /* Mobile: small button */
          w-20 h-20
          /* Tablet: large button for touch */
          md:w-40 md:h-40
          /* PC: smaller button to save space */
          lg:w-28 lg:h-28"
      >
        {isConnecting ? (
          <div className="border-white border-t-transparent rounded-full animate-spin
            /* Mobile: small spinner */
            w-6 h-6 border-2
            /* Tablet: large spinner */
            md:w-12 md:h-12 md:border-4
            /* PC: medium spinner */
            lg:w-10 lg:h-10 lg:border-3" />
        ) : (
          <Bell className="
            /* Mobile: small icon */
            w-8 h-8
            /* Tablet: large icon */
            md:w-16 md:h-16
            /* PC: smaller icon */
            lg:w-10 lg:h-10" />
        )}
      </Button>
      <div className="text-gray-700 font-semibold tracking-wide text-sm md:text-base lg:text-lg">
        {isConnecting ? '接続中...' : '呼出'}
      </div>
    </div>
  );
};