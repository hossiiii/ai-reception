// Simple Slack webhook service for intercom notifications

interface SlackNotificationData {
  visitorName: string;
  purpose: string;
  roomName: string;
  joinUrl: string;
  timestamp?: string;
}

interface SlackMessage {
  text: string;
  blocks?: any[];
}

const SLACK_WEBHOOK_URL = 'https://hooks.slack.com/services/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';

/**
 * Send a notification to Slack when a visitor arrives at the intercom
 */
export async function sendIntercomNotification(data: SlackNotificationData): Promise<boolean> {
  try {
    const timestamp = data.timestamp || new Date().toLocaleString('ja-JP', {
      timeZone: 'Asia/Tokyo',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });

    const message: SlackMessage = {
      text: `受付にお客様がいらっしゃいました - ${data.visitorName}`,
      blocks: [
        {
          type: 'header',
          text: {
            type: 'plain_text',
            text: '🔔 受付通知',
            emoji: true
          }
        },
        {
          type: 'section',
          fields: [
            {
              type: 'mrkdwn',
              text: `*お客様:* ${data.visitorName}`
            },
            {
              type: 'mrkdwn',
              text: `*用件:* ${data.purpose}`
            },
            {
              type: 'mrkdwn',
              text: `*時刻:* ${timestamp}`
            },
            {
              type: 'mrkdwn',
              text: `*ルーム:* ${data.roomName}`
            }
          ]
        },
        {
          type: 'actions',
          elements: [
            {
              type: 'button',
              text: {
                type: 'plain_text',
                text: '📹 ビデオ通話に参加',
                emoji: true
              },
              style: 'primary',
              url: data.joinUrl,
              action_id: 'join_video_call'
            }
          ]
        },
        {
          type: 'context',
          elements: [
            {
              type: 'mrkdwn',
              text: '上のボタンからビデオ通話に参加してお客様と話すことができます。'
            }
          ]
        }
      ]
    };

    const response = await fetch(SLACK_WEBHOOK_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(message),
    });

    if (!response.ok) {
      console.error('Slack notification failed:', response.status, response.statusText);
      return false;
    }

    console.log('✅ Slack notification sent successfully for visitor:', data.visitorName);
    return true;

  } catch (error) {
    console.error('Error sending Slack notification:', error);
    return false;
  }
}

/**
 * Send a simple text notification to Slack
 */
export async function sendSimpleSlackNotification(message: string): Promise<boolean> {
  try {
    const payload = {
      text: message
    };

    const response = await fetch(SLACK_WEBHOOK_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      console.error('Simple Slack notification failed:', response.status, response.statusText);
      return false;
    }

    console.log('✅ Simple Slack notification sent successfully');
    return true;

  } catch (error) {
    console.error('Error sending simple Slack notification:', error);
    return false;
  }
}

/**
 * Test the Slack webhook connection
 */
export async function testSlackWebhook(): Promise<boolean> {
  return sendSimpleSlackNotification('🔧 Slack webhook test from intercom system');
}

export default {
  sendIntercomNotification,
  sendSimpleSlackNotification,
  testSlackWebhook,
};