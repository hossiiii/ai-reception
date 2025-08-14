import {
  ConversationStartResponse,
  MessageResponse,
  ConversationHistoryResponse,
  MessageRequest,
  VideoRoomRequest,
  VideoRoomResponse,
  StaffTokenRequest,
  StaffTokenResponse,
  VideoRoomEndRequest,
  VideoRoomEndResponse,
  ApiError,
  ApiConfig
} from './types';

class ApiClient {
  private config: ApiConfig;

  constructor(config?: Partial<ApiConfig>) {
    this.config = {
      baseUrl: process.env.NODE_ENV === 'production' 
        ? (process.env.NEXT_PUBLIC_API_URL || 'https://your-app.vercel.app') 
        : 'http://localhost:8000',
      timeout: 30000, // Increased from 10s to 30s for AI processing
      retries: 3,
      ...config
    };
  }

  private async fetchWithRetry<T>(
    url: string,
    options: RequestInit = {},
    retries: number = this.config.retries
  ): Promise<T> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const error = new Error(errorData.detail || `HTTP ${response.status}`) as ApiError;
        error.status = response.status;
        error.code = errorData.code;
        error.details = errorData.detail;
        throw error;
      }

      return await response.json();
    } catch (error) {
      clearTimeout(timeoutId);

      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error('Request timeout') as ApiError;
      }

      if (retries > 0 && this.shouldRetry(error as ApiError)) {
        await this.delay(1000 * (this.config.retries - retries + 1));
        return this.fetchWithRetry<T>(url, options, retries - 1);
      }

      throw error;
    }
  }

  private shouldRetry(error: ApiError): boolean {
    // Retry on network errors or 5xx server errors
    return !error.status || error.status >= 500;
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  private getUrl(path: string): string {
    return `${this.config.baseUrl}${path}`;
  }

  // Conversation API Methods

  /**
   * Start a new conversation session
   */
  async startConversation(): Promise<ConversationStartResponse> {
    try {
      const response = await this.fetchWithRetry<ConversationStartResponse>(
        this.getUrl('/api/conversations/'),
        {
          method: 'POST',
        }
      );

      return response;
    } catch (error) {
      console.error('Failed to start conversation:', error);
      throw error;
    }
  }

  /**
   * Send a message to an existing conversation
   */
  async sendMessage(sessionId: string, message: string): Promise<MessageResponse> {
    if (!sessionId.trim()) {
      throw new Error('Session ID is required') as ApiError;
    }

    if (!message.trim()) {
      throw new Error('Message cannot be empty') as ApiError;
    }

    try {
      const request: MessageRequest = { message: message.trim() };

      const response = await this.fetchWithRetry<MessageResponse>(
        this.getUrl(`/api/conversations/${sessionId}/messages`),
        {
          method: 'POST',
          body: JSON.stringify(request),
        }
      );

      return response;
    } catch (error) {
      console.error('Failed to send message:', error);
      throw error;
    }
  }

  /**
   * Get conversation history
   */
  async getConversationHistory(sessionId: string): Promise<ConversationHistoryResponse> {
    if (!sessionId.trim()) {
      throw new Error('Session ID is required') as ApiError;
    }

    try {
      const response = await this.fetchWithRetry<ConversationHistoryResponse>(
        this.getUrl(`/api/conversations/${sessionId}`)
      );

      return response;
    } catch (error) {
      console.error('Failed to get conversation history:', error);
      throw error;
    }
  }

  /**
   * End a conversation session
   */
  async endConversation(sessionId: string): Promise<{ message: string; session_id: string }> {
    if (!sessionId.trim()) {
      throw new Error('Session ID is required') as ApiError;
    }

    try {
      const response = await this.fetchWithRetry<{ message: string; session_id: string }>(
        this.getUrl(`/api/conversations/${sessionId}`),
        {
          method: 'DELETE',
        }
      );

      return response;
    } catch (error) {
      console.error('Failed to end conversation:', error);
      throw error;
    }
  }

  // Video Call API Methods

  /**
   * Create a new video room for visitor reception
   */
  async createVideoRoom(visitorInfo: VideoRoomRequest): Promise<VideoRoomResponse> {
    if (!visitorInfo.visitor_name.trim()) {
      throw new Error('Visitor name is required') as ApiError;
    }

    try {
      const response = await this.fetchWithRetry<VideoRoomResponse>(
        this.getUrl('/api/video/create-room'),
        {
          method: 'POST',
          body: JSON.stringify(visitorInfo),
        }
      );

      return response;
    } catch (error) {
      console.error('Failed to create video room:', error);
      throw error;
    }
  }

  /**
   * Generate access token for staff member to join existing room
   */
  async generateStaffToken(request: StaffTokenRequest): Promise<StaffTokenResponse> {
    if (!request.room_name.trim()) {
      throw new Error('Room name is required') as ApiError;
    }

    if (!request.staff_name.trim()) {
      throw new Error('Staff name is required') as ApiError;
    }

    try {
      const response = await this.fetchWithRetry<StaffTokenResponse>(
        this.getUrl('/api/video/staff-token'),
        {
          method: 'POST',
          body: JSON.stringify(request),
        }
      );

      return response;
    } catch (error) {
      console.error('Failed to generate staff token:', error);
      throw error;
    }
  }

  /**
   * End an active video room
   */
  async endVideoRoom(roomName: string): Promise<VideoRoomEndResponse> {
    if (!roomName.trim()) {
      throw new Error('Room name is required') as ApiError;
    }

    try {
      const request: VideoRoomEndRequest = { room_name: roomName };
      
      const response = await this.fetchWithRetry<VideoRoomEndResponse>(
        this.getUrl('/api/video/end-room'),
        {
          method: 'POST',
          body: JSON.stringify(request),
        }
      );

      return response;
    } catch (error) {
      console.error('Failed to end video room:', error);
      throw error;
    }
  }

  /**
   * Health check endpoint
   */
  async healthCheck(): Promise<{ status: string; message: string }> {
    try {
      const response = await this.fetchWithRetry<{ status: string; message: string }>(
        this.getUrl('/api/health'),
        { method: 'GET' }
      );

      return response;
    } catch (error) {
      console.error('Health check failed:', error);
      throw error;
    }
  }

  /**
   * Update configuration
   */
  updateConfig(newConfig: Partial<ApiConfig>): void {
    this.config = { ...this.config, ...newConfig };
  }
}

// Create singleton instance
export const apiClient = new ApiClient();

// Export for custom instances
export { ApiClient };

// Utility functions for error handling
export const isApiError = (error: unknown): error is ApiError => {
  return error instanceof Error && 'status' in error;
};

export const getErrorMessage = (error: unknown): string => {
  if (isApiError(error)) {
    return error.details || error.message;
  }
  
  if (error instanceof Error) {
    return error.message;
  }
  
  return 'An unexpected error occurred';
};

export const isNetworkError = (error: unknown): boolean => {
  if (isApiError(error)) {
    return !error.status || error.message.includes('fetch') || error.message.includes('timeout');
  }
  
  return false;
};

export const isServerError = (error: unknown): boolean => {
  if (isApiError(error)) {
    return error.status ? error.status >= 500 : false;
  }
  
  return false;
};

export const isClientError = (error: unknown): boolean => {
  if (isApiError(error)) {
    return error.status ? error.status >= 400 && error.status < 500 : false;
  }
  
  return false;
};