import { getAuthApiClient } from "@/lib/api";
import { getDashboardContext } from "@/lib/dashboard-data";

import { InstagramCard } from "./instagram-card";
import { SettingsForm } from "./settings-form";

interface PageProps {
  searchParams: Promise<{ instagram_connected?: string }>;
}

export default async function SettingsPage({ searchParams }: PageProps) {
  await getDashboardContext();
  const api = getAuthApiClient();
  const [{ tenant }, instagramStatus, sp] = await Promise.all([
    api.getTenant(),
    api.getInstagramStatus(),
    searchParams,
  ]);

  // Set by the Meta OAuth callback redirect (?instagram_connected=1/0).
  const callbackResult =
    sp.instagram_connected === "1"
      ? ("success" as const)
      : sp.instagram_connected === "0"
        ? ("error" as const)
        : null;

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <header>
        <h1 className="font-display text-3xl leading-tight text-electric-cyan sm:text-4xl">
          Settings
        </h1>
        <p className="mt-2 text-sm text-electric-text-muted">
          Brand info shown to your customers, plus the Google review link they
          land on after a tap.
        </p>
      </header>

      <InstagramCard status={instagramStatus} callbackResult={callbackResult} />

      <SettingsForm
        initial={{
          name: tenant.name,
          primary_color: tenant.primary_color,
          accent_color: tenant.accent_color,
          logo_url: tenant.logo_url ?? "",
          google_review_url: tenant.google_review_url ?? "",
          google_business_url: tenant.google_business_url ?? "",
          google_place_id: tenant.google_place_id ?? "",
          opening_hours: tenant.opening_hours ?? "",
          menu_info: tenant.menu_info ?? "",
          brand_voice: tenant.brand_voice ?? "",
        }}
      />
    </div>
  );
}
