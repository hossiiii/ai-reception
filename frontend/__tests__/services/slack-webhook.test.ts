/**
 * Slack Webhook Service Tests
 * Tests for lib/services/slack-webhook.ts
 */

import {
  sendIntercomNotification,
  sendSimpleSlackNotification,
  testSlackWebhook,
} from '@/lib/services/slack-webhook';

// Mock fetch globally
global.fetch = jest.fn();
const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;

// Mock console methods
const originalConsoleLog = console.log;
const originalConsoleError = console.error;

describe('Slack Webhook Service', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    console.log = jest.fn();
    console.error = jest.fn();
  });

  afterAll(() => {
    console.log = originalConsoleLog;
    console.error = originalConsoleError;
  });

  describe('sendIntercomNotification', () => {
    const testNotificationData = {
      visitorName: '田中太郎',
      purpose: '打ち合わせ',
      roomName: 'room-test-123',
      joinUrl: 'https://example.com/video-call?room=room-test-123',
    };

    it('should send notification successfully with all data', async () => {
      const mockResponse = {
        ok: true,
        status: 200,
        statusText: 'OK',
      };
      mockFetch.mockResolvedValue(mockResponse as Response);

      const result = await sendIntercomNotification(testNotificationData);

      expect(result).toBe(true);
      expect(mockFetch).toHaveBeenCalledTimes(1);
      
      const [url, options] = mockFetch.mock.calls[0];
      expect(url).toBe('https://hooks.slack.com/services/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');
      expect(options).toEqual({
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: expect.any(String),
      });

      // Parse the body to check message structure
      const body = JSON.parse(options!.body as string);
      expect(body.text).toBe('受付にお客様がいらっしゃいました - 田中太郎');
      expect(body.blocks).toBeDefined();
      expect(body.blocks).toHaveLength(4);

      // Check header block
      expect(body.blocks[0]).toEqual({
        type: 'header',
        text: {
          type: 'plain_text',
          text: '🔔 受付通知',
          emoji: true,
        },
      });

      // Check section block with visitor info
      expect(body.blocks[1].type).toBe('section');
      expect(body.blocks[1].fields).toHaveLength(4);
      expect(body.blocks[1].fields[0].text).toBe('*お客様:* 田中太郎');
      expect(body.blocks[1].fields[1].text).toBe('*用件:* 打ち合わせ');
      expect(body.blocks[1].fields[2].text).toMatch(/\*時刻:\* \d{4}\/\d{2}\/\d{2} \d{2}:\d{2}/);
      expect(body.blocks[1].fields[3].text).toBe('*ルーム:* room-test-123');

      // Check actions block with join button
      expect(body.blocks[2].type).toBe('actions');
      expect(body.blocks[2].elements[0]).toEqual({
        type: 'button',
        text: {
          type: 'plain_text',
          text: '📹 ビデオ通話に参加',
          emoji: true,
        },
        style: 'primary',
        url: testNotificationData.joinUrl,
        action_id: 'join_video_call',
      });

      expect(console.log).toHaveBeenCalledWith(
        '✅ Slack notification sent successfully for visitor:',
        '田中太郎'
      );
    });

    it('should use custom timestamp when provided', async () => {
      const customTimestamp = '2024/01/15 14:30';
      const dataWithTimestamp = {
        ...testNotificationData,
        timestamp: customTimestamp,
      };

      mockFetch.mockResolvedValue({ ok: true } as Response);

      await sendIntercomNotification(dataWithTimestamp);

      const body = JSON.parse(mockFetch.mock.calls[0][1]!.body as string);
      expect(body.blocks[1].fields[2].text).toBe(`*時刻:* ${customTimestamp}`);
    });

    it('should generate timestamp in JST when not provided', async () => {
      mockFetch.mockResolvedValue({ ok: true } as Response);

      // Mock Date to return a predictable value
      const mockDate = new Date('2024-01-15T05:30:00Z'); // UTC time
      jest.spyOn(global, 'Date').mockImplementation(() => mockDate as any);

      await sendIntercomNotification(testNotificationData);

      const body = JSON.parse(mockFetch.mock.calls[0][1]!.body as string);
      // Should convert UTC to JST (+9 hours)
      expect(body.blocks[1].fields[2].text).toMatch(/\*時刻:\* 2024\/01\/15 14:30/);

      (global.Date as any).mockRestore();
    });

    it('should handle HTTP error responses', async () => {
      const mockResponse = {
        ok: false,
        status: 400,
        statusText: 'Bad Request',
      };
      mockFetch.mockResolvedValue(mockResponse as Response);

      const result = await sendIntercomNotification(testNotificationData);

      expect(result).toBe(false);
      expect(console.error).toHaveBeenCalledWith(
        'Slack notification failed:',
        400,
        'Bad Request'
      );
    });

    it('should handle network errors', async () => {
      const networkError = new Error('Network error');
      mockFetch.mockRejectedValue(networkError);

      const result = await sendIntercomNotification(testNotificationData);

      expect(result).toBe(false);
      expect(console.error).toHaveBeenCalledWith(
        'Error sending Slack notification:',
        networkError
      );
    });

    it('should handle fetch API exceptions', async () => {
      const fetchError = new TypeError('Failed to fetch');
      mockFetch.mockRejectedValue(fetchError);

      const result = await sendIntercomNotification(testNotificationData);

      expect(result).toBe(false);
      expect(console.error).toHaveBeenCalledWith(
        'Error sending Slack notification:',
        fetchError
      );
    });

    it('should handle invalid JSON response', async () => {
      // Mock a response that would cause JSON parsing issues
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.reject(new Error('Invalid JSON')),
      } as any);

      const result = await sendIntercomNotification(testNotificationData);

      expect(result).toBe(true); // Still succeeds because we only check response.ok
    });
  });

  describe('sendSimpleSlackNotification', () => {
    it('should send simple text notification successfully', async () => {
      const message = 'Test notification message';
      mockFetch.mockResolvedValue({ ok: true } as Response);

      const result = await sendSimpleSlackNotification(message);

      expect(result).toBe(true);
      expect(mockFetch).toHaveBeenCalledTimes(1);

      const [url, options] = mockFetch.mock.calls[0];
      expect(url).toBe('https://hooks.slack.com/services/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');
      expect(options).toEqual({
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: message }),
      });

      expect(console.log).toHaveBeenCalledWith('✅ Simple Slack notification sent successfully');
    });

    it('should handle HTTP error responses', async () => {
      const message = 'Test message';
      const mockResponse = {
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
      };
      mockFetch.mockResolvedValue(mockResponse as Response);

      const result = await sendSimpleSlackNotification(message);

      expect(result).toBe(false);
      expect(console.error).toHaveBeenCalledWith(
        'Simple Slack notification failed:',
        500,
        'Internal Server Error'
      );
    });

    it('should handle network errors', async () => {
      const message = 'Test message';
      const networkError = new Error('Network timeout');
      mockFetch.mockRejectedValue(networkError);

      const result = await sendSimpleSlackNotification(message);

      expect(result).toBe(false);
      expect(console.error).toHaveBeenCalledWith(
        'Error sending simple Slack notification:',
        networkError
      );
    });

    it('should handle empty message', async () => {
      const message = '';
      mockFetch.mockResolvedValue({ ok: true } as Response);

      const result = await sendSimpleSlackNotification(message);

      expect(result).toBe(true);
      
      const body = JSON.parse(mockFetch.mock.calls[0][1]!.body as string);
      expect(body.text).toBe('');
    });

    it('should handle special characters in message', async () => {
      const message = 'Test with 特殊文字 and émojis 🚀';
      mockFetch.mockResolvedValue({ ok: true } as Response);

      const result = await sendSimpleSlackNotification(message);

      expect(result).toBe(true);
      
      const body = JSON.parse(mockFetch.mock.calls[0][1]!.body as string);
      expect(body.text).toBe(message);
    });
  });

  describe('testSlackWebhook', () => {
    it('should send test notification successfully', async () => {
      mockFetch.mockResolvedValue({ ok: true } as Response);

      const result = await testSlackWebhook();

      expect(result).toBe(true);
      expect(mockFetch).toHaveBeenCalledTimes(1);

      const body = JSON.parse(mockFetch.mock.calls[0][1]!.body as string);
      expect(body.text).toBe('🔧 Slack webhook test from intercom system');
    });

    it('should handle test notification failure', async () => {
      mockFetch.mockResolvedValue({ ok: false, status: 403 } as Response);

      const result = await testSlackWebhook();

      expect(result).toBe(false);
    });

    it('should handle test notification network error', async () => {
      mockFetch.mockRejectedValue(new Error('Network error'));

      const result = await testSlackWebhook();

      expect(result).toBe(false);
    });
  });

  describe('Message Format Validation', () => {
    it('should create properly formatted Slack blocks', async () => {
      const testData = {
        visitorName: 'テスト太郎',
        purpose: 'ミーティング',
        roomName: 'room-123',
        joinUrl: 'https://test.com/join',
      };

      mockFetch.mockResolvedValue({ ok: true } as Response);
      await sendIntercomNotification(testData);

      const body = JSON.parse(mockFetch.mock.calls[0][1]!.body as string);

      // Validate block structure
      expect(body.blocks).toHaveLength(4);
      expect(body.blocks[0].type).toBe('header');
      expect(body.blocks[1].type).toBe('section');
      expect(body.blocks[2].type).toBe('actions');
      expect(body.blocks[3].type).toBe('context');

      // Validate section fields
      const sectionFields = body.blocks[1].fields;
      expect(sectionFields).toHaveLength(4);
      expect(sectionFields.every((field: any) => field.type === 'mrkdwn')).toBe(true);

      // Validate button action
      const button = body.blocks[2].elements[0];
      expect(button.type).toBe('button');
      expect(button.url).toBe(testData.joinUrl);
      expect(button.action_id).toBe('join_video_call');
    });

    it('should handle long visitor names gracefully', async () => {
      const longName = 'とても長い名前の訪問者さんでテストケースとして使用します';
      const testData = {
        visitorName: longName,
        purpose: 'テスト',
        roomName: 'room-long-name',
        joinUrl: 'https://test.com',
      };

      mockFetch.mockResolvedValue({ ok: true } as Response);
      await sendIntercomNotification(testData);

      const body = JSON.parse(mockFetch.mock.calls[0][1]!.body as string);
      expect(body.text).toBe(`受付にお客様がいらっしゃいました - ${longName}`);
      expect(body.blocks[1].fields[0].text).toBe(`*お客様:* ${longName}`);
    });

    it('should handle URLs with special characters', async () => {
      const specialUrl = 'https://example.com/video?room=テスト-123&token=abc%20def';
      const testData = {
        visitorName: 'テスト',
        purpose: 'テスト',
        roomName: 'room-special',
        joinUrl: specialUrl,
      };

      mockFetch.mockResolvedValue({ ok: true } as Response);
      await sendIntercomNotification(testData);

      const body = JSON.parse(mockFetch.mock.calls[0][1]!.body as string);
      expect(body.blocks[2].elements[0].url).toBe(specialUrl);
    });
  });

  describe('Error Resilience', () => {
    it('should not throw exceptions on fetch failure', async () => {
      mockFetch.mockRejectedValue(new Error('Catastrophic failure'));

      await expect(sendIntercomNotification({
        visitorName: 'Test',
        purpose: 'Test',
        roomName: 'test',
        joinUrl: 'test',
      })).resolves.toBe(false);

      await expect(sendSimpleSlackNotification('test')).resolves.toBe(false);
      await expect(testSlackWebhook()).resolves.toBe(false);
    });

    it('should handle malformed webhook URL gracefully', async () => {
      // This tests the service behavior with current hardcoded URL
      // In a real scenario, you might want to test with configurable URLs
      mockFetch.mockRejectedValue(new TypeError('Invalid URL'));

      const result = await sendIntercomNotification({
        visitorName: 'Test',
        purpose: 'Test',
        roomName: 'test',
        joinUrl: 'test',
      });

      expect(result).toBe(false);
      expect(console.error).toHaveBeenCalled();
    });
  });

  describe('Logging Behavior', () => {
    it('should log success for intercom notifications', async () => {
      mockFetch.mockResolvedValue({ ok: true } as Response);
      
      await sendIntercomNotification({
        visitorName: 'ログテスト',
        purpose: 'テスト',
        roomName: 'room-log-test',
        joinUrl: 'https://test.com',
      });

      expect(console.log).toHaveBeenCalledWith(
        '✅ Slack notification sent successfully for visitor:',
        'ログテスト'
      );
    });

    it('should log success for simple notifications', async () => {
      mockFetch.mockResolvedValue({ ok: true } as Response);
      
      await sendSimpleSlackNotification('Simple test message');

      expect(console.log).toHaveBeenCalledWith('✅ Simple Slack notification sent successfully');
    });

    it('should log errors for failed requests', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 404,
        statusText: 'Not Found',
      } as Response);
      
      await sendIntercomNotification({
        visitorName: 'Error Test',
        purpose: 'Error',
        roomName: 'room-error',
        joinUrl: 'https://error.com',
      });

      expect(console.error).toHaveBeenCalledWith(
        'Slack notification failed:',
        404,
        'Not Found'
      );
    });
  });
});