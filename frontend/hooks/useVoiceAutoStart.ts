/**
 * Phase 3: 音声チャット自動開始管理フック
 * 自動開始ロジックを分離し、依存関係を明確化
 */

import { useEffect } from 'react';

export interface UseVoiceAutoStartOptions {
  autoStart: boolean;
  startVoiceChat: () => Promise<boolean>;
}

export interface UseVoiceAutoStartReturn {
  // No external interface needed - manages auto-start internally
}

export function useVoiceAutoStart(options: UseVoiceAutoStartOptions): UseVoiceAutoStartReturn {
  const { autoStart, startVoiceChat } = options;

  // Auto-start voice chat if requested
  useEffect(() => {
    if (autoStart) {
      console.log('🚀 Auto-starting voice chat');
      startVoiceChat();
    }
  }, [autoStart, startVoiceChat]);

  return {};
}