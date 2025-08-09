/** @type {import('next').NextConfig} */
const nextConfig = {
  // API configuration
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: process.env.NODE_ENV === 'production' 
          ? `${process.env.NEXT_PUBLIC_API_URL}/api/:path*`
          : 'http://localhost:8000/api/:path*'
      }
    ]
  },
  
  // Optimize for tablet performance
  poweredByHeader: false,
  reactStrictMode: true,
}

module.exports = nextConfig