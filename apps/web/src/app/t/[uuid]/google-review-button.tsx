interface Props {
  url: string;
  tenantSlug: string;
  accentColor: string;
}

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
      className="inline-block rounded-full px-6 py-3 font-semibold"
      style={{ backgroundColor: accentColor, color: "#1A1A1A" }}
    >
      ⭐ Leave a Google Review
    </a>
  );
}
