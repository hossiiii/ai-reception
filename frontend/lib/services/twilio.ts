// Twilio Video service for Next.js (ported from Python)

import { v4 as uuidv4 } from 'uuid';
import { getTwilioConfig } from '../config';

// Local type definitions to avoid import issues
interface VideoRoomInfo {
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

interface StaffTokenInfo {
  access_token: string;
  identity: string;
}

// JWT types for manual token generation
interface JWTHeader {
  alg: string;
  typ: string;
  cty: string; // Content type header for Twilio
}

interface JWTPayload {
  iss: string;
  sub: string;
  aud: string[];
  exp: number;
  iat: number;
  jti: string;
  grants: {
    identity: string;
    video: {
      room: string;
    };
  };
}

export class TwilioService {
  private accountSid: string;
  private authToken: string;
  private apiKey: string;
  private apiSecret: string;
  private frontendUrl: string;
  private useMock: boolean;

  constructor() {
    const config = getTwilioConfig();
    this.accountSid = config.accountSid;
    this.authToken = config.authToken;
    this.apiKey = config.apiKey;
    this.apiSecret = config.apiSecret;
    this.frontendUrl = config.frontendUrl;
    this.useMock = config.useMock;

    if (this.useMock) {
      console.log('⚠️ Twilio credentials not configured. Video calls will be mocked.');
    } else {
      console.log('✅ TwilioService initialized with Twilio API');
    }
  }

  async createRoom(visitorName: string): Promise<VideoRoomInfo> {
    // Sanitize visitor name to ensure it's valid
    const sanitizedVisitorName = this.sanitizeNameForIdentity(visitorName);
    
    // Generate unique room name with prefix
    const roomName = `reception-${uuidv4().substring(0, 8)}`;

    // If in development mode without credentials, return mock data
    if (this.useMock) {
      console.log(`🔧 Development mode: Mocking room creation for ${sanitizedVisitorName}`);
      return this.createMockRoomResponse(roomName, sanitizedVisitorName);
    }

    try {
      console.log(`🔄 Creating Twilio video room: ${roomName}`);

      // Try to create room with timeout parameters suitable for trial accounts
      let room: any = null;
      let creationMethod = '';

      try {
        // Attempt 1: Create room with trial-compatible timeout values
        room = await this.createTwilioRoom(roomName, {
          type: 'group', // Group room for up to 50 participants
          maxParticipants: 2, // Limit to 2 for reception use case
          recordParticipantsOnConnect: false, // Disable recording for free trial
          emptyRoomTimeout: 60, // 1 minute (compatible with trial accounts)
          unusedRoomTimeout: 60, // 1 minute (compatible with trial accounts)
        });
        creationMethod = 'with trial-compatible timeouts (60s)';

      } catch (timeoutError) {
        if (timeoutError instanceof Error && timeoutError.message.includes('Timeout is out of range')) {
          console.log('⚠️ Trial timeout values failed, trying without timeout parameters...');

          // Attempt 2: Create room without timeout parameters (uses Twilio defaults)
          room = await this.createTwilioRoom(roomName, {
            type: 'group',
            maxParticipants: 2,
            recordParticipantsOnConnect: false,
            // No timeout parameters - uses Twilio defaults
          });
          creationMethod = 'without timeout parameters (Twilio defaults)';
        } else {
          // Re-throw if it's not a timeout-related error
          throw timeoutError;
        }
      }

      if (room) {
        console.log(`✅ Successfully created Twilio room ${creationMethod}: ${room.sid}`);
      } else {
        throw new Error('Failed to create room with any configuration');
      }

      // Generate unique access token for visitor with timestamp to prevent duplicates
      const timestamp = Date.now();
      const sessionId = uuidv4().substring(0, 8);
      const identity = `${sanitizedVisitorName}_visitor_${timestamp}_${sessionId}`;
      const accessToken = this.generateAccessToken(identity, roomName);

      // Generate room URL for staff joining via Slack
      const roomUrl = `${this.frontendUrl}/video-call?room=${roomName}&staff=true`;

      // Calculate expiry times
      const createdAt = new Date();
      const expiresAt = new Date(createdAt.getTime() + 60 * 60 * 1000); // 1 hour

      return {
        room_name: roomName,
        room_sid: room.sid,
        access_token: accessToken,
        room_url: roomUrl,
        created_at: createdAt.toISOString(),
        expires_at: expiresAt.toISOString(),
        visitor_identity: identity,
        max_participants: 2,
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error(`❌ Failed to create Twilio room: ${errorMessage}`);

      // Provide specific error messages for common issues
      if (errorMessage.includes('Type must be one of')) {
        throw new Error('Invalid room type. Please check Twilio account permissions for room types.');
      } else if (errorMessage.includes('Invalid Access Token') || errorMessage.toLowerCase().includes('authentication')) {
        throw new Error('Twilio authentication failed. Please verify TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN.');
      } else if (errorMessage.includes('API Key')) {
        throw new Error('API Key error. Ensure TWILIO_API_KEY and TWILIO_API_SECRET are set and the API Key is in US1 region.');
      } else {
        // For development/testing, return mock response for unknown errors
        console.log('🔧 Falling back to mock response due to Twilio error');
        return this.createMockRoomResponse(roomName, sanitizedVisitorName);
      }
    }
  }

  async generateStaffToken(roomName: string, staffName: string): Promise<StaffTokenInfo> {
    // Validate room name
    if (!roomName || !roomName.trim()) {
      throw new Error('Room name cannot be empty');
    }

    // Sanitize staff name for identity
    const sanitizedStaffName = this.sanitizeNameForIdentity(staffName);

    if (this.useMock) {
      console.log('🔧 Development mode: Returning mock staff token');
      // Create mock JWT token for staff (similar to visitor token)
      const mockJwtHeader = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9';
      const mockJwtPayload = 'eyJpc3MiOiJtb2NrIiwic3ViIjoic3RhZmYiLCJhdWQiOlsidmlkZW8iXSwiZXhwIjo5OTk5OTk5OTk5LCJpYXQiOjE2MDAwMDAwMDAsImp0aSI6Im1vY2tfc3RhZmZfand0X2lkIiwiZ3JhbnRzIjp7InZpZGVvIjp7InJvb20iOiJ0ZXN0LXJvb20tc3RhZmYifX19';
      const mockJwtSignature = 'mock_staff_signature_for_development';
      const mockStaffToken = `${mockJwtHeader}.${mockJwtPayload}.${mockJwtSignature}`;

      // Generate unique mock identity to match production behavior
      const timestamp = Date.now();
      const sessionId = uuidv4().substring(0, 8);
      const uniqueIdentity = `${sanitizedStaffName}_staff_${timestamp}_${sessionId}`;
      
      return {
        access_token: mockStaffToken,
        identity: uniqueIdentity,
      };
    }

    try {
      // Generate unique staff identity with timestamp to prevent duplicates
      const timestamp = Date.now();
      const sessionId = uuidv4().substring(0, 8);
      const identity = `${sanitizedStaffName}_staff_${timestamp}_${sessionId}`;
      const accessToken = this.generateAccessToken(identity, roomName);

      return {
        access_token: accessToken,
        identity,
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error(`❌ Failed to generate staff token: ${errorMessage}`);
      throw new Error(`Staff token generation failed: ${errorMessage}`);
    }
  }

  async endRoom(roomName: string): Promise<boolean> {
    if (this.useMock) {
      console.log(`🔧 Development mode: Mocking room end for ${roomName}`);
      return true;
    }

    try {
      // Update room status to completed
      await this.updateTwilioRoom(roomName, 'completed');
      console.log(`Room ${roomName} ended successfully`);
      return true;
    } catch (error) {
      console.error(`Failed to end room ${roomName}:`, error);
      return false;
    }
  }

  private async createTwilioRoom(roomName: string, options: any): Promise<any> {
    const url = `https://video.twilio.com/v1/Rooms`;
    
    const formData = new URLSearchParams();
    formData.append('UniqueName', roomName);
    formData.append('Type', options.type);
    formData.append('MaxParticipants', options.maxParticipants.toString());
    formData.append('RecordParticipantsOnConnect', options.recordParticipantsOnConnect.toString());
    
    if (options.emptyRoomTimeout !== undefined) {
      formData.append('EmptyRoomTimeout', options.emptyRoomTimeout.toString());
    }
    if (options.unusedRoomTimeout !== undefined) {
      formData.append('UnusedRoomTimeout', options.unusedRoomTimeout.toString());
    }

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': `Basic ${Buffer.from(`${this.accountSid}:${this.authToken}`).toString('base64')}`,
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Twilio API error: ${response.status} ${errorText}`);
    }

    return response.json();
  }

  private async updateTwilioRoom(roomName: string, status: string): Promise<any> {
    const url = `https://video.twilio.com/v1/Rooms/${roomName}`;
    
    const formData = new URLSearchParams();
    formData.append('Status', status);

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': `Basic ${Buffer.from(`${this.accountSid}:${this.authToken}`).toString('base64')}`,
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Twilio API error: ${response.status} ${errorText}`);
    }

    return response.json();
  }

  private generateAccessToken(identity: string, roomName: string): string {
    // Validate required credentials
    if (!this.apiKey || !this.apiSecret) {
      throw new Error('API key and secret are required for token generation. Ensure TWILIO_API_KEY and TWILIO_API_SECRET are set.');
    }

    if (!this.accountSid) {
      throw new Error('Account SID is required for token generation. Ensure TWILIO_ACCOUNT_SID is set.');
    }

    // Validate identity (must be non-empty and valid format)
    if (!identity || !identity.trim()) {
      throw new Error('Identity cannot be empty');
    }

    // Sanitize identity to ensure it meets Twilio requirements
    const sanitizedIdentity = identity.trim().replace(/\s/g, '_').substring(0, 50); // Max 50 chars, no spaces

    // Create JWT manually (since we're in a browser environment)
    try {
      const now = Math.floor(Date.now() / 1000);
      const exp = now + 3600; // 1 hour expiry

      const header: JWTHeader = {
        alg: 'HS256',
        typ: 'JWT',
        cty: 'twilio-fpa;v=1'
      };

      const payload: JWTPayload = {
        iss: this.apiKey,
        sub: this.accountSid,
        aud: ['video'],
        exp,
        iat: now,
        jti: uuidv4(),
        grants: {
          identity: sanitizedIdentity,
          video: {
            room: roomName,
          },
        },
      };

      // Simple JWT creation for Node.js environment
      const headerB64 = Buffer.from(JSON.stringify(header)).toString('base64url');
      const payloadB64 = Buffer.from(JSON.stringify(payload)).toString('base64url');
      
      // Create signature using HMAC SHA256
      const crypto = require('crypto');
      const signature = crypto
        .createHmac('sha256', this.apiSecret)
        .update(`${headerB64}.${payloadB64}`)
        .digest('base64url');

      const jwtToken = `${headerB64}.${payloadB64}.${signature}`;
      
      console.log(`✅ Generated JWT token for identity: ${sanitizedIdentity}, room: ${roomName}`);
      console.log(`🔐 Identity details - Original: ${identity}, Sanitized: ${sanitizedIdentity}, Room: ${roomName}`);
      return jwtToken;

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error(`❌ Failed to generate JWT token: ${errorMessage}`);
      throw new Error(`JWT token generation failed: ${errorMessage}`);
    }
  }

  private createMockRoomResponse(roomName: string, visitorName: string): VideoRoomInfo {
    const createdAt = new Date();
    const expiresAt = new Date(createdAt.getTime() + 60 * 60 * 1000); // 1 hour

    // Create a properly formatted mock JWT token that looks valid to frontend
    // This allows development testing without real Twilio credentials
    const mockJwtHeader = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9'; // {"alg":"HS256","typ":"JWT"}
    const mockJwtPayload = 'eyJpc3MiOiJtb2NrIiwic3ViIjoidGVzdCIsImF1ZCI6WyJ2aWRlbyJdLCJleHAiOjk5OTk5OTk5OTksImlhdCI6MTYwMDAwMDAwMCwianRpIjoibW9ja19qd3RfaWQiLCJncmFudHMiOnsidmlkZW8iOnsicm9vbSI6InRlc3Qtcm9vbSJ9fX0'; // Mock payload with video grant
    const mockJwtSignature = 'mock_signature_for_development_only';
    const mockAccessToken = `${mockJwtHeader}.${mockJwtPayload}.${mockJwtSignature}`;

    // Generate unique mock visitor identity to match production behavior
    const timestamp = Date.now();
    const sessionId = uuidv4().substring(0, 8);
    const uniqueVisitorIdentity = `${visitorName}_visitor_${timestamp}_${sessionId}`;

    return {
      room_name: roomName,
      room_sid: `mock_sid_${roomName}`,
      access_token: mockAccessToken,
      room_url: `${this.frontendUrl}/video-call?room=${roomName}&staff=true`,
      created_at: createdAt.toISOString(),
      expires_at: expiresAt.toISOString(),
      visitor_identity: uniqueVisitorIdentity,
      max_participants: 2,
      mock: true,
    };
  }

  private sanitizeNameForIdentity(name: string): string {
    if (!name || typeof name !== 'string') {
      return 'ゲスト';
    }
    
    // Remove dangerous characters and trim
    const sanitized = name.trim().replace(/[<>\"'&]/g, '');
    
    // Return default if empty after sanitization
    return sanitized || 'ゲスト';
  }
}

// Create singleton instance
let twilioService: TwilioService | null = null;

export function getTwilioService(): TwilioService {
  if (!twilioService) {
    twilioService = new TwilioService();
  }
  return twilioService;
}

export default TwilioService;