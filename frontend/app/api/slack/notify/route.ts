// API route for sending Slack notifications when video rooms are created

import { NextRequest, NextResponse } from 'next/server';
import { sendIntercomNotification } from '@/lib/services/slack-webhook';
import { createErrorResponse, logInfo, logError, logSuccess } from '@/lib/utils';

interface NotificationRequest {
  visitorName: string;
  purpose: string;
  roomName: string;
  roomUrl?: string; // Optional, will construct if not provided
}

export async function POST(request: NextRequest) {
  try {
    logInfo('Slack notification request received');

    // Parse request body
    const body: NotificationRequest = await request.json();
    
    // Validate required fields
    if (!body.visitorName || typeof body.visitorName !== 'string') {
      return NextResponse.json(
        createErrorResponse('Missing Parameter', 'visitorName is required'),
        { status: 400 }
      );
    }

    if (!body.roomName || typeof body.roomName !== 'string') {
      return NextResponse.json(
        createErrorResponse('Missing Parameter', 'roomName is required'),
        { status: 400 }
      );
    }

    // Construct the join URL for staff
    const baseUrl = process.env.NEXTAUTH_URL || process.env.VERCEL_URL || 'http://localhost:3000';
    const joinUrl = body.roomUrl || `${baseUrl}/video-call?room=${encodeURIComponent(body.roomName)}&staff=true`;

    const notificationData = {
      visitorName: body.visitorName,
      purpose: body.purpose || 'お客様対応',
      roomName: body.roomName,
      joinUrl,
      timestamp: new Date().toLocaleString('ja-JP', {
        timeZone: 'Asia/Tokyo',
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      }),
    };

    logInfo(`Sending Slack notification for visitor: ${body.visitorName}, room: ${body.roomName}`);

    // Send Slack notification
    const success = await sendIntercomNotification(notificationData);

    if (success) {
      logSuccess(`Slack notification sent successfully for visitor: ${body.visitorName}`, {
        visitorName: body.visitorName,
        roomName: body.roomName,
        joinUrl,
      });

      return NextResponse.json({
        success: true,
        message: 'Slack notification sent successfully',
        data: {
          visitorName: body.visitorName,
          roomName: body.roomName,
          joinUrl,
        },
      }, { status: 200 });
    } else {
      logError('Failed to send Slack notification');
      return NextResponse.json(
        createErrorResponse('Notification Failed', 'Could not send Slack notification'),
        { status: 500 }
      );
    }

  } catch (error) {
    logError('Slack notification API error', error);
    
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
export async function GET() {
  return NextResponse.json(
    createErrorResponse('Method Not Allowed', 'Only POST requests are supported'),
    { status: 405 }
  );
}

export async function PUT() {
  return NextResponse.json(
    createErrorResponse('Method Not Allowed', 'Only POST requests are supported'),
    { status: 405 }
  );
}

export async function DELETE() {
  return NextResponse.json(
    createErrorResponse('Method Not Allowed', 'Only POST requests are supported'),
    { status: 405 }
  );
}