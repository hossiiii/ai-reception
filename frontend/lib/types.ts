// API Response Types
export interface ApiResponse<T = any> {
  success: boolean;
  error?: string;
  data?: T;
}

// Conversation Types
export interface ConversationStartResponse {
  success: boolean;
  session_id: string;
  message: string;
  step: string;
  visitor_info?: VisitorInfo;
  error?: string;
}

export interface MessageResponse {
  success: boolean;
  session_id: string;
  message: string;
  step: string;
  visitor_info?: VisitorInfo;
  calendar_result?: CalendarResult;
  completed: boolean;
  error?: string;
}

export interface ConversationHistoryResponse {
  success: boolean;
  session_id: string;
  messages: ConversationMessage[];
  visitor_info?: VisitorInfo;
  current_step?: string;
  calendar_result?: CalendarResult;
  completed: boolean;
  error?: string;
}

// Message Types
export interface ConversationMessage {
  speaker: 'visitor' | 'ai';
  content: string;
  timestamp?: string;
}

export interface MessageRequest {
  message: string;
}

// Visitor Types
export type VisitorType = 'appointment' | 'sales' | 'delivery';

export interface VisitorInfo {
  name: string;
  company: string;
  visitor_type?: VisitorType;
  confirmed: boolean;
  correction_count: number;
}

// Calendar Types
export interface CalendarResult {
  found: boolean;
  events?: CalendarEvent[];
  identifier: string;
  message: string;
  error?: boolean;
  roomName?: string;
}

export interface CalendarEvent {
  id: string;
  summary: string;
  description?: string;
  start: EventTime;
  end: EventTime;
  attendees?: Attendee[];
  location?: string;
  creator?: Person;
  organizer?: Person;
}

export interface EventTime {
  dateTime?: string;
  date?: string;
}

export interface Attendee {
  email: string;
  displayName?: string;
  responseStatus?: string;
  organizer?: boolean;
}

export interface Person {
  email: string;
  displayName?: string;
}

// UI State Types
export interface ChatState {
  isLoading: boolean;
  isTyping: boolean;
  error: string | null;
  sessionId: string | null;
  conversationStarted: boolean;
  conversationCompleted: boolean;
}

export interface ConversationStep {
  step: string;
  title: string;
  description: string;
  completed: boolean;
}

// Component Props Types
export interface ChatInterfaceProps {
  sessionId?: string;
  onConversationEnd?: () => void;
  onError?: (error: string) => void;
}

export interface ConversationDisplayProps {
  messages: ConversationMessage[];
  isLoading: boolean;
  isTyping: boolean;
  visitorInfo?: VisitorInfo;
}


// Error Types
export interface ApiError extends Error {
  status?: number;
  code?: string;
  details?: string;
}

// Configuration Types
export interface ApiConfig {
  baseUrl: string;
  timeout: number;
  retries: number;
}

// Utility Types
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

export type RequiredFields<T, K extends keyof T> = T & Required<Pick<T, K>>;

// Constants
export const CONVERSATION_STEPS: Record<string, ConversationStep> = {
  greeting: {
    step: 'greeting',
    title: '挨拶',
    description: 'AIが挨拶をします',
    completed: false
  },
  name_collection: {
    step: 'name_collection',
    title: '情報収集',
    description: 'お名前と会社名をお聞きします',
    completed: false
  },
  confirmation: {
    step: 'confirmation',
    title: '確認',
    description: '入力内容を確認します',
    completed: false
  },
  type_detection: {
    step: 'type_detection',
    title: 'タイプ判定',
    description: '来客者タイプを判定します',
    completed: false
  },
  appointment_check: {
    step: 'appointment_check',
    title: '予約確認',
    description: 'カレンダーで予約を確認します',
    completed: false
  },
  guidance: {
    step: 'guidance',
    title: '案内',
    description: '適切な案内を提供します',
    completed: false
  },
  complete: {
    step: 'complete',
    title: '完了',
    description: '対応が完了しました',
    completed: true
  }
};