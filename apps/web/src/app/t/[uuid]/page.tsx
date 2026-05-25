import { headers } from "next/headers";
import { notFound } from "next/navigation";

import { ApiError, getApiClient } from "@/lib/api";
import { readMagicToken } from "@/lib/magic-link";

import { TapView } from "./tap-view";

interface PageProps {
  params: Promise<{ uuid: string }>;
}

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function detectDevice(userAgent: string | null): "ios" | "android" | "other" {
  if (!userAgent) return "other";
  const ua = userAgent.toLowerCase();
  if (ua.includes("iphone") || ua.includes("ipad") || ua.includes("ipod")) return "ios";
  if (ua.includes("android")) return "android";
  return "other";
}

export default async function CustomerTapPage({ params }: PageProps) {
  const { uuid } = await params;
  if (!UUID_RE.test(uuid)) notFound();

  const hdrs = await headers();
  const userAgent = hdrs.get("user-agent");
  const magicToken = await readMagicToken();

  const api = getApiClient();

  try {
    const data = await api.tap(uuid, {
      device_type: detectDevice(userAgent),
      interaction_type: "nfc",
      magic_link_token: magicToken ?? undefined,
    });
    return <TapView data={data} />;
  } catch (err) {
    if (err instanceof ApiError) {
      if (err.status === 404) notFound();
      if (err.status === 410) {
        return (
          <main className="container flex min-h-dvh items-center justify-center text-center">
            <p className="text-muted-foreground">This tag is no longer active.</p>
          </main>
        );
      }
    }
    throw err;
  }
}
