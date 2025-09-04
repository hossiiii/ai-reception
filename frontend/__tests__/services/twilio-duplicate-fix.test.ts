// Test for verifying duplicate identity fix in Twilio service

import { describe, it, expect, beforeEach } from '@jest/globals';
import { getTwilioService } from '@/lib/services/twilio';

describe('Twilio Duplicate Identity Fix', () => {
  let twilioService: any;

  beforeEach(() => {
    // Get fresh instance for each test
    twilioService = getTwilioService();
  });

  it('should generate unique identities for the same visitor name', async () => {
    const visitorName = 'TestUser';
    
    // Create multiple rooms with same visitor name
    const room1 = await twilioService.createRoom(visitorName);
    const room2 = await twilioService.createRoom(visitorName);
    const room3 = await twilioService.createRoom(visitorName);
    
    // Visitor identities should be unique
    expect(room1.visitor_identity).not.toBe(room2.visitor_identity);
    expect(room2.visitor_identity).not.toBe(room3.visitor_identity);
    expect(room1.visitor_identity).not.toBe(room3.visitor_identity);
    
    // All should contain the base visitor name
    expect(room1.visitor_identity).toContain('TestUser_visitor');
    expect(room2.visitor_identity).toContain('TestUser_visitor');
    expect(room3.visitor_identity).toContain('TestUser_visitor');
    
    // Should contain timestamps and session IDs
    expect(room1.visitor_identity).toMatch(/TestUser_visitor_\d+_[a-f0-9]{8}/);
    expect(room2.visitor_identity).toMatch(/TestUser_visitor_\d+_[a-f0-9]{8}/);
    expect(room3.visitor_identity).toMatch(/TestUser_visitor_\d+_[a-f0-9]{8}/);
  });

  it('should generate unique staff identities for the same staff name', async () => {
    const staffName = 'TestStaff';
    const roomName = 'test-room';
    
    // Generate multiple staff tokens
    const token1 = await twilioService.generateStaffToken(roomName, staffName);
    const token2 = await twilioService.generateStaffToken(roomName, staffName);
    const token3 = await twilioService.generateStaffToken(roomName, staffName);
    
    // Staff identities should be unique
    expect(token1.identity).not.toBe(token2.identity);
    expect(token2.identity).not.toBe(token3.identity);
    expect(token1.identity).not.toBe(token3.identity);
    
    // All should contain the base staff name
    expect(token1.identity).toContain('TestStaff_staff');
    expect(token2.identity).toContain('TestStaff_staff');
    expect(token3.identity).toContain('TestStaff_staff');
    
    // Should contain timestamps and session IDs
    expect(token1.identity).toMatch(/TestStaff_staff_\d+_[a-f0-9]{8}/);
    expect(token2.identity).toMatch(/TestStaff_staff_\d+_[a-f0-9]{8}/);
    expect(token3.identity).toMatch(/TestStaff_staff_\d+_[a-f0-9]{8}/);
  });

  it('should handle Japanese names correctly', async () => {
    const visitorName = '田中太郎';
    
    const room1 = await twilioService.createRoom(visitorName);
    const room2 = await twilioService.createRoom(visitorName);
    
    // Should generate unique identities even with Japanese names
    expect(room1.visitor_identity).not.toBe(room2.visitor_identity);
    expect(room1.visitor_identity).toContain('田中太郎_visitor');
    expect(room2.visitor_identity).toContain('田中太郎_visitor');
  });

  it('should handle edge cases', async () => {
    // Empty names (will become default)
    const room1 = await twilioService.createRoom('');
    const room2 = await twilioService.createRoom('');
    
    // Should still generate unique identities for default names
    expect(room1.visitor_identity).not.toBe(room2.visitor_identity);
    expect(room1.visitor_identity).toContain('ゲスト_visitor');
    expect(room2.visitor_identity).toContain('ゲスト_visitor');
    
    // Very long names
    const longName = 'A'.repeat(100);
    const room3 = await twilioService.createRoom(longName);
    expect(room3.visitor_identity).toContain('_visitor_');
  });

  it('should generate identities with correct timestamp ordering', async () => {
    const visitorName = 'TimestampTest';
    
    const room1 = await twilioService.createRoom(visitorName);
    // Small delay to ensure different timestamps
    await new Promise(resolve => setTimeout(resolve, 10));
    const room2 = await twilioService.createRoom(visitorName);
    
    // Extract timestamps
    const timestamp1Match = room1.visitor_identity.match(/_(\d+)_/);
    const timestamp2Match = room2.visitor_identity.match(/_(\d+)_/);
    
    expect(timestamp1Match).toBeTruthy();
    expect(timestamp2Match).toBeTruthy();
    
    const timestamp1 = parseInt(timestamp1Match![1]);
    const timestamp2 = parseInt(timestamp2Match![1]);
    
    // Second timestamp should be greater than or equal to first
    expect(timestamp2).toBeGreaterThanOrEqual(timestamp1);
  });

  it('should maintain room name uniqueness independent of identity', async () => {
    const visitorName = 'RoomTest';
    
    const room1 = await twilioService.createRoom(visitorName);
    const room2 = await twilioService.createRoom(visitorName);
    
    // Room names should be unique (they use UUID)
    expect(room1.room_name).not.toBe(room2.room_name);
    expect(room1.room_name).toMatch(/^reception-[a-f0-9]{8}$/);
    expect(room2.room_name).toMatch(/^reception-[a-f0-9]{8}$/);
    
    // But identities should also be unique
    expect(room1.visitor_identity).not.toBe(room2.visitor_identity);
  });
});