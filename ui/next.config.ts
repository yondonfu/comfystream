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

// Check if we're in development mode
// This is set by the NEXT_PUBLIC_DEV environment variable in package.json scripts
const isDev = process.env.NEXT_PUBLIC_DEV === 'true';
console.log(`Running in ${isDev ? 'DEVELOPMENT' : 'PRODUCTION'} mode`);
console.log(`Output directory: ${isDev ? './.next' : '../nodes/web/static'}`);

const distDir = isDev ? './.next' : '../nodes/web/static';

const nextConfig: NextConfig = {
  output: isDev ? undefined : 'export',
  distDir: distDir,
  // Set base path for the app when served from ComfyUI
  basePath: isDev ? '' : `/extensions/${extensionName}/static`,
  // Set asset prefix for static files
  assetPrefix: isDev ? '' : `/extensions/${extensionName}/static`,
  // Disable image optimization since we're doing static export
  images: {
    unoptimized: true,
  },
  eslint: {
    // Only run ESLint during development, not during builds
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;

/*
Build Commands:
--------------
- Development: npm run dev (uses ./.next directory)
- Production: npm run build (uses ../nodes/web/static directory)
*/