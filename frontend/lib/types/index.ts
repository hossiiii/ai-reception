// Core types for non-AI reception system

export type VisitorType = "appointment" | "sales" | "delivery";

export interface VisitorInfo {
  name: string;
  company: string;
  visitor_type: VisitorType | null;
  confirmed: boolean;
  correction_count: number;
  purpose: string;
}

export interface ConversationLog {
  timestamp: Date;
  speaker: "visitor" | "ai";
  message: string;
}

// Calendar related types
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

export interface EventTime {
  dateTime?: string;
  date?: string;
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

export interface ReservationCheckResult {
  found: boolean;
  events?: CalendarEvent[];
  identifier?: string;
  message?: string;
  error?: boolean;
  roomName?: string;
  startTime?: string;
  endTime?: string;
  attendees?: string[];
  subject?: string;
}

export interface CalendarReservationResult {
  found: boolean;
  roomName?: string;
  startTime?: string;
  endTime?: string;
  attendees?: string[];
  subject?: string;
  events?: CalendarEvent[];
}

// Video call related types
export interface VideoRoomInfo {
  room_name: string;
  room_sid: string;
  access_token: string;
  room_url: string;
  created_at: string;
  expires_at: string;
  visitor_identity: string;
  max_participants: number;
  mock?: boolean;
}

export interface StaffTokenInfo {
  access_token: string;
  identity: string;
}

// Reception session types
export interface ReceptionSession {
  id: string;
  visitor_info: VisitorInfo;
  status: "started" | "verified" | "completed" | "error";
  calendar_result?: ReservationCheckResult;
  video_room?: VideoRoomInfo;
  conversation_logs: ConversationLog[];
  created_at: string;
  updated_at: string;
}

// API Request/Response types
export interface StartReceptionRequest {
  visitor_name: string;
  company_name: string;
  purpose?: string;
}

export interface StartReceptionResponse {
  session_id: string;
  message: string;
  success: boolean;
}

export interface VerifyReservationRequest {
  session_id: string;
  visitor_identifier: string;
}

export interface VerifyReservationResponse {
  session_id: string;
  reservation_result: CalendarReservationResult;
  success: boolean;
}

export interface CompleteReceptionRequest {
  session_id: string;
  visitor_type?: VisitorType;
  additional_notes?: string;
}

export interface CompleteReceptionResponse {
  session_id: string;
  message: string;
  slack_notified: boolean;
  success: boolean;
}

export interface VideoRoomRequest {
  visitorName: string;
  purpose: string;
}

export interface VideoRoomResponse {
  roomId: string;
  token: string;
  success: boolean;
}

// Video creation API types for legacy compatibility
export interface CreateVideoRoomRequest extends VideoRoomRequest {}
export interface CreateVideoRoomResponse extends VideoRoomResponse {}

export interface SlackNotificationRequest {
  session_id: string;
  message_type: "visitor" | "video_call" | "error";
  additional_data?: Record<string, any>;
}

export interface SlackNotificationResponse {
  success: boolean;
  thread_ts?: string;
}

// Error response type
export interface ApiErrorResponse {
  error: string;
  details?: string;
  success: false;
}

// Common API response wrapper
export type ApiResponse<T> = T | ApiErrorResponse;

// Session storage types
export interface SessionData {
  visitor_info: Partial<VisitorInfo>;
  status: ReceptionSession["status"];
  conversation_logs: ConversationLog[];
  calendar_result?: ReservationCheckResult;
  video_room?: VideoRoomInfo;
  created_at: Date;
  updated_at: Date;
}