import { getAuthApiClient } from "@/lib/api";
import { getDashboardContext } from "@/lib/dashboard-data";

import { SettingsForm } from "./settings-form";

export default async function SettingsPage() {
  await getDashboardContext();
  const api = getAuthApiClient();
  const { tenant } = await api.getTenant();

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <header>
        <h1 className="font-display text-3xl leading-tight text-brand-green sm:text-4xl">
          Settings
        </h1>
        <p className="mt-2 text-sm text-neutral-600">
          Brand info shown to your customers, plus the Google review link they
          land on after a tap.
        </p>
      </header>

      <SettingsForm
        initial={{
          name: tenant.name,
          primary_color: tenant.primary_color,
          accent_color: tenant.accent_color,
          logo_url: tenant.logo_url ?? "",
          google_review_url: tenant.google_review_url ?? "",
          google_business_url: tenant.google_business_url ?? "",
          google_place_id: tenant.google_place_id ?? "",
        }}
      />
    </div>
  );
}
