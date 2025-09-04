/**
 * シンプル受付システム用APIクライアント
 * Next.js API Routesとの通信を管理
 */

// Simple fetch wrapper for Next.js API routes
class SimpleApiClient {
  private baseUrl: string;

  constructor() {
    // Always use relative paths for Next.js API routes
    this.baseUrl = '';
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}/api${endpoint}`;
    
    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // Reception API
  async startReception(data: { type: string }) {
    return this.request('/reception/start', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async verifyAppointment(data: { company: string; name: string }) {
    return this.request('/reception/verify', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async completeReception(data: { sessionId: string; action: string }) {
    return this.request('/reception/complete', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Calendar API
  async checkCalendar(params: { company: string; name: string }) {
    const query = new URLSearchParams(params);
    return this.request(`/calendar/check?${query}`);
  }

  // Notification API
  async sendSlackNotification(data: {
    message_type: "visitor" | "video_call" | "error";
    visitor_info?: {
      name: string;
      company: string;
      email?: string;
      purpose?: string;
    };
    session_id?: string;
    additional_data?: Record<string, any>;
  }) {
    return this.request('/notification/slack', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Video API
  async createVideoRoom(data: { visitorName: string; purpose: string }) {
    return this.request('/video/create', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }
}

// Export singleton instance
export const apiClient = new SimpleApiClient();