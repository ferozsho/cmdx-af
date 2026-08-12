import path from "node:path";

import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  poweredByHeader: false,
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "no-referrer" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=(), payment=()",
          },
        ],
      },
    ];
  },
  experimental: {
    // Node 24 can return an empty stdout stream from Next's detached tsc
    // subprocess. TypeScript 5 still exposes the compiler API, so use it.
    useTypeScriptCli: false,
  },
  turbopack: {
    root: path.resolve(__dirname),
  },
};

export default nextConfig;
