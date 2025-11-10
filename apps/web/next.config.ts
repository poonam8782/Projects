import type { NextConfig } from 'next';

const config: NextConfig = {
  poweredByHeader: false,
  experimental: {
    typedRoutes: true,
    optimizePackageImports: [],
  },
  transpilePackages: ['@neura/ui'],
  images: {
    formats: ['image/avif', 'image/webp'],
    remotePatterns: [],
  },
  async headers() {
    return [];
  },
};

export default config;
