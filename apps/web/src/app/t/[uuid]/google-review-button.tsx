import { Star } from "lucide-react";

interface Props {
  url: string;
  tenantSlug: string;
  accentColor: string;
}

/**
 * The dominant CTA on the customer-facing /t/[uuid] page.
 *
 * Visual weight is intentional — review volume is the highest-leverage
 * metric per LANDING-SPEC §1, so this button anchors the above-the-fold
 * region. Full-width on mobile, bold display copy, filled star icon, and
 * a soft drop shadow that lifts it off the tenant-coloured background.
 *
 * UTMs are appended client-side so the merchant's Google Business
 * Insights can attribute review traffic to SmartTap specifically.
 */
export function GoogleReviewButton({ url, tenantSlug, accentColor }: Props) {
  let href = url;
  try {
    const u = new URL(url);
    u.searchParams.set("utm_source", "smarttap");
    u.searchParams.set("utm_medium", "nfc");
    u.searchParams.set("utm_campaign", "tap");
    u.searchParams.set("utm_content", tenantSlug);
    href = u.toString();
  } catch {
    // url was not valid; fall back to the raw value
  }

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="group flex w-full flex-col items-center justify-center gap-1 rounded-xl px-6 py-5 text-center font-semibold shadow-[0_8px_16px_rgba(232,160,32,0.2)] transition-transform active:scale-[0.98] sm:py-6"
      style={{ backgroundColor: accentColor, color: "#1A1A1A" }}
    >
      <span className="flex items-center gap-2 text-xl leading-tight tracking-tight sm:text-2xl">
        <Star className="h-6 w-6 fill-current" aria-hidden="true" />
        Leave a Google Review
      </span>
      <span className="text-xs font-medium opacity-75 sm:text-sm">
        Takes 5 seconds · helps the shop
      </span>
    </a>
  );
}
