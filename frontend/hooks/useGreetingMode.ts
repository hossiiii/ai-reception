/**
 * Phase 3: 挨拶モード管理フック
 * 挨拶モードの状態管理を分離し、参照の更新を担当
 */

import { useEffect, useRef } from 'react';

export interface UseGreetingModeOptions {
  isGreeting?: boolean;
}

export interface UseGreetingModeReturn {
  isGreetingRef: React.MutableRefObject<boolean>;
}

export function useGreetingMode(options: UseGreetingModeOptions = {}): UseGreetingModeReturn {
  const { isGreeting = false } = options;
  
  // Greeting mode ref for dynamic updates during conversation
  const isGreetingRef = useRef(isGreeting);

  // Update greeting ref when option changes
  useEffect(() => {
    const newGreetingState = isGreeting;
    if (isGreetingRef.current !== newGreetingState) {
      console.log(`🎭 Greeting mode changed: ${isGreetingRef.current} → ${newGreetingState}`);
      isGreetingRef.current = newGreetingState;
    }
  }, [isGreeting]);

  return {
    isGreetingRef
  };
}