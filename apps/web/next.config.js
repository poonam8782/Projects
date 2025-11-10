// @ts-check

/**
 * @type {import('next').NextConfig}
 */
const config = {
  poweredByHeader: false,
  generateEtags: true,
  experimental: {
    typedRoutes: true,
    optimizePackageImports: [],
  },
  transpilePackages: ['@neura/ui'],
  images: {
    formats: ['image/avif', 'image/webp'],
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'images.unsplash.com',
        port: '',
        pathname: '/**',
      },
    ],
  },
  async headers() {
    return [];
  },
};

module.exports = config;
