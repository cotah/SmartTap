import Link from "next/link";
import { notFound } from "next/navigation";

import { writeMagicToken } from "@/lib/magic-link";

interface PageProps {
  params: Promise<{ token: string }>;
}

// Same shape as the opt-out page — tokens are url-safe base64 from
// secrets.token_urlsafe(24), so ~32 chars. Bounded length defeats hand-typed
// gibberish before we ever write a cookie.
const TOKEN_RE = /^[A-Za-z0-9_-]{8,128}$/;

/**
 * Landing page for the "Show my stamps" CTA in the reactivation email.
 *
 * Intentionally minimal: stores the magic token in a cookie so the customer's
 * next NFC tap is recognised as them (carrying their stamps over), then shows
 * a short confirmation. We don't render stamp counts here because:
 *
 *   1. Doing so would need a new "lookup customer by magic token" endpoint,
 *      which is out of scope for S4-W2.
 *   2. The email already told them their progress; repeating it on this page
 *      adds nothing and risks drift if the numbers move between send & click.
 *
 * The reward only materialises when they physically visit the shop, so the
 * call-to-action here is exactly that.
 */
export default async function MagicLinkLanding({ params }: PageProps) {
  const { token } = await params;
  if (!TOKEN_RE.test(token)) notFound();

  // Server-side cookie write — runs before any client JS, so customers
  // without JS still get recognised on their next tap.
  await writeMagicToken(token);

  return (
    <main className="container flex min-h-dvh items-center justify-center px-4 py-8">
      <div className="w-full max-w-md space-y-4 rounded-2xl bg-white p-6 text-center shadow-sm">
        <h1 className="font-display text-2xl">You&apos;re recognised</h1>
        <p className="text-sm text-brand-black/70">
          Next time you tap a SmartTap card at the shop, your stamps will be
          waiting for you — nothing else to do.
        </p>
        <p className="text-xs text-brand-black/50">
          Got this by mistake?{" "}
          <Link
            href={`/u/${encodeURIComponent(token)}`}
            className="underline underline-offset-2"
          >
            Unsubscribe
          </Link>
          .
        </p>
      </div>
    </main>
  );
}
