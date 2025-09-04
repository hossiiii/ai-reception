// Session utilities for the intercom system

export interface Session {
  id: string;
  visitorName: string;
  roomName?: string;
  startTime: Date;
  endTime?: Date;
  purpose?: string;
}

export function createSession(visitorName: string, purpose?: string): Session {
  return {
    id: generateSessionId(),
    visitorName,
    startTime: new Date(),
    purpose,
  };
}

export function generateSessionId(): string {
  const timestamp = Date.now().toString(36);
  const random = Math.random().toString(36).substring(2, 8);
  return `session_${timestamp}_${random}`;
}

export function isActiveSession(session: Session): boolean {
  return !session.endTime;
}

export function getSessionDuration(session: Session): number {
  const endTime = session.endTime || new Date();
  return endTime.getTime() - session.startTime.getTime();
}

export function formatSessionDuration(durationMs: number): string {
  const seconds = Math.floor(durationMs / 1000);
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  
  if (minutes > 0) {
    return `${minutes}分${remainingSeconds}秒`;
  } else {
    return `${remainingSeconds}秒`;
  }
}