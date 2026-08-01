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
            // NOTE: the /test/test-landing.html block below overrides this
            // for that path (later matching source wins for the same key).
            key: "Content-Security-Policy",
            value: "frame-ancestors 'none'; object-src 'none'",
          },
        ],
      },
      {
        source: "/test/test-landing.html",
        headers: [
          {
            key: "Content-Security-Policy",
            value:
              "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src * data: blob:;",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
