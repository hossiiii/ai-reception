/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable experimental features for NextJS 15
  experimental: {
    // App directory is enabled by default in NextJS 15
  },
  
  // API configuration
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: process.env.NODE_ENV === 'production' 
          ? '/api/:path*'  // Use Vercel serverless functions in production
          : 'http://localhost:8000/api/:path*'  // Proxy to FastAPI in development
      }
    ]
  },
  
  // Environment variables
  env: {
    NEXT_PUBLIC_API_URL: process.env.NODE_ENV === 'production'
      ? process.env.NEXT_PUBLIC_API_URL || 'https://your-app.vercel.app'
      : 'http://localhost:3000'
  },
  
  // Image optimization
  images: {
    domains: [],
  },
  
  // Optimize for tablet performance
  poweredByHeader: false,
  reactStrictMode: true,
  
  // Build configuration
  output: 'standalone',
  
  // TypeScript configuration
  typescript: {
    ignoreBuildErrors: false,
  },
  
  // ESLint configuration
  eslint: {
    ignoreDuringBuilds: false,
  }
}

module.exports = nextConfig