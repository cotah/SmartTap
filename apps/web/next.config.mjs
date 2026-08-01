/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@smarttap/core", "@smarttap/api", "@smarttap/ui"],
  typedRoutes: false,
  poweredByHeader: false,
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
          {
            // Minimal CSP: blocks framing + <object>/<embed> without touching
            // script/style, so nothing in the Next app can break. The full
            // nonce-based CSP is tracked as tech debt.
            key: "Content-Security-Policy",
            value: "frame-ancestors 'none'; object-src 'none'",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
