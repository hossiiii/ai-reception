// Utility functions export barrel for non-AI reception system

export * from './session';
export * from './validation';

// Common utility functions
export function generateId(): string {
  return Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
}

export function formatTimestamp(date: Date): string {
  return date.toLocaleString('ja-JP', {
    timeZone: 'Asia/Tokyo',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

export function formatTime(date: Date): string {
  return date.toLocaleTimeString('ja-JP', {
    timeZone: 'Asia/Tokyo',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });
}

export function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

export function isValidUUID(uuid: string): boolean {
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  return uuidRegex.test(uuid);
}

export function truncateString(str: string, maxLength: number): string {
  if (str.length <= maxLength) {
    return str;
  }
  return str.substring(0, maxLength - 3) + '...';
}

export function capitalizeFirst(str: string): string {
  if (!str) return str;
  return str.charAt(0).toUpperCase() + str.slice(1);
}

// Error handling utilities
export function createErrorResponse(error: string, details?: string): { error: string; details?: string; success: false } {
  return {
    error,
    details,
    success: false,
  };
}

export function createSuccessResponse<T>(data: T): T & { success: true } {
  return {
    ...data,
    success: true,
  };
}

// Logging utilities
export function logInfo(message: string, data?: any): void {
  console.log(`ℹ️ ${message}`, data ? data : '');
}

export function logWarning(message: string, data?: any): void {
  console.warn(`⚠️ ${message}`, data ? data : '');
}

export function logError(message: string, error?: any): void {
  console.error(`❌ ${message}`, error ? error : '');
}

export function logSuccess(message: string, data?: any): void {
  console.log(`✅ ${message}`, data ? data : '');
}

// Type guards
export function isString(value: any): value is string {
  return typeof value === 'string';
}

export function isNumber(value: any): value is number {
  return typeof value === 'number' && !isNaN(value);
}

export function isBoolean(value: any): value is boolean {
  return typeof value === 'boolean';
}

export function isObject(value: any): value is object {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

export function isArray(value: any): value is any[] {
  return Array.isArray(value);
}

// Environment utilities
export function isDevelopment(): boolean {
  return process.env.NODE_ENV === 'development';
}

export function isProduction(): boolean {
  return process.env.NODE_ENV === 'production';
}

export function getEnvironment(): string {
  return process.env.NODE_ENV || 'development';
}