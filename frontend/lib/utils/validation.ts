// Validation utilities for the intercom system

export function sanitizeVisitorName(name: string): string {
  if (!name || typeof name !== 'string') {
    return 'ゲスト';
  }
  
  // Remove dangerous characters and trim
  const sanitized = name.trim().replace(/[<>\"'&]/g, '');
  
  // Return default if empty after sanitization
  return sanitized || 'ゲスト';
}

export function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

export function isValidPhoneNumber(phone: string): boolean {
  const phoneRegex = /^[\d\s\-\(\)\+]+$/;
  return phoneRegex.test(phone);
}

export function sanitizeString(input: string, maxLength: number = 100): string {
  if (!input || typeof input !== 'string') {
    return '';
  }
  
  return input.trim().slice(0, maxLength).replace(/[<>\"'&]/g, '');
}