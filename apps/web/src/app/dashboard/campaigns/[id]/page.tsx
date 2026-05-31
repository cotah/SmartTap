import Link from "next/link";
import { notFound } from "next/navigation";

import { ApiError, getAuthApiClient } from "@/lib/api";
import { getDashboardContext } from "@/lib/dashboard-data";

import { CampaignForm } from "../campaign-form";

interface Props {
  params: Promise<{ id: string }>;
}

export default async function EditCampaignPage({ params }: Props) {
  await getDashboardContext();
  const { id } = await params;
  const api = getAuthApiClient();

  // No single-campaign GET in the backend — list and find. Cheap (handful of
  // rows per tenant) and avoids adding an endpoint just for this page.
  let items;
  try {
    ({ items } = await api.listCampaigns());
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  }
  const campaign = items.find((c) => c.id === id);
  if (!campaign) notFound();

  return (
    <main className="space-y-6">
      <header>
        <p className="text-sm text-electric-text-muted">
          <Link href="/dashboard/campaigns" className="underline">
            Campaigns
          </Link>{" "}
          / {campaign.name}
        </p>
        <h1 className="font-display text-3xl">{campaign.name}</h1>
      </header>

      <CampaignForm
        mode="edit"
        initial={{
          id: campaign.id,
          name: campaign.name,
          multiplier: campaign.multiplier,
          starts_at: toDatetimeLocal(campaign.starts_at),
          ends_at: toDatetimeLocal(campaign.ends_at),
          status: campaign.status,
        }}
      />
    </main>
  );
}

function toDatetimeLocal(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}`
  );
}
