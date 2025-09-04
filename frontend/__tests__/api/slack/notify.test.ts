/**
 * Slack Notification API Route Tests
 * Tests for /app/api/slack/notify/route.ts
 */

import { NextRequest } from 'next/server';
import { POST, GET, PUT, DELETE } from '@/app/api/slack/notify/route';
import * as slackWebhook from '@/lib/services/slack-webhook';
import * as utils from '@/lib/utils';

// Mock dependencies
jest.mock('@/lib/services/slack-webhook');
jest.mock('@/lib/utils');

const mockSendIntercomNotification = slackWebhook.sendIntercomNotification as jest.MockedFunction<typeof slackWebhook.sendIntercomNotification>;
const mockCreateErrorResponse = utils.createErrorResponse as jest.MockedFunction<typeof utils.createErrorResponse>;
const mockLogInfo = utils.logInfo as jest.MockedFunction<typeof utils.logInfo>;
const mockLogError = utils.logError as jest.MockedFunction<typeof utils.logError>;
const mockLogSuccess = utils.logSuccess as jest.MockedFunction<typeof utils.logSuccess>;

describe('/api/slack/notify', () => {
  const validRequestBody = {
    visitorName: '田中太郎',
    purpose: '打ち合わせ',
    roomName: 'room-田中太郎-123',
    roomUrl: 'https://example.com/video-call?room=room-田中太郎-123',
  };

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Default mock implementations
    mockLogInfo.mockImplementation();
    mockLogError.mockImplementation();
    mockLogSuccess.mockImplementation();
    
    // Mock environment variables
    process.env.NEXTAUTH_URL = 'https://example.com';
  });

  afterEach(() => {
    // Clean up environment variables
    delete process.env.NEXTAUTH_URL;
    delete process.env.VERCEL_URL;
  });

  describe('POST method', () => {
    const createMockRequest = (body: any) => {
      return new NextRequest('http://localhost:3000/api/slack/notify', {
        method: 'POST',
        body: JSON.stringify(body),
        headers: {
          'content-type': 'application/json',
        },
      });
    };

    it('should send notification successfully with all required fields', async () => {
      mockSendIntercomNotification.mockResolvedValue(true);

      const request = createMockRequest(validRequestBody);
      const response = await POST(request);
      const responseData = await response.json();

      expect(response.status).toBe(200);
      expect(responseData.success).toBe(true);
      expect(responseData.message).toBe('Slack notification sent successfully');
      expect(responseData.data).toEqual({
        visitorName: validRequestBody.visitorName,
        roomName: validRequestBody.roomName,
        joinUrl: validRequestBody.roomUrl,
      });

      expect(mockLogInfo).toHaveBeenCalledWith('Slack notification request received');
      expect(mockLogInfo).toHaveBeenCalledWith(
        `Sending Slack notification for visitor: ${validRequestBody.visitorName}, room: ${validRequestBody.roomName}`
      );
      
      expect(mockSendIntercomNotification).toHaveBeenCalledWith({
        visitorName: validRequestBody.visitorName,
        purpose: validRequestBody.purpose,
        roomName: validRequestBody.roomName,
        joinUrl: validRequestBody.roomUrl,
        timestamp: expect.stringMatching(/\d{4}\/\d{2}\/\d{2} \d{2}:\d{2}/),
      });

      expect(mockLogSuccess).toHaveBeenCalledWith(
        `Slack notification sent successfully for visitor: ${validRequestBody.visitorName}`,
        {
          visitorName: validRequestBody.visitorName,
          roomName: validRequestBody.roomName,
          joinUrl: validRequestBody.roomUrl,
        }
      );
    });

    it('should generate joinUrl when not provided', async () => {
      const bodyWithoutUrl = {
        visitorName: '佐藤次郎',
        purpose: 'ミーティング',
        roomName: 'room-佐藤次郎-456',
      };

      mockSendIntercomNotification.mockResolvedValue(true);

      const request = createMockRequest(bodyWithoutUrl);
      const response = await POST(request);
      const responseData = await response.json();

      expect(response.status).toBe(200);
      
      const expectedJoinUrl = `https://example.com/video-call?room=${encodeURIComponent(bodyWithoutUrl.roomName)}&staff=true`;
      
      expect(mockSendIntercomNotification).toHaveBeenCalledWith({
        visitorName: bodyWithoutUrl.visitorName,
        purpose: bodyWithoutUrl.purpose,
        roomName: bodyWithoutUrl.roomName,
        joinUrl: expectedJoinUrl,
        timestamp: expect.any(String),
      });

      expect(responseData.data.joinUrl).toBe(expectedJoinUrl);
    });

    it('should use default purpose when not provided', async () => {
      const bodyWithoutPurpose = {
        visitorName: '高橋三郎',
        roomName: 'room-高橋三郎-789',
      };

      mockSendIntercomNotification.mockResolvedValue(true);

      const request = createMockRequest(bodyWithoutPurpose);
      const response = await POST(request);

      expect(response.status).toBe(200);
      
      expect(mockSendIntercomNotification).toHaveBeenCalledWith({
        visitorName: bodyWithoutPurpose.visitorName,
        purpose: 'お客様対応',
        roomName: bodyWithoutPurpose.roomName,
        joinUrl: expect.any(String),
        timestamp: expect.any(String),
      });
    });

    it('should use VERCEL_URL when NEXTAUTH_URL is not set', async () => {
      delete process.env.NEXTAUTH_URL;
      process.env.VERCEL_URL = 'https://myapp.vercel.app';

      const bodyWithoutUrl = {
        visitorName: '山田花子',
        roomName: 'room-山田花子-101',
      };

      mockSendIntercomNotification.mockResolvedValue(true);

      const request = createMockRequest(bodyWithoutUrl);
      await POST(request);

      const expectedJoinUrl = `https://myapp.vercel.app/video-call?room=${encodeURIComponent(bodyWithoutUrl.roomName)}&staff=true`;
      
      expect(mockSendIntercomNotification).toHaveBeenCalledWith(
        expect.objectContaining({
          joinUrl: expectedJoinUrl,
        })
      );
    });

    it('should fallback to localhost when no base URL env vars are set', async () => {
      delete process.env.NEXTAUTH_URL;
      delete process.env.VERCEL_URL;

      const bodyWithoutUrl = {
        visitorName: '鈴木五郎',
        roomName: 'room-鈴木五郎-202',
      };

      mockSendIntercomNotification.mockResolvedValue(true);

      const request = createMockRequest(bodyWithoutUrl);
      await POST(request);

      const expectedJoinUrl = `http://localhost:3000/video-call?room=${encodeURIComponent(bodyWithoutUrl.roomName)}&staff=true`;
      
      expect(mockSendIntercomNotification).toHaveBeenCalledWith(
        expect.objectContaining({
          joinUrl: expectedJoinUrl,
        })
      );
    });

    it('should return validation error when visitorName is missing', async () => {
      const invalidBody = {
        roomName: 'room-test-123',
        purpose: 'test',
      };

      const mockErrorResponse = {
        error: 'Missing Parameter',
        message: 'visitorName is required',
      };

      mockCreateErrorResponse.mockReturnValue(mockErrorResponse);

      const request = createMockRequest(invalidBody);
      const response = await POST(request);
      const responseData = await response.json();

      expect(response.status).toBe(400);
      expect(responseData).toEqual(mockErrorResponse);
      expect(mockCreateErrorResponse).toHaveBeenCalledWith('Missing Parameter', 'visitorName is required');
      expect(mockSendIntercomNotification).not.toHaveBeenCalled();
    });

    it('should return validation error when visitorName is not a string', async () => {
      const invalidBody = {
        visitorName: 123,
        roomName: 'room-test-123',
      };

      const mockErrorResponse = {
        error: 'Missing Parameter',
        message: 'visitorName is required',
      };

      mockCreateErrorResponse.mockReturnValue(mockErrorResponse);

      const request = createMockRequest(invalidBody);
      const response = await POST(request);
      const responseData = await response.json();

      expect(response.status).toBe(400);
      expect(responseData).toEqual(mockErrorResponse);
      expect(mockSendIntercomNotification).not.toHaveBeenCalled();
    });

    it('should return validation error when roomName is missing', async () => {
      const invalidBody = {
        visitorName: '田中太郎',
        purpose: 'test',
      };

      const mockErrorResponse = {
        error: 'Missing Parameter',
        message: 'roomName is required',
      };

      mockCreateErrorResponse.mockReturnValue(mockErrorResponse);

      const request = createMockRequest(invalidBody);
      const response = await POST(request);
      const responseData = await response.json();

      expect(response.status).toBe(400);
      expect(responseData).toEqual(mockErrorResponse);
      expect(mockSendIntercomNotification).not.toHaveBeenCalled();
    });

    it('should return validation error when roomName is not a string', async () => {
      const invalidBody = {
        visitorName: '田中太郎',
        roomName: null,
      };

      const mockErrorResponse = {
        error: 'Missing Parameter',
        message: 'roomName is required',
      };

      mockCreateErrorResponse.mockReturnValue(mockErrorResponse);

      const request = createMockRequest(invalidBody);
      const response = await POST(request);

      expect(response.status).toBe(400);
      expect(mockSendIntercomNotification).not.toHaveBeenCalled();
    });

    it('should return 500 when Slack notification fails', async () => {
      mockSendIntercomNotification.mockResolvedValue(false);

      const mockErrorResponse = {
        error: 'Notification Failed',
        message: 'Could not send Slack notification',
      };

      mockCreateErrorResponse.mockReturnValue(mockErrorResponse);

      const request = createMockRequest(validRequestBody);
      const response = await POST(request);
      const responseData = await response.json();

      expect(response.status).toBe(500);
      expect(responseData).toEqual(mockErrorResponse);
      expect(mockLogError).toHaveBeenCalledWith('Failed to send Slack notification');
    });

    it('should handle JSON parsing errors', async () => {
      const mockErrorResponse = {
        error: 'Internal Server Error',
        message: 'Unexpected token < in JSON at position 0',
      };

      mockCreateErrorResponse.mockReturnValue(mockErrorResponse);

      // Create a request with invalid JSON
      const request = new NextRequest('http://localhost:3000/api/slack/notify', {
        method: 'POST',
        body: '<html>invalid json</html>',
        headers: {
          'content-type': 'application/json',
        },
      });

      const response = await POST(request);
      const responseData = await response.json();

      expect(response.status).toBe(500);
      expect(responseData).toEqual(mockErrorResponse);
      expect(mockLogError).toHaveBeenCalledWith('Slack notification API error', expect.any(Error));
    });

    it('should handle sendIntercomNotification throwing an error', async () => {
      const notificationError = new Error('Slack API error');
      mockSendIntercomNotification.mockRejectedValue(notificationError);

      const mockErrorResponse = {
        error: 'Internal Server Error',
        message: 'Slack API error',
      };

      mockCreateErrorResponse.mockReturnValue(mockErrorResponse);

      const request = createMockRequest(validRequestBody);
      const response = await POST(request);
      const responseData = await response.json();

      expect(response.status).toBe(500);
      expect(responseData).toEqual(mockErrorResponse);
      expect(mockLogError).toHaveBeenCalledWith('Slack notification API error', notificationError);
    });

    it('should handle unknown errors', async () => {
      // Mock an error that's not an instance of Error
      mockSendIntercomNotification.mockRejectedValue('String error');

      const mockErrorResponse = {
        error: 'Internal Server Error',
        message: 'Unknown error occurred',
      };

      mockCreateErrorResponse.mockReturnValue(mockErrorResponse);

      const request = createMockRequest(validRequestBody);
      const response = await POST(request);
      const responseData = await response.json();

      expect(response.status).toBe(500);
      expect(responseData).toEqual(mockErrorResponse);
    });

    it('should generate JST timestamp correctly', async () => {
      mockSendIntercomNotification.mockResolvedValue(true);

      // Mock Date to return a predictable value
      const mockDate = new Date('2024-01-15T05:30:00Z'); // UTC time
      jest.spyOn(global, 'Date').mockImplementation((() => mockDate) as any);

      const request = createMockRequest(validRequestBody);
      await POST(request);

      expect(mockSendIntercomNotification).toHaveBeenCalledWith(
        expect.objectContaining({
          timestamp: '2024/01/15 14:30', // Converted to JST (+9 hours)
        })
      );

      (global.Date as any).mockRestore();
    });
  });

  describe('Unsupported HTTP methods', () => {
    it('should return 405 for GET requests', async () => {
      const expectedErrorResponse = {
        error: 'Method Not Allowed',
        message: 'Only POST requests are supported',
      };

      mockCreateErrorResponse.mockReturnValue(expectedErrorResponse);

      const response = await GET();
      const responseData = await response.json();

      expect(response.status).toBe(405);
      expect(responseData).toEqual(expectedErrorResponse);
    });

    it('should return 405 for PUT requests', async () => {
      const expectedErrorResponse = {
        error: 'Method Not Allowed',
        message: 'Only POST requests are supported',
      };

      mockCreateErrorResponse.mockReturnValue(expectedErrorResponse);

      const response = await PUT();
      const responseData = await response.json();

      expect(response.status).toBe(405);
      expect(responseData).toEqual(expectedErrorResponse);
    });

    it('should return 405 for DELETE requests', async () => {
      const expectedErrorResponse = {
        error: 'Method Not Allowed',
        message: 'Only POST requests are supported',
      };

      mockCreateErrorResponse.mockReturnValue(expectedErrorResponse);

      const response = await DELETE();
      const responseData = await response.json();

      expect(response.status).toBe(405);
      expect(responseData).toEqual(expectedErrorResponse);
    });
  });

  describe('URL Encoding', () => {
    it('should properly encode room names with special characters', async () => {
      const bodyWithSpecialChars = {
        visitorName: 'テスト太郎',
        roomName: 'room-テスト太郎-123 & 456',
      };

      mockSendIntercomNotification.mockResolvedValue(true);

      const request = createMockRequest(bodyWithSpecialChars);
      await POST(request);

      const expectedEncodedRoom = encodeURIComponent('room-テスト太郎-123 & 456');
      const expectedJoinUrl = `https://example.com/video-call?room=${expectedEncodedRoom}&staff=true`;

      expect(mockSendIntercomNotification).toHaveBeenCalledWith(
        expect.objectContaining({
          joinUrl: expectedJoinUrl,
        })
      );
    });

    it('should handle empty room names gracefully', async () => {
      const bodyWithEmptyRoom = {
        visitorName: 'テスト太郎',
        roomName: '',
      };

      const mockErrorResponse = {
        error: 'Missing Parameter',
        message: 'roomName is required',
      };

      mockCreateErrorResponse.mockReturnValue(mockErrorResponse);

      const request = createMockRequest(bodyWithEmptyRoom);
      const response = await POST(request);

      expect(response.status).toBe(400);
      expect(mockSendIntercomNotification).not.toHaveBeenCalled();
    });
  });

  describe('Response Data Consistency', () => {
    it('should return consistent data structure on success', async () => {
      mockSendIntercomNotification.mockResolvedValue(true);

      const request = createMockRequest(validRequestBody);
      const response = await POST(request);
      const responseData = await response.json();

      expect(responseData).toHaveProperty('success');
      expect(responseData).toHaveProperty('message');
      expect(responseData).toHaveProperty('data');
      expect(responseData.data).toHaveProperty('visitorName');
      expect(responseData.data).toHaveProperty('roomName');
      expect(responseData.data).toHaveProperty('joinUrl');

      expect(typeof responseData.success).toBe('boolean');
      expect(typeof responseData.message).toBe('string');
      expect(typeof responseData.data).toBe('object');
    });

    it('should maintain data types in response', async () => {
      mockSendIntercomNotification.mockResolvedValue(true);

      const request = createMockRequest(validRequestBody);
      const response = await POST(request);
      const responseData = await response.json();

      expect(responseData.success).toBe(true);
      expect(responseData.data.visitorName).toBe(validRequestBody.visitorName);
      expect(responseData.data.roomName).toBe(validRequestBody.roomName);
      expect(typeof responseData.data.joinUrl).toBe('string');
    });
  });
});