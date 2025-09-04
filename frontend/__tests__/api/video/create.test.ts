/**
 * Video Room Creation API Route Tests
 * Tests for /app/api/video/create/route.ts
 */

import { NextRequest } from 'next/server';
import { POST, GET, DELETE, PUT } from '@/app/api/video/create/route';
import * as sessionUtils from '@/lib/utils/session';
import * as validation from '@/lib/utils/validation';
import * as utils from '@/lib/utils';
import * as twilio from '@/lib/services/twilio';

// Mock dependencies
jest.mock('@/lib/utils/session');
jest.mock('@/lib/utils/validation');
jest.mock('@/lib/utils');
jest.mock('@/lib/services/twilio');

const mockGetSession = sessionUtils.getSession as jest.MockedFunction<typeof sessionUtils.getSession>;
const mockUpdateSession = sessionUtils.updateSession as jest.MockedFunction<typeof sessionUtils.updateSession>;
const mockValidateCreateVideoRoomRequest = validation.validateCreateVideoRoomRequest as jest.MockedFunction<typeof validation.validateCreateVideoRoomRequest>;
const mockSanitizeVisitorName = validation.sanitizeVisitorName as jest.MockedFunction<typeof validation.sanitizeVisitorName>;
const mockCreateValidationErrorResponse = validation.createValidationErrorResponse as jest.MockedFunction<typeof validation.createValidationErrorResponse>;
const mockLogValidationErrors = validation.logValidationErrors as jest.MockedFunction<typeof validation.logValidationErrors>;
const mockCreateErrorResponse = utils.createErrorResponse as jest.MockedFunction<typeof utils.createErrorResponse>;
const mockLogInfo = utils.logInfo as jest.MockedFunction<typeof utils.logInfo>;
const mockLogError = utils.logError as jest.MockedFunction<typeof utils.logError>;
const mockLogSuccess = utils.logSuccess as jest.MockedFunction<typeof utils.logSuccess>;
const mockGetTwilioService = twilio.getTwilioService as jest.MockedFunction<typeof twilio.getTwilioService>;

describe('/api/video/create', () => {
  const mockTwilioService = {
    createRoom: jest.fn(),
    generateStaffToken: jest.fn(),
    endRoom: jest.fn(),
  };

  const mockSessionData = {
    visitor_info: {
      name: '田中太郎',
      company: '株式会社テスト',
      purpose: '打ち合わせ',
      confirmed: true,
      correction_count: 0,
      visitor_type: 'appointment',
    },
    conversation_logs: ['ログ1', 'ログ2'],
    calendar_result: {
      found: true,
      roomName: '会議室A',
    },
  };

  const mockVideoRoom = {
    room_name: 'room-田中太郎-123',
    room_sid: 'RM123456789',
    room_url: 'https://video.example.com/room-田中太郎-123',
    visitor_token: {
      token: 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
      identity: '田中太郎',
    },
  };

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Default mock implementations
    mockValidateCreateVideoRoomRequest.mockReturnValue({ isValid: true, errors: [] });
    mockSanitizeVisitorName.mockImplementation((name) => name);
    mockGetSession.mockReturnValue(mockSessionData);
    mockUpdateSession.mockReturnValue(true);
    mockGetTwilioService.mockReturnValue(mockTwilioService as any);
    mockLogInfo.mockImplementation();
    mockLogError.mockImplementation();
    mockLogSuccess.mockImplementation();
  });

  describe('POST method', () => {
    const createMockRequest = (body: any) => {
      const request = new NextRequest('http://localhost:3000/api/video/create', {
        method: 'POST',
        body: JSON.stringify(body),
        headers: {
          'content-type': 'application/json',
        },
      });
      return request;
    };

    it('should create video room successfully', async () => {
      const requestBody = {
        session_id: 'session-123',
        visitor_name: '田中太郎',
        purpose: '打ち合わせ',
      };

      mockTwilioService.createRoom.mockResolvedValue(mockVideoRoom);

      const request = createMockRequest(requestBody);
      const response = await POST(request);
      const responseData = await response.json();

      expect(response.status).toBe(201);
      expect(responseData.success).toBe(true);
      expect(responseData.session_id).toBe('session-123');
      expect(responseData.video_room).toEqual(mockVideoRoom);
      
      expect(mockValidateCreateVideoRoomRequest).toHaveBeenCalledWith(requestBody);
      expect(mockGetSession).toHaveBeenCalledWith('session-123');
      expect(mockSanitizeVisitorName).toHaveBeenCalledWith('田中太郎');
      expect(mockTwilioService.createRoom).toHaveBeenCalledWith('田中太郎');
      expect(mockUpdateSession).toHaveBeenCalledWith('session-123', {
        video_room: mockVideoRoom,
      });
      expect(mockLogSuccess).toHaveBeenCalledWith(
        'Video room created for session: session-123',
        {
          roomName: 'room-田中太郎-123',
          roomSid: 'RM123456789',
          visitor: '田中太郎',
          roomUrl: 'https://video.example.com/room-田中太郎-123',
        }
      );
    });

    it('should return validation error for invalid data', async () => {
      const requestBody = {
        session_id: '',
        visitor_name: '',
      };

      const validationErrors = [
        { field: 'session_id', message: 'セッションIDは必須です' },
        { field: 'visitor_name', message: '訪問者名は必須です' },
      ];

      mockValidateCreateVideoRoomRequest.mockReturnValue({
        isValid: false,
        errors: validationErrors,
      });

      const mockValidationErrorResponse = {
        error: 'Validation Error',
        details: validationErrors,
      };

      mockCreateValidationErrorResponse.mockReturnValue(mockValidationErrorResponse);

      const request = createMockRequest(requestBody);
      const response = await POST(request);
      const responseData = await response.json();

      expect(response.status).toBe(400);
      expect(responseData).toEqual(mockValidationErrorResponse);
      expect(mockLogValidationErrors).toHaveBeenCalledWith('video/create', validationErrors);
      expect(mockGetSession).not.toHaveBeenCalled();
    });

    it('should return 404 when session not found', async () => {
      const requestBody = {
        session_id: 'invalid-session',
        visitor_name: '田中太郎',
      };

      mockGetSession.mockReturnValue(null);

      const mockErrorResponse = {
        error: 'Session Not Found',
        message: 'The provided session ID is invalid or expired',
      };

      mockCreateErrorResponse.mockReturnValue(mockErrorResponse);

      const request = createMockRequest(requestBody);
      const response = await POST(request);
      const responseData = await response.json();

      expect(response.status).toBe(404);
      expect(responseData).toEqual(mockErrorResponse);
      expect(mockLogError).toHaveBeenCalledWith('Session not found: invalid-session');
      expect(mockTwilioService.createRoom).not.toHaveBeenCalled();
    });

    it('should handle session update failure and cleanup room', async () => {
      const requestBody = {
        session_id: 'session-123',
        visitor_name: '田中太郎',
      };

      mockTwilioService.createRoom.mockResolvedValue(mockVideoRoom);
      mockUpdateSession.mockReturnValue(false);
      mockTwilioService.endRoom.mockResolvedValue(true);

      const mockErrorResponse = {
        error: 'Session Update Failed',
        message: 'Could not update session with video room information',
      };

      mockCreateErrorResponse.mockReturnValue(mockErrorResponse);

      const request = createMockRequest(requestBody);
      const response = await POST(request);
      const responseData = await response.json();

      expect(response.status).toBe(500);
      expect(responseData).toEqual(mockErrorResponse);
      expect(mockLogError).toHaveBeenCalledWith('Failed to update session with video room: session-123');
      expect(mockTwilioService.endRoom).toHaveBeenCalledWith('room-田中太郎-123');
    });

    it('should handle cleanup failure after session update failure', async () => {
      const requestBody = {
        session_id: 'session-123',
        visitor_name: '田中太郎',
      };

      mockTwilioService.createRoom.mockResolvedValue(mockVideoRoom);
      mockUpdateSession.mockReturnValue(false);
      mockTwilioService.endRoom.mockRejectedValue(new Error('Cleanup failed'));

      const request = createMockRequest(requestBody);
      const response = await POST(request);

      expect(response.status).toBe(500);
      expect(mockLogError).toHaveBeenCalledWith('Failed to cleanup video room after session update failure', expect.any(Error));
    });

    it('should handle Twilio service error', async () => {
      const requestBody = {
        session_id: 'session-123',
        visitor_name: '田中太郎',
      };

      mockTwilioService.createRoom.mockRejectedValue(
        new Error('Twilio API error')
      );

      const mockErrorResponse = {
        error: 'Video Room Creation Failed',
        message: 'Twilio API error',
      };

      mockCreateErrorResponse.mockReturnValue(mockErrorResponse);

      const request = createMockRequest(requestBody);
      const response = await POST(request);
      const responseData = await response.json();

      expect(response.status).toBe(503);
      expect(responseData).toEqual(mockErrorResponse);
      expect(mockLogError).toHaveBeenCalledWith('Twilio video room creation error', expect.any(Error));
    });
  });

  describe('GET method (staff token generation)', () => {
    it('should generate staff token successfully', async () => {
      const mockStaffToken = {
        token: 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
        identity: 'スタッフ太郎',
      };

      mockTwilioService.generateStaffToken.mockResolvedValue(mockStaffToken);

      const request = new NextRequest('http://localhost:3000/api/video/create?room_name=room-123&staff_name=スタッフ太郎');
      const response = await GET(request);
      const responseData = await response.json();

      expect(response.status).toBe(200);
      expect(responseData.success).toBe(true);
      expect(responseData.token).toBe(mockStaffToken.token);
      expect(responseData.identity).toBe(mockStaffToken.identity);
      
      expect(mockTwilioService.generateStaffToken).toHaveBeenCalledWith('room-123', 'スタッフ太郎');
      expect(mockLogSuccess).toHaveBeenCalledWith(
        'Staff token generated for room: room-123',
        {
          staffName: 'スタッフ太郎',
          identity: 'スタッフ太郎',
        }
      );
    });

    it('should return error when room_name parameter is missing', async () => {
      const mockErrorResponse = {
        error: 'Missing Parameter',
        message: 'room_name query parameter is required',
      };

      mockCreateErrorResponse.mockReturnValue(mockErrorResponse);

      const request = new NextRequest('http://localhost:3000/api/video/create?staff_name=スタッフ太郎');
      const response = await GET(request);
      const responseData = await response.json();

      expect(response.status).toBe(400);
      expect(responseData).toEqual(mockErrorResponse);
      expect(mockTwilioService.generateStaffToken).not.toHaveBeenCalled();
    });

    it('should return error when staff_name parameter is missing', async () => {
      const mockErrorResponse = {
        error: 'Missing Parameter',
        message: 'staff_name query parameter is required',
      };

      mockCreateErrorResponse.mockReturnValue(mockErrorResponse);

      const request = new NextRequest('http://localhost:3000/api/video/create?room_name=room-123');
      const response = await GET(request);
      const responseData = await response.json();

      expect(response.status).toBe(400);
      expect(responseData).toEqual(mockErrorResponse);
    });

    it('should handle staff token generation error', async () => {
      mockTwilioService.generateStaffToken.mockRejectedValue(
        new Error('Token generation failed')
      );

      const mockErrorResponse = {
        error: 'Staff Token Generation Failed',
        message: 'Token generation failed',
      };

      mockCreateErrorResponse.mockReturnValue(mockErrorResponse);

      const request = new NextRequest('http://localhost:3000/api/video/create?room_name=room-123&staff_name=スタッフ太郎');
      const response = await GET(request);
      const responseData = await response.json();

      expect(response.status).toBe(503);
      expect(responseData).toEqual(mockErrorResponse);
      expect(mockLogError).toHaveBeenCalledWith('Staff token generation error', expect.any(Error));
    });
  });

  describe('DELETE method (room termination)', () => {
    it('should end video room successfully', async () => {
      mockTwilioService.endRoom.mockResolvedValue(true);

      const request = new NextRequest('http://localhost:3000/api/video/create?room_name=room-123', {
        method: 'DELETE',
      });
      const response = await DELETE(request);
      const responseData = await response.json();

      expect(response.status).toBe(200);
      expect(responseData.success).toBe(true);
      expect(responseData.room_name).toBe('room-123');
      expect(responseData.ended).toBe(true);
      
      expect(mockTwilioService.endRoom).toHaveBeenCalledWith('room-123');
      expect(mockLogSuccess).toHaveBeenCalledWith('Video room ended: room-123');
    });

    it('should return error when room_name parameter is missing', async () => {
      const mockErrorResponse = {
        error: 'Missing Parameter',
        message: 'room_name query parameter is required',
      };

      mockCreateErrorResponse.mockReturnValue(mockErrorResponse);

      const request = new NextRequest('http://localhost:3000/api/video/create', {
        method: 'DELETE',
      });
      const response = await DELETE(request);
      const responseData = await response.json();

      expect(response.status).toBe(400);
      expect(responseData).toEqual(mockErrorResponse);
      expect(mockTwilioService.endRoom).not.toHaveBeenCalled();
    });

    it('should handle room end failure', async () => {
      mockTwilioService.endRoom.mockResolvedValue(false);

      const mockErrorResponse = {
        error: 'Room End Failed',
        message: 'Could not end the video room',
      };

      mockCreateErrorResponse.mockReturnValue(mockErrorResponse);

      const request = new NextRequest('http://localhost:3000/api/video/create?room_name=room-123', {
        method: 'DELETE',
      });
      const response = await DELETE(request);
      const responseData = await response.json();

      expect(response.status).toBe(500);
      expect(responseData).toEqual(mockErrorResponse);
      expect(mockLogError).toHaveBeenCalledWith('Failed to end video room: room-123');
    });

    it('should handle Twilio service error when ending room', async () => {
      mockTwilioService.endRoom.mockRejectedValue(
        new Error('Twilio API error')
      );

      const mockErrorResponse = {
        error: 'Video Room End Failed',
        message: 'Twilio API error',
      };

      mockCreateErrorResponse.mockReturnValue(mockErrorResponse);

      const request = new NextRequest('http://localhost:3000/api/video/create?room_name=room-123', {
        method: 'DELETE',
      });
      const response = await DELETE(request);
      const responseData = await response.json();

      expect(response.status).toBe(503);
      expect(responseData).toEqual(mockErrorResponse);
      expect(mockLogError).toHaveBeenCalledWith('Video room end error', expect.any(Error));
    });
  });

  describe('Unsupported HTTP methods', () => {
    it('should return 405 for PUT requests', async () => {
      const expectedErrorResponse = {
        error: 'Method Not Allowed',
        message: 'Only GET, POST, and DELETE requests are supported',
      };

      mockCreateErrorResponse.mockReturnValue(expectedErrorResponse);

      const response = await PUT();
      const responseData = await response.json();

      expect(response.status).toBe(405);
      expect(responseData).toEqual(expectedErrorResponse);
    });
  });
});