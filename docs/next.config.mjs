import { createMDX } from 'fumadocs-mdx/next';
import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const withMDX = createMDX();
const docsRoot = dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const config = {
  reactStrictMode: true,
  turbopack: {
    root: docsRoot,
  },
  experimental: {
    cpus: 2,
    workerThreads: false,
    staticGenerationMaxConcurrency: 2,
    staticGenerationMinPagesPerWorker: 100,
  },
  webpack: (webpackConfig) => {
    webpackConfig.cache = false;
    return webpackConfig;
  },
};

export default withMDX(config);
