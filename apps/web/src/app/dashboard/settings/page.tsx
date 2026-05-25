import Link from "next/link";

import { getAuthApiClient } from "@/lib/api";
import { getDashboardContext } from "@/lib/dashboard-data";

import { SettingsForm } from "./settings-form";

export default async function SettingsPage() {
  await getDashboardContext();
  const api = getAuthApiClient();
  const { tenant } = await api.getTenant();

  return (
    <main className="space-y-6">
      <header>
        <p className="text-sm text-brand-black/60">
          <Link href="/dashboard" className="underline">
            Dashboard
          </Link>{" "}
          / Settings
        </p>
        <h1 className="font-display text-3xl">Settings</h1>
        <p className="mt-1 text-sm text-brand-black/60">
          Brand info shown to your customers, plus Google review links.
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
    </main>
  );
}
