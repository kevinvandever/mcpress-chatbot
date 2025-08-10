/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false,
  typescript: {
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  experimental: {
    esmExternals: false,
  },
  swcMinify: false,
  // Force skip type checking completely
  ...(process.env.SKIP_TYPE_CHECK === 'true' && {
    typescript: {
      ignoreBuildErrors: true,
    },
    eslint: {
      ignoreDuringBuilds: true,
    },
  }),
  // Proxy API requests to local backend in development only
  async rewrites() {
    // Only proxy in development, not in production (Netlify/Railway)
    return process.env.NODE_ENV === 'development' ? [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/:path*',
      },
    ] : []
  },
}