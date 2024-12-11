/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  experimental: {
    serverActions: true,
  },
  webpack: (config, { dev, isServer }) => {
    if (dev) {
      config.devtool = 'source-map';
    }
    config.externals = [...(config.externals || []), 'child_process', 'fs'];
    return config;
  },
}

module.exports = nextConfig