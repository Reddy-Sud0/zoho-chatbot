/** @type {import('next').NextConfig} */
const nextConfig = {
  // Fix: tell Next.js the correct output root to avoid
  // the "multiple lockfiles" workspace detection warning
  outputFileTracingRoot: require('path').join(__dirname, '../'),

  reactStrictMode: true,
};

module.exports = nextConfig;
