// Intercom API service that combines video room creation with Slack notifications

interface CreateIntercomCallRequest {
  visitorName: string;
  purpose?: string;
}

interface CreateIntercomCallResponse {
  success: boolean;
  video_room?: {
    room_name: string;
    room_sid: string;
    access_token: string;
    room_url: string;
    created_at: string;
    expires_at: string;
    visitor_identity: string;
    max_participants: number;
  };
  visitor_name?: string;
  purpose?: string;
  slack_notification_sent?: boolean;
  error?: string;
}

interface StaffTokenResponse {
  success: boolean;
  access_token?: string;
  identity?: string;
  room_name?: string;
  error?: string;
}

/**
 * Create a video room and send Slack notification in one call
 */
export async function createIntercomCall(data: CreateIntercomCallRequest): Promise<CreateIntercomCallResponse> {
  try {
    // First, create the video room
    const videoResponse = await fetch('/api/video/create', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        visitorName: data.visitorName,
        purpose: data.purpose || 'お客様対応',
      }),
    });

    if (!videoResponse.ok) {
      const error = await videoResponse.json();
      throw new Error(error.message || 'Failed to create video room');
    }

    const videoResult = await videoResponse.json();

    if (!videoResult.success) {
      throw new Error('Video room creation failed');
    }

    // Then send Slack notification
    let slackNotificationSent = false;
    try {
      const slackResponse = await fetch('/api/slack/notify', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          visitorName: data.visitorName,
          purpose: data.purpose || 'お客様対応',
          roomName: videoResult.video_room.room_name,
          roomUrl: videoResult.video_room.room_url,
        }),
      });

      if (slackResponse.ok) {
        const slackResult = await slackResponse.json();
        slackNotificationSent = slackResult.success;
      }
    } catch (slackError) {
      console.warn('Failed to send Slack notification, but video room was created:', slackError);
      // Don't fail the entire operation if Slack fails
    }

    return {
      success: true,
      video_room: videoResult.video_room,
      visitor_name: videoResult.visitor_name,
      purpose: videoResult.purpose,
      slack_notification_sent: slackNotificationSent,
    };

  } catch (error) {
    console.error('Error creating intercom call:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error occurred',
    };
  }
}

/**
 * Get staff access token for joining an existing room
 */
export async function getStaffToken(roomName: string, staffName: string = 'Staff'): Promise<StaffTokenResponse> {
  try {
    const response = await fetch(`/api/video/create?room_name=${encodeURIComponent(roomName)}&staff_name=${encodeURIComponent(staffName)}`, {
      method: 'GET',
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Failed to generate staff token');
    }

    const result = await response.json();

    if (!result.success) {
      throw new Error('Staff token generation failed');
    }

    return {
      success: true,
      access_token: result.access_token,
      identity: result.identity,
      room_name: result.room_name,
    };

  } catch (error) {
    console.error('Error getting staff token:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error occurred',
    };
  }
}

/**
 * End a video room
 */
export async function endVideoRoom(roomName: string): Promise<{ success: boolean; error?: string }> {
  try {
    const response = await fetch(`/api/video/create?room_name=${encodeURIComponent(roomName)}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Failed to end video room');
    }

    const result = await response.json();

    return {
      success: result.success || false,
    };

  } catch (error) {
    console.error('Error ending video room:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error occurred',
    };
  }
}

export default {
  createIntercomCall,
  getStaffToken,
  endVideoRoom,
};