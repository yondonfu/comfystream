import type { NextConfig } from "next";
import path from 'path';
import fs from 'fs';

// Get the extension name dynamically from the directory structure
const getExtensionName = () => {
  try {
    // Get the current directory
    const currentDir = __dirname;
    // Extract the extension name from the path (assuming format: custom_nodes/extension_name/ui)
    const extensionName = path.basename(path.dirname(currentDir));
    return extensionName;
  } catch (error) {
    console.warn('Failed to get extension name dynamically:', error);
    // Fallback to the current name
    return 'ComfyStream';
  }
};

const extensionName = getExtensionName();

const nextConfig: NextConfig = {
  output: 'export',
  distDir: '../nodes/web/static',
  // Set base path for the app when served from ComfyUI
  basePath: `/extensions/${extensionName}/static`,
  // Set asset prefix for static files
  assetPrefix: `/extensions/${extensionName}/static`,
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