'use client';

import { ReceptionButtonProps } from '@/lib/types';

export default function ReceptionButton({
  onStartConversation,
  disabled = false,
  loading = false
}: ReceptionButtonProps) {
  return (
    <div className="flex flex-col items-center">
      <button
        onClick={onStartConversation}
        disabled={disabled || loading}
        className="group relative bg-primary-600 hover:bg-primary-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-bold py-8 px-12 rounded-3xl text-2xl shadow-soft-lg hover:shadow-xl transform hover:scale-105 disabled:transform-none transition-all duration-300 touch-safe"
        aria-label="受付を開始する"
      >
        {loading ? (
          <div className="flex items-center space-x-3">
            <div className="loading-spinner border-white border-t-transparent w-6 h-6"></div>
            <span>システム準備中...</span>
          </div>
        ) : (
          <div className="flex items-center space-x-4">
            <svg
              className="w-8 h-8 group-hover:scale-110 transition-transform"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z"
              />
            </svg>
            <span>受付開始</span>
          </div>
        )}
        
        {/* Pulse effect for active state */}
        {!disabled && !loading && (
          <div className="absolute inset-0 rounded-3xl bg-primary-500 opacity-0 group-hover:opacity-20 transition-opacity duration-300"></div>
        )}
      </button>
      
      {/* Additional instruction text */}
      <p className="mt-6 text-gray-600 text-lg text-center max-w-md">
        {disabled
          ? 'システムがご利用いただけません'
          : loading
          ? 'システムを準備しています...'
          : 'このボタンを押すと、AIとの対話が始まります'}
      </p>
      
      {/* Visual feedback for disabled state */}
      {disabled && (
        <div className="mt-4 flex items-center space-x-2 text-red-600">
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"
            />
          </svg>
          <span className="text-sm">システムエラーが発生しています</span>
        </div>
      )}
    </div>
  );
}