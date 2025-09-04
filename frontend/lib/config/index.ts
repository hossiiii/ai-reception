// Configuration management for Simple Intercom System

export interface AppConfig {
  // Twilio Video Configuration
  twilioAccountSid: string;
  twilioAuthToken: string;
  twilioApiKey: string;
  twilioApiSecret: string;
  frontendUrl: string;
  
  // Application Configuration
  environment: string;
  debug: boolean;
}

class ConfigManager {
  private config: AppConfig;

  constructor() {
    this.config = {
      // Twilio Video Configuration
      twilioAccountSid: process.env.TWILIO_ACCOUNT_SID || '',
      twilioAuthToken: process.env.TWILIO_AUTH_TOKEN || '',
      twilioApiKey: process.env.TWILIO_API_KEY || '',
      twilioApiSecret: process.env.TWILIO_API_SECRET || '',
      frontendUrl: process.env.FRONTEND_URL || 'http://localhost:3000',
      
      // Application Configuration
      environment: process.env.NODE_ENV || 'development',
      debug: process.env.NODE_ENV === 'development',
    };
  }

  get(): AppConfig;
  get<K extends keyof AppConfig>(key: K): AppConfig[K];
  get<K extends keyof AppConfig>(key?: K): AppConfig | AppConfig[K] {
    if (key === undefined) {
      return this.config;
    }
    return this.config[key];
  }

  // Helper methods for specific configurations
  getCorsOrigins(): string[] {
    if (this.config.environment === 'development') {
      return ['*'];
    } else {
      const allowedOrigins = process.env.ALLOWED_ORIGINS || '';
      if (allowedOrigins) {
        return allowedOrigins.split(',').map(origin => origin.trim()).filter(origin => origin);
      }
      return [];
    }
  }

  getCorsAllowCredentials(): boolean {
    const origins = this.getCorsOrigins();
    return !origins.includes('*');
  }

  // Validation methods
  validateTwilioConfig(): boolean {
    return !!(
      this.config.twilioAccountSid &&
      this.config.twilioAuthToken &&
      this.config.twilioApiKey &&
      this.config.twilioApiSecret
    );
  }

  // Check if service should use mock mode
  shouldUseMockTwilio(): boolean {
    return !this.validateTwilioConfig();
  }

  // Get service status for debugging
  getServiceStatus() {
    return {
      twilio: {
        configured: this.validateTwilioConfig(),
        useMock: this.shouldUseMockTwilio()
      }
    };
  }
}

// Create singleton instance
export const config = new ConfigManager();

// Export convenience function for getting config
export const getConfig = () => config.get();

// Export Twilio configuration getter
export const getTwilioConfig = () => {
  const baseConfig = {
    accountSid: config.get('twilioAccountSid'),
    authToken: config.get('twilioAuthToken'),
    apiKey: config.get('twilioApiKey'),
    apiSecret: config.get('twilioApiSecret'),
    useMock: config.shouldUseMockTwilio()
  };

  // In development, determine the correct URL for staff joining
  let frontendUrl = config.get('frontendUrl');
  
  if (config.get('environment') === 'development') {
    // Check if we have STAFF_PORT environment variable for development
    const staffPort = process.env.STAFF_PORT || '3001';
    frontendUrl = `http://localhost:${staffPort}`;
  }

  return {
    ...baseConfig,
    frontendUrl
  };
};

export default config;