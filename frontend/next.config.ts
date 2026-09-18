import type { NextConfig } from "next";

import { getDefaultBackendUrl, getLanIpv4Address } from "./lib/network-config";

const backendUrl = process.env.BACKEND_URL ?? getDefaultBackendUrl();
const allowedDevOrigins = [
  "localhost",
  "127.0.0.1",
  getLanIpv4Address() ?? "",
].filter(Boolean);

const nextConfig: NextConfig = {
  turbopack: {
    root: process.cwd(),
  },
  allowedDevOrigins,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
