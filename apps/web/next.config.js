/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  // Allow Next to transpile the local shared package from the monorepo.
  transpilePackages: ["@cartana/shared"],
  // Pass through the API base URL at build time.
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL || "/api",
  },
};

module.exports = nextConfig;