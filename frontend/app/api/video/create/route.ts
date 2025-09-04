// Video room creation API route for simple intercom system

import { NextRequest, NextResponse } from 'next/server';
import { getTwilioService } from '@/lib/services/twilio';
import { 
  sanitizeVisitorName,
} from '@/lib/utils/validation';
import { createErrorResponse, logInfo, logError, logSuccess } from '@/lib/utils';

export async function POST(request: NextRequest) {
  try {
    logInfo('Intercom video room creation request received');

    // Parse request body - simplified for intercom use case
    const body: { visitorName: string; purpose?: string; } = await request.json();
    
    // Validate visitor name
    if (!body.visitorName || typeof body.visitorName !== 'string') {
      return NextResponse.json(
        createErrorResponse('Missing Parameter', 'visitorName is required'),
        { status: 400 }
      );
    }

    // Sanitize visitor name
    const sanitizedVisitorName = sanitizeVisitorName(body.visitorName);
    
    logInfo(`Creating intercom video room for visitor: ${sanitizedVisitorName}`);

    try {
      // Create Twilio video room
      const twilioService = getTwilioService();
      const videoRoom = await twilioService.createRoom(sanitizedVisitorName);

      logSuccess(`Intercom video room created for visitor: ${sanitizedVisitorName}`, {
        roomName: videoRoom.room_name,
        roomSid: videoRoom.room_sid,
        visitor: sanitizedVisitorName,
        roomUrl: videoRoom.room_url,
        purpose: body.purpose || 'general'
      });

      // Simplified response for intercom use case
      const response = {
        video_room: videoRoom,
        visitor_name: sanitizedVisitorName,
        purpose: body.purpose || 'general',
        success: true,
      };

      return NextResponse.json(response, { status: 201 });

    } catch (twilioError) {
      logError('Twilio video room creation error', twilioError);
      
      return NextResponse.json(
        createErrorResponse(
          'Video Room Creation Failed',
          twilioError instanceof Error ? twilioError.message : 'Unknown Twilio error occurred'
        ),
        { status: 503 }
      );
    }

  } catch (error) {
    logError('Video room creation API error', error);
    
    return NextResponse.json(
      createErrorResponse(
        'Internal Server Error',
        error instanceof Error ? error.message : 'Unknown error occurred'
      ),
      { status: 500 }
    );
  }
}

// GET method for generating staff access tokens (simplified for intercom)
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const roomName = searchParams.get('room_name');
    const staffName = searchParams.get('staff_name') || 'Staff';
    
    if (!roomName) {
      return NextResponse.json(
        createErrorResponse('Missing Parameter', 'room_name query parameter is required'),
        { status: 400 }
      );
    }

    logInfo(`Generating staff token for intercom room: ${roomName}, staff: ${staffName}`);

    try {
      // Generate staff access token
      const twilioService = getTwilioService();
      const staffToken = await twilioService.generateStaffToken(roomName, staffName);

      logSuccess(`Staff token generated for intercom room: ${roomName}`, {
        staffName,
        identity: staffToken.identity,
      });

      return NextResponse.json({
        access_token: staffToken.access_token,
        identity: staffToken.identity,
        room_name: roomName,
        success: true,
      }, { status: 200 });

    } catch (twilioError) {
      logError('Staff token generation error', twilioError);
      
      return NextResponse.json(
        createErrorResponse(
          'Staff Token Generation Failed',
          twilioError instanceof Error ? twilioError.message : 'Unknown Twilio error occurred'
        ),
        { status: 503 }
      );
    }

  } catch (error) {
    logError('Staff token generation API error', error);
    
    return NextResponse.json(
      createErrorResponse(
        'Internal Server Error',
        error instanceof Error ? error.message : 'Unknown error occurred'
      ),
      { status: 500 }
    );
  }
}

// DELETE method for ending video rooms
export async function DELETE(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const roomName = searchParams.get('room_name');
    
    if (!roomName) {
      return NextResponse.json(
        createErrorResponse('Missing Parameter', 'room_name query parameter is required'),
        { status: 400 }
      );
    }

    logInfo(`Ending video room: ${roomName}`);

    try {
      // End Twilio video room
      const twilioService = getTwilioService();
      const roomEnded = await twilioService.endRoom(roomName);

      if (roomEnded) {
        logSuccess(`Video room ended: ${roomName}`);
        return NextResponse.json({
          room_name: roomName,
          ended: true,
          success: true,
        }, { status: 200 });
      } else {
        logError(`Failed to end video room: ${roomName}`);
        return NextResponse.json(
          createErrorResponse('Room End Failed', 'Could not end the video room'),
          { status: 500 }
        );
      }

    } catch (twilioError) {
      logError('Video room end error', twilioError);
      
      return NextResponse.json(
        createErrorResponse(
          'Video Room End Failed',
          twilioError instanceof Error ? twilioError.message : 'Unknown Twilio error occurred'
        ),
        { status: 503 }
      );
    }

  } catch (error) {
    logError('Video room end API error', error);
    
    return NextResponse.json(
      createErrorResponse(
        'Internal Server Error',
        error instanceof Error ? error.message : 'Unknown error occurred'
      ),
      { status: 500 }
    );
  }
}

// Handle unsupported methods
export async function PUT() {
  return NextResponse.json(
    createErrorResponse('Method Not Allowed', 'Only GET, POST, and DELETE requests are supported'),
    { status: 405 }
  );
}