import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'export',
  distDir: '../nodes/web/static',
  // Set base path for the app when served from ComfyUI
  basePath: '/extensions/comfystream_inside/static',
  // Set asset prefix for static files
  assetPrefix: '/extensions/comfystream_inside/static',
  // Disable image optimization since we're doing static export
  images: {
    unoptimized: true,
  },
  eslint: {
    // Only run ESLint during development, not during builds
    ignoreDuringBuilds: true,
  },
  // Test comment
};

export default nextConfig;

//to build:
// cd ui
// ./node_modules/.bin/next build