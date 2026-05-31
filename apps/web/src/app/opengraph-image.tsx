import { ImageResponse } from "next/og";

/**
 * OpenGraph image for the SmartTap landing page. Generated on the Edge
 * at build/deploy time and served as a static asset by Next 15.
 *
 * Dark Electric treatment: near-black background with cyan NFC waves,
 * white headline (system font fallback since the edge runtime can't load
 * fonts from /public reliably), cyan accents, and the founder tagline +
 * URL in the bottom corner.
 *
 * Output: 1200×630 (the OG standard adopted by Twitter, LinkedIn,
 * Facebook, WhatsApp link previews).
 */
export const alt =
  "SmartTap — one tap, reviews go up, regulars come back. Built in Dublin.";
export const size = {
  width: 1200,
  height: 630,
};
export const contentType = "image/png";
export const runtime = "edge";

export default async function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "80px",
          background: "#0A0A0F",
          fontFamily: "sans-serif",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Decorative NFC waves in the top right — purely visual */}
        <svg
          width="320"
          height="320"
          viewBox="0 0 320 320"
          style={{ position: "absolute", top: -60, right: -60, opacity: 0.3 }}
        >
          <g stroke="#00D4FF" strokeWidth="6" fill="none" strokeLinecap="round">
            <path d="M280 160 Q280 80 200 80" />
            <path d="M280 160 Q280 40 160 40" />
            <path d="M280 160 Q280 0 120 0" />
          </g>
        </svg>

        {/* Brand mark */}
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div
            style={{
              width: 64,
              height: 64,
              borderRadius: 14,
              background: "#00D4FF",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#0A0A0F",
              fontSize: 32,
              fontWeight: 700,
            }}
          >
            ST
          </div>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <span style={{ fontSize: 28, color: "#FFFFFF", fontWeight: 600 }}>
              SmartTap
            </span>
            <span style={{ fontSize: 14, color: "#8899AA", letterSpacing: 1.5 }}>
              TAP · CONNECT · GROW
            </span>
          </div>
        </div>

        {/* Headline */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 940 }}>
          <span style={{ fontSize: 72, color: "#FFFFFF", lineHeight: 1.05, letterSpacing: -1.5 }}>
            One tap. Reviews go up.{" "}
            <span style={{ color: "#00D4FF" }}>Regulars come back.</span>
          </span>
          <span style={{ fontSize: 26, color: "#8899AA", lineHeight: 1.4, fontFamily: "sans-serif" }}>
            Your stand. Your customers. Your data. Not stuck inside someone else&apos;s app.
          </span>
        </div>

        {/* Footer line */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            fontFamily: "sans-serif",
          }}
        >
          <span style={{ fontSize: 22, color: "#FFFFFF", fontWeight: 600 }}>
            Built in Dublin for Dublin shops.
          </span>
          <span
            style={{
              fontSize: 22,
              color: "#00D4FF",
              fontWeight: 700,
              letterSpacing: 0.5,
            }}
          >
            smarttap.ie
          </span>
        </div>
      </div>
    ),
    {
      ...size,
    },
  );
}
